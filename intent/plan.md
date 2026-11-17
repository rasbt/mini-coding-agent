# Plan: Agent Skills for `mini_coding_agent.py`

Derived from `spec.md` and a read of `mini_coding_agent.py` (1,019 lines, stdlib-only, Ollama backend, `MiniAgent` with six numbered components).

## 1. Goal

Let the agent discover skill folders (e.g. `.claude/skills/pr-review/skill.md`), pick the best one for a user prompt or a mid-run need by comparing against each skill's description, execute that skill's instructions, and log the prompt, the similarity result, and the executed skill (name + description).

## 2. Design decisions (and why)

| Decision | Choice | Reason grounded in the existing code |
|---|---|---|
| Dependencies | **None.** Pure-Python similarity, stdlib logging | The file only imports stdlib and talks to Ollama via `urllib`. Keep it single-file and dependency-free. |
| Similarity method | TF-IDF cosine over `name + description` tokens (with stopword removal and light suffix stripping). Matcher sits behind a small interface so an Ollama-embedding backend can be swapped in later. | Small corpus, small local model (default `qwen3.5:4b`), no extra service needed. Scores land in [0, 1], which makes thresholds and logs easy to read. |
| What "executing a skill" means | Make the skill's instructions the **active skill** for the current request, injected into the prompt as its own section. The model then follows them using the existing tools. | The agent has no separate execution engine; the model drives everything through `ask()`. |
| Where instructions are injected | A dedicated `Active skill:` section in `prompt()`, **not** the tool-result history | `history_text()` clips older tool output to 180 chars (900 for recent) and `run_tool()` clips to 4,000, so instructions delivered as a tool result would be truncated or dropped within a few steps. |
| Two trigger paths | (a) **Prompt trigger**: auto-match at the start of `ask()`. (b) **Internal-need trigger**: a new `use_skill` tool the model can call mid-run. | Spec: "when an appropriate prompt is triggered *or* when the code agent needs a specific skill during execution." |
| Log format | JSON Lines file at `<repo_root>/.mini-coding-agent/logs/skills.jsonl`, plus optional one-line stderr echo | Machine-parseable, sits next to the existing `sessions/` dir, and `.mini-coding-agent` is already in `IGNORED_PATH_NAMES`. |
| Folder name | Skills live **only** in `.claude/skills/`. Use `pathlib`, never hard-coded backslashes. | Confirmed convention. `Path` handles Windows and POSIX separators. |
| File name | Find `skill.md` case-insensitively (`SKILL.md`, `Skill.md`) | Spec says `skill.md`; Claude-style skills use `SKILL.md`. |

## 3. Skill file format

```markdown
---
name: pr-review
description: Review a pull request or diff for bugs, style issues, and missing tests.
---
# Instructions
1. Run `git diff <default_branch>...HEAD`.
2. ...
```

- Parse a simple `key: value` frontmatter block with a small hand-written parser (no PyYAML).
- Fallbacks if frontmatter is missing: `name` = folder name, `description` = first non-heading paragraph.
- Skip (and log a warning for) skills with no usable description, since there would be nothing to match on.

## 4. Implementation steps

### Phase 0: Preparation

- [ ] **0.1** Preserve the file's **CRLF line endings** when editing. `patch_file` / diffs that assume `\n` will fail to match.
- [ ] **0.2** Add a section header for the new component to match the existing convention, and extend the header comment block: `# 7) Agent Skills -> SkillRegistry, SkillMatcher, SkillLogger, use_skill`.
- [ ] **0.3** Add constants near `MAX_TOOL_OUTPUT`:
  - `SKILLS_DIR = ".claude/skills"`
  - `SKILL_FILE_NAME = "skill.md"`
  - `MAX_SKILL_CHARS = 3000` (small local models have small context; clip instructions)
  - `DEFAULT_SKILL_THRESHOLD = 0.20`, `DEFAULT_SKILL_MARGIN = 0.05` (starting values; tune in Phase 6)
  - `MAX_SKILL_CATALOG = 20`

### Phase 1: Skill model and discovery

- [ ] **1.1** `Skill` dataclass (or plain class, matching the file's style): `name`, `description`, `instructions`, `path` (folder), `file` (the skill.md path).
- [ ] **1.2** `parse_skill_file(path)` implementing the format in section 3. Read with `encoding="utf-8", errors="replace"`, as the rest of the file does.
- [ ] **1.3** `SkillRegistry.discover(repo_root, cwd)`:
  - Look under `SKILLS_DIR` in `repo_root` and `cwd` (mirroring how `WorkspaceContext.build` checks both for docs).
  - One level of subfolders, each containing a `skill.md`.
  - De-duplicate by skill name; the first one found wins, and log a warning on collisions.
  - Return an empty registry (no error) if no skills dir exists, so existing behavior is unchanged.
- [ ] **1.4** Registry API: `all()`, `get(name)`, `__len__`, `catalog_text(limit=MAX_SKILL_CATALOG)` (name plus description clipped to ~160 chars).

### Phase 2: Similarity matching

- [ ] **2.1** `tokenize(text)`: lowercase, split on non-alphanumerics, drop a short stopword list and 1-char tokens, strip simple suffixes (`ing`, `ed`, `es`, `s`) so "reviewing" matches "review".
- [ ] **2.2** `SkillMatcher(skills)`: precompute TF-IDF vectors over `name + description`, with smoothed IDF so a 1-3 skill corpus doesn't produce all-zero weights.
- [ ] **2.3** `match(text) -> MatchResult` containing:
  - `scores`: every skill with its score, sorted descending (logged in full)
  - `best`: top skill or `None`
  - `threshold`, `margin`, and `decision` (`"selected"` or `"no_match"`)
  - `reason`: e.g. `below_threshold`, `ambiguous_margin`, `no_skills`
- [ ] **2.4** Selection rule: select the top skill only if `score >= threshold` **and** (`score - runner_up >= margin` or only one skill exists). Otherwise return no match. A weak guess is worse than no skill.
- [ ] **2.5** Define a `Matcher` interface (`match(text)`) so a future `OllamaEmbeddingMatcher` (`/api/embed`) can be selected by flag without touching the agent.

### Phase 3: Logging

- [ ] **3.1** `SkillLogger(path, session_id_getter, echo=False)` with `event(kind, **fields)` that appends one JSON line and (if `echo`) prints a short summary to **stderr** so stdout stays clean for answers.
- [ ] **3.2** Every record includes: `ts` (use the existing `now()`), `session_id`, `depth` (0 for the main agent, 1 for delegated child), `event`.
- [ ] **3.3** Three event types, one per spec requirement:

| Event | Fields | Spec item |
|---|---|---|
| `skill_trigger` | `source` (`"prompt"` or `"tool"`), `text` (the original prompt or the model's stated need, clipped) | Original prompt or trigger event |
| `skill_match` | `candidates` (all name/score pairs), `best`, `best_score`, `threshold`, `margin`, `decision`, `reason`, `method` | Similarity score/result |
| `skill_executed` | `name`, `description`, `path`, `instructions_chars`, `truncated` (bool) | Name and description of executed skill |

- [ ] **3.4** Also log `skill_skipped` when a match was rejected (below threshold or ambiguous) so no-match cases are visible, and `skill_warning` for discovery problems.
- [ ] **3.5** Logging must never crash the agent: wrap file writes in try/except and fall back to a stderr warning.
- [ ] **3.6** Log the prompt text clipped via `clip()` (e.g., 500 chars) since prompts may be long or contain secrets. Note this in the docs.

### Phase 4: Agent integration

All changes are in `MiniAgent` and `build_agent`.

- [ ] **4.1 Constructor.** Add kwargs `skills=None`, `skill_matcher=None`, `skill_logger=None`. Assign them **before** `self.tools = self.build_tools()` and `self.prefix = self.build_prefix()`, because both will read the registry. Add `self.active_skill = None`.
- [ ] **4.2 Prefix catalog (`build_prefix`).** If the registry is non-empty, add a `Skills:` block (`registry.catalog_text()`) and a rule: *"If a listed skill fits a need, call `use_skill`."* This block is static for the session, so prompt-cache reuse (component 2) is preserved.
- [ ] **4.3 New tool `use_skill` (`build_tools`).** Register only when skills exist:
  - schema `{"name": "str=''", "need": "str=''"}`, `risky: False`, description "Load a skill's instructions by name, or by describing the need."
  - `tool_use_skill(args)`: resolve by exact `name`; else run the matcher on `need`. Log `skill_trigger(source="tool")` and `skill_match`, then activate.
  - Returns a short confirmation (`"activated skill 'pr-review'; follow its instructions"`), **not** the full body (see section 2).
- [ ] **4.4 Validation and examples.** Add a `use_skill` branch to `validate_tool` (require non-empty `name` or `need`; unknown `name` is an error) and an entry in `tool_example`. Add an example line to `build_prefix`'s examples. Add `"name"` and `"need"` handling to `parse_xml_tool` only if XML form is wanted (JSON form works without changes).
- [ ] **4.5 Prompt trigger (`ask`).** At the top of `ask()`, after recording the user message and before the loop:
  1. Reset `self.active_skill = None`.
  2. Log `skill_trigger(source="prompt", text=user_message)`.
  3. Run `matcher.match(user_message)`; log `skill_match`.
  4. If `decision == "selected"`, call `self.activate_skill(skill)`; otherwise log `skill_skipped`.
  - Run this **once per `ask()`**, not once per loop attempt, to avoid log spam and repeated work.
- [ ] **4.6 `activate_skill(skill, source)`.** Set `self.active_skill`, clip instructions to `MAX_SKILL_CHARS` (set `truncated`), log `skill_executed`, and `remember()` the skill name in session memory.
- [ ] **4.7 Prompt injection (`prompt`).** Insert an `Active skill:` section between `memory_text()` and `Transcript:`:
  ```
  Active skill: pr-review
  Description: ...
  Follow these instructions for this request:
  <clipped instructions>
  ```
  Omit the section when no skill is active.
- [ ] **4.8 Mid-run switching.** If `use_skill` is called while a skill is already active, replace it and log both events. Cap `use_skill` calls per `ask()` (e.g., 2) so a confused model can't loop; the existing `repeated_tool_call` guard already blocks identical repeats.
- [ ] **4.9 Session state.** Add `"skill"` to `session["memory"]`, show it in `memory_text()`, clear it in `reset()`. Read with `.get("skill")` so sessions saved before this change still load via `from_session`.
- [ ] **4.10 Delegation (`tool_delegate`).** Pass `skills`, `skill_matcher`, and `skill_logger` to the child so it can use the same skills read-only. `depth` in the log distinguishes parent from child. The child's `ask()` will run its own prompt match on the delegated task, which is acceptable.
- [ ] **4.11 `build_agent`.**
  1. Build `SkillRegistry.discover(...)` from `workspace`.
  2. Build the matcher and `SkillLogger` at `<repo_root>/.mini-coding-agent/logs/skills.jsonl`.
  3. Pass all three into both `MiniAgent.from_session(...)` and `MiniAgent(...)`.
  4. Log any discovery warnings and a one-time `skills_loaded` summary (count and names).
- [ ] **4.12 Safety.** Skill instructions are untrusted repo content. They get **no** extra permissions: risky tools still go through `approve()`, and `read_only` children stay read-only. Skill-relative file reads still go through `path()`, so they are restricted to the repo root.

### Phase 5: CLI and UX

- [ ] **5.1** New arguments in `build_arg_parser`: `--skill-threshold` (float), `--no-skills` (disable the feature), `--skill-verbose` (echo log lines to stderr).
- [ ] **5.2** New `/skills` command in `main()` listing discovered skills and the currently active one. Update `HELP_DETAILS` (and `HELP_TEXT`).
- [ ] **5.3** Show skill count in `build_welcome` (e.g., a `SKILLS` cell) when any are loaded.
- [ ] **5.4** `/reset` also clears the active skill (covered by 4.9).

### Phase 6: Tests

Use the existing `FakeModelClient` for deterministic agent-loop tests, with a `tmp_path` workspace containing sample skills (`pr-review`, `write-tests`, `release-notes`).

- [ ] **6.1 Parsing:** frontmatter, missing frontmatter fallback, empty description skipped, CRLF files, `SKILL.md` casing.
- [ ] **6.2 Discovery:** `.claude/skills/` under `cwd` vs `repo_root`, duplicate names, no skills dir (no-op).
- [ ] **6.3 Matching:** "review this PR" selects `pr-review`; unrelated prompt returns `no_match`; near-tie returns `ambiguous_margin`; scores are within [0, 1]; stemming works.
- [ ] **6.4 Logging:** a run produces `skill_trigger`, `skill_match`, `skill_executed` in order with the required fields; no-match produces `skill_skipped` and **no** `skill_executed`; a read-only log directory doesn't crash the agent.
- [ ] **6.5 Prompt trigger e2e:** Fake model returns `<final>`; assert `agent.model_client.prompts[0]` contains the `Active skill:` section.
- [ ] **6.6 Tool trigger e2e:** Fake model emits `<tool>{"name":"use_skill",...}</tool>` then `<final>`; assert the skill appears in the *next* prompt and the log has `source: "tool"`.
- [ ] **6.7 Regression:** with no skills dir (and with `--no-skills`), prompts are byte-identical to the pre-change output and `use_skill` is not in the tool list.
- [ ] **6.8 Session:** resume an old session JSON without `memory["skill"]`; `/reset` clears it.
- [ ] **6.9 Delegation:** child agent logs `depth: 1` and stays read-only.
- [ ] **6.10 Threshold tuning:** run the sample prompts against the sample skills, adjust `DEFAULT_SKILL_THRESHOLD` / `DEFAULT_SKILL_MARGIN` so the positive and negative cases above separate cleanly.

### Phase 7: Documentation and samples

- [ ] **7.1** Add a sample `.claude/skills/pr-review/skill.md` (also used as the test fixture).
- [ ] **7.2** README section: skill folder layout, file format, how matching works, the threshold flags, and the log schema with one example record per event type.
- [ ] **7.3** Document the caveat that prompts are logged (clipped) and the log file may contain sensitive text.

## 5. Example log output

```json
{"ts":"2026-11-17T18:02:11+00:00","session_id":"20261117-180211-a1b2c3","depth":0,"event":"skill_trigger","source":"prompt","text":"Please review my PR for bugs"}
{"ts":"...","event":"skill_match","method":"tfidf","candidates":[{"name":"pr-review","score":0.52},{"name":"write-tests","score":0.08}],"best":"pr-review","best_score":0.52,"threshold":0.2,"margin":0.05,"decision":"selected","reason":"ok"}
{"ts":"...","event":"skill_executed","name":"pr-review","description":"Review a pull request or diff for bugs, style issues, and missing tests.","path":".claude/skills/pr-review/skill.md","instructions_chars":1184,"truncated":false}
```

## 6. Files touched

| File | Change |
|---|---|
| `mini_coding_agent.py` | New constants and classes (`Skill`, `SkillRegistry`, `SkillMatcher`, `SkillLogger`); edits to `MiniAgent.__init__`, `build_tools`, `build_prefix`, `prompt`, `ask`, `memory_text`, `reset`, `validate_tool`, `tool_example`, `tool_delegate`; edits to `build_agent`, `build_arg_parser`, `main`, `build_welcome` |
| `tests/test_skills.py` (new) | Phase 6 tests |
| `.claude/skills/pr-review/skill.md` (new) | Sample skill and fixture |
| `README.md` | Phase 7 docs |

## 7. Requirement traceability

| Spec requirement | Covered by |
|---|---|
| 1. Skill identification (prompt or internal need) | 1.3, 4.3, 4.5 |
| 2. Similarity matching against descriptions | 2.1-2.5 |
| 3a. Log original prompt / trigger event | 3.3 `skill_trigger`, 4.5, 4.3 |
| 3b. Log similarity score/result | 3.3 `skill_match`, 3.4 |
| 3c. Log name and description of executed skill | 3.3 `skill_executed`, 4.6 |
| Skills in `.claude/skills/`, each with `skill.md` | Section 3, 1.2, 1.3 |
| Logging integrated into execution flow | Phase 4 (logger passed through constructor, `ask`, `use_skill`, delegation) |

## 8. Risks and open questions

- **Small-model reliability.** A 4B model may rarely call `use_skill` on its own. The prompt-time auto-match (4.5) is the dependable path; the tool is a bonus. Consider lowering the threshold or adding the embedding matcher (2.5) if mid-run discovery matters.
- **Threshold sensitivity.** Lexical matching is weak on paraphrases ("look over my changes" vs. "review"). Mitigation: encourage keyword-rich descriptions in docs; revisit embeddings if misses are common.
- **Context budget.** Catalog plus active skill adds prompt length. Controlled by `MAX_SKILL_CATALOG`, description clipping, and `MAX_SKILL_CHARS`; may need lowering for the default model.
- **Scope.** Only project-level skills in `.claude/skills/` are supported. User-level skills (e.g. `~/.claude/skills`) are out of scope.
- **Skill-defined scripts.** Skills that tell the model to run commands still go through `run_shell` approval. Keep it that way.

## 9. Suggested build order

1. Phases 1-3 as pure, testable units (no agent changes), with their tests.
2. Phase 4.1-4.7 (prompt trigger path) and its e2e test.
3. Phase 4.3-4.4, 4.8 (`use_skill` tool path) and its e2e test.
4. Phase 4.9-4.11 (session, delegation, `build_agent`).
5. Phase 5 (CLI), then Phase 7 (docs), then Phase 6.10 threshold tuning against real prompts with Ollama.