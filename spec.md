# Spec: Agent Skills Component

SDLC stage 2 of 4: intent.md -> **Spec** -> plan.md -> validation.md

Lists requirements, skill file format, and the log events. 

## Definitions
- **Skill**: a folder containing SKILL.md
- **Skill root**: a folder whose sub-folders are skills (e.g. `.claude/skills/`).
- **Active skill**: the skill whose instructions are injected into the model prompt for the current request.

## Skill File Format
name: vacuum-rl                  # optional, defaults to folder name
description: What it does and when to use it.    # optional, defaults to first paragraph
tools: Skill, Read, Write        # optional, Claude Code field - ignored by the mini agent
triggers: [vacuum robot, q-learning]             # optional, added for this agent; `keywords:` is an alias

## Instructions the agent executes
Front matter supports `key: value`, `key: [a, b]` and block lists (`key:` then `- item`). Unknown keys are ignored.

## Functional Requirements
| ID | Requirement |
|----|-------------|
| FR1 | **Discovery.** At start-up the agent loads skills from, in priority order: `<workspace>/skills`, `<workspace>/skill`, `<workspace>/.claude/skills`, `<workspace>/.mini-coding-agent/skills`, any `--skills-dir`, then the skills bundled next to `mini_coding_agent.py` (CLI only; `--no-bundled-skills` disables). On a name clash the earlier root wins. |
| FR2 | **Catalog.** If at least one skill exists, the prompt prefix lists `- name: description` under `Skills:` and the tool `use_skill(name)` is offered. With no skills, prefix and tools are unchanged. |
| FR3 | **Similarity check.** For every user prompt each skill gets a score in [0, 1]; the best skill is selected if `score >= threshold` (default 0.25, `--skill-threshold`). First matching rule wins: (a) explicit `/skill <name>`, `$<name>`, "use the <name> skill" -> 1.0; (b) a trigger phrase occurs in the prompt as whole words, ignoring case and `_ - . /` -> 0.9; (c) else cosine similarity between prompt term counts and the skill profile (name x3, triggers x2, description x1) after lower-casing, stop-word removal and light stemming. |
| FR4 | **Execution (prompt-triggered).** The selected skill becomes active: its rendered instructions (name, description, source path, supporting files, body) are inserted after the cached prefix and memory and before the transcript, in every model call of that request. |
| FR5 | **Execution (agent-triggered).** The model may call `use_skill(name)` at any step; the skill becomes active for the rest of the request and its body is returned as the tool result. Unknown/empty names fail validation with the list of available skills. |
| FR6 | The active skill is cleared when the request ends (also on exceptions) and on `/reset`. Memory gets the note `skill <name> activated (<trigger>)`. |
| FR7 | **Logging.** Events are appended as JSON lines to `<workspace>/.mini-coding-agent/skill_events.jsonl`, each with `timestamp`, `session_id`, `event`. |
| FR8 | Delegated child agents use the same skill roots and threshold, and log with `depth` > 0. |
| FR9 | REPL `/skills` lists skills and the log path; the welcome screen shows skill names. |
| FR10 | **Project memory.** `CLAUDE.md` is read into the workspace context with AGENTS.md/README.md, so the Lab 4 grid definition reaches the model. |
| FR11 | `--num-ctx` sets Ollama's context window (only sent when given). |

## Non Functional Requrements
- NFR1: No new dependencies, no network calls in the similarity check; deterministic.
- NFR2: Backward compatible: all original tests pass unchanged.
- NFR3: The stable prompt prefix stays cache-friendly; the per-request skill block comes after it.
- NFR4: Injected skill body capped at 6000 chars; `use_skill` output at 8000.

## Log Events
| event | when | extra fields |
|-------|------|--------------|
| `prompt_received` | first thing in `ask()` | `prompt` |
| `similarity_check` | right after | `prompt`, `threshold`, `candidates[]` (`skill`, `score`, `method`, `matched_terms`, `matched_triggers`, best first), `selected` (name or null), `reason`, `depth` |
| `skill_executed` | a skill becomes active | `skill`, `path`, `trigger` (`explicit`/`trigger_phrase`/`cosine`/`tool`), `score`, `instructions_chars`, `depth` |
| `skill_completed` | request ends with an active skill | `skill`, `tool_calls[]` (`name`, `ok`), `status` (`final`/`stopped`/`error`), `final` (clipped), `depth` |

Order per request: `prompt_received` -> `similarity_check` -> (`skill_executed` -> `skill_completed`)?

## Acceptance Tests (`test_skills.py`)
Discovery incl. `.claude/skills` (FR1), catalog / no-skill behaviour (FR2), Lab 4 prompts -> `vacuum-rl`, TDD prompts -> `python-tdd`, review prompts -> `pr-review`, unrelated -> none, explicit invocation, threshold (FR3), injection order (FR4), `use_skill` mid-run and unknown name (FR5), cleanup on crash (FR6), event order/fields (FR7), CLAUDE.md in prompt (FR10), num_ctx (FR11), Lab 5 skill body unchanged, Lab 4 end-to-end run.