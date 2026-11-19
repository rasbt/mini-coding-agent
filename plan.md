# Plan: Agent Skills Component

SDLC stage 3 of 4: intent.md -> spec.md -> **Plan** -> validation.md

## Design Decisions
- Same file format as Claude Code to keep consistency.
- Read CLAUDE.md for persistent-memory strategy. The skill relies on the grid in CLAUDE.md but the agent only reads README.md/AGENTS.md
- Execute = inject instructions into the prompt so when the model executes the skill, the skill dictates what it writes and which tools it uses, then is cleared after each request.

## Tasks

| # | Task | Files | Done when |
|---|------|-------|-----------|
| 1 | Skill parsing + discovery | `skills.py` | discovery tests pass |
| 2 | Tokenizer, cosine, trigger and explicit matching | `skills.py` | similarity tests pass |
| 3 | Registry in `MiniAgent`, catalog in prefix, `use_skill` tool + validation | `mini_coding_agent.py` | original tests still pass |
| 4 | `select_skill` / `activate_skill` / skill block in `prompt()` / cleanup in `ask()` | `mini_coding_agent.py` | injection + crash tests pass |
| 5 | Log the 4 events | `mini_coding_agent.py`, `skill_logger.py` | order/field tests pass |
| 6 | CLI flags, `/skills`, welcome row, child agents, `.claude/skills`, `CLAUDE.md`, `--num-ctx` | `mini_coding_agent.py` | `--help` shows flags |
| 7 | Import Lab 5 skill + add triggers; extra skills `pr-review`, `python-tdd` as distractors | `skills/`, `lab4_template/` | skill tests pass |
| 8 | Lab 4 template (CLAUDE.md, README, code-reviewer, skill; no code) + runner (scripted / `--ollama`) | `lab4_template/`, `run_lab4_with_skill.py`, `demo/` | `python main.py` exits 0 |
| 9 | Validation report | `validation.md` | filled with results |

## Risks
- A small model may ignore skill rules -> the skill's rules are short and explicit; the transcript shows which were followed.
- Follow-ups with no domain words ("run main.py and fix it") miss the skill -> name the domain, use `/skill vacuum-rl`, or rely on the model calling `use_skill` from the catalog.