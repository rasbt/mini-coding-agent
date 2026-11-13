# 03 — Plan

**SDLC stage:** Planning
**Implements:** [02-spec.md](02-spec.md)

## Work breakdown

| # | Task | Files | Verifies |
|---|------|-------|----------|
| T1 | Write intent, spec, plan | `sdlc/01..03` | — |
| T2 | `Skill` data class + `parse_skill_file` (front-matter parser, stdlib only) | `mini_coding_agent.py` | S1 |
| T3 | `SkillRegistry.discover` over the search roots | `mini_coding_agent.py` | S1 |
| T4 | Tokenizer + TF-IDF cosine + trigger bonus → `SkillRegistry.match` | `mini_coding_agent.py` | S2 |
| T5 | `SkillLogger` (JSONL + stderr) | `mini_coding_agent.py` | S4 |
| T6 | Wire into `MiniAgent`: skill catalogue in prefix, `activate_skill`, auto match in `ask()`, `/skill` explicit prefix, Active-skill prompt section, `use_skill` tool | `mini_coding_agent.py` | S2, S3 |
| T7 | CLI flags and REPL commands (`/skills`, `/skill`) | `mini_coding_agent.py` | — |
| T8 | Package skills: `vacuum-world-agent` (Lab 5) and `pr-review` (example / distractor for the similarity check) | `skills/` | S5 |
| T9 | Unit tests for T2–T7 with `FakeModelClient` | `tests/test_skills.py` | S1–S4, S7 |
| T10 | Build clean Lab 4 workspace, run the mini agent with Ollama, run Lab 4 tests, capture logs | `lab4_skill_run/`, `sdlc/05-verification.md` | S6 |
| T11 | Update README with Component 7 | `README.md` | — |
| T12 | *(added after run 1)* Skill `context`/`resources` preloading + test | `mini_coding_agent.py`, `tests/test_skills.py` | S6 |

## Order and dependencies

```
T1 → T2 → T3 → T4 → T5 → T6 → T7 → T9
                          T8 ─────────┘
                                 T9 → T10 → T11
```

## Design decisions

- **Single file.** The original project is one file (`mini_coding_agent.py`)
  organised by component banners; the new component follows that pattern under
  a `7) Agent Skills` banner instead of adding a package.
- **TF-IDF + trigger phrases instead of embeddings.** Keeps zero runtime
  dependencies and makes the score explainable in the log.
- **Skill body in the per-request part of the prompt, catalogue in the prefix.**
  Matches component 2 (stable prefix for cache reuse; changing parts after it).
- **stderr for skill logs.** One-shot mode prints the final answer on stdout,
  so piping the answer still works.

## Risks

| Risk | Mitigation |
|------|------------|
| Small model (qwen3.5:4b) ignores long instructions | Skill written as short numbered steps; reference snippets in a separate `reference.md` the model reads with `read_file` |
| Default `max_new_tokens=512` too small to write a whole agent file | Run Lab 4 with `--max-new-tokens 4096 --max-steps 14` |
| False-positive skill activation | Threshold + distractor skill + negative unit test |
