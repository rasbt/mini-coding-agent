# 02 — Specification

**SDLC stage:** Specification / Design
**Implements:** [01-intent.md](01-intent.md)

## 1. Skill folder format

A skill is a folder containing a `SKILL.md` file. Any other files in the folder
(templates, reference notes, scripts) are resources the instructions may point
to.

```
skills/
├── pr-review/
│   └── SKILL.md
└── vacuum-world-agent/
    ├── SKILL.md
    └── reference.md
```

`SKILL.md` starts with a small front-matter block, followed by the
instructions in Markdown:

```markdown
---
name: vacuum-world-agent
description: Implement an AIMA vacuum-world agent in Python from a spec.md ...
triggers: vacuum world, vacuum agent, spec.md, persistent memory, q-learning
---

# Instructions
1. ...
```

| Field | Required | Meaning |
|-------|----------|---------|
| `name` | no (defaults to the folder name) | unique id used by `use_skill` and `/skill` |
| `description` | yes | one or two sentences; the main text used for similarity |
| `triggers` | no | comma-separated phrases; an exact phrase hit in the prompt boosts the score |
| `context` | no | comma-separated workspace files or globs (e.g. `spec.md, Test/*.py`) loaded into the prompt while the skill is active. Paths go through the normal workspace validation; missing files are skipped. *(added in iteration 2, see 05-verification.md)* |
| `resources` | no | comma-separated files inside the skill folder (e.g. `reference.md`) loaded the same way |

Loaded files are clipped to 9000 chars each and 20000 chars in total, and
are listed in the `skill_executed` log event as `loaded_files`.

Folders without a `SKILL.md`, or with a `SKILL.md` that has no description,
are skipped (and the reason is logged).

## 2. Discovery (`SkillRegistry.discover`)

Search roots, in priority order (first skill with a given name wins):

1. every `--skills-dir` passed on the command line
2. `<repo_root>/skills`, `<repo_root>/skill`
3. `<cwd>/skills`, `<cwd>/skill`
4. `<directory of mini_coding_agent.py>/skills` (skills shipped with the agent)

Each direct sub-folder of a root that contains `SKILL.md` is one skill.

## 3. Similarity check (`SkillRegistry.match`)

Standard library only. For each skill:

- **Tokenize** the prompt and the skill document
  (`name` + `description` + `triggers`, triggers counted twice):
  lower-case, split on non-alphanumerics, drop stop-words and 1-char tokens,
  light suffix stemming (`-ing`, `-ed`, `-es`, `-s`).
- **TF-IDF cosine**: IDF is computed over the skill corpus with smoothing
  `idf = ln((N + 1) / (df + 1)) + 1`.
- **Trigger bonus**: `trigger = 1.0` if any trigger phrase appears verbatim
  (case-insensitive) in the prompt, else `0.0`.
- **Score**: `score = 0.6 * cosine + 0.4 * trigger`, in `[0, 1]`.

The best-scoring skill is selected if `score >= threshold`
(default `0.20`, set with `--skill-threshold`). Ties go to the first skill in
discovery order. If no skill reaches the threshold, no skill is activated.

## 4. Triggering

| Trigger | When | Source label in log |
|---------|------|---------------------|
| Automatic | at the start of every `ask()`, the similarity check runs on the user prompt | `auto` |
| Explicit | user prompt starts with `/skill <name>` (REPL or one-shot) | `explicit` |
| On demand | the model calls the tool `use_skill(name)` during execution | `tool` |

The skill catalogue (name + description of every skill) is part of the stable
prompt prefix, so the model always knows which skills exist and can choose
`use_skill` when it realizes it needs one mid-task.

## 5. Execution

"Executing" a skill means making its instructions the governing procedure for
the current request:

- The active skill is stored in `session["active_skill"]`
  (`name`, `trigger`, `score`, `path`).
- `prompt()` inserts an **Active skill** section between the memory and the
  transcript, containing the skill directory and the full `SKILL.md` body
  (clipped to 6000 chars) plus the rule *"Follow these instructions step by
  step."*
- A `{"role": "skill", ...}` entry is added to the session history so the
  transcript shows when and why a skill became active.
- The active skill lasts for the current `ask()`; the next user request runs
  a fresh similarity check.
- Tool calls requested by the skill still go through validation and approval
  (component 3). Skills cannot bypass permissions.

## 6. Logging (`SkillLogger`)

Every skill event is written as one JSON line to
`<repo_root>/.mini-coding-agent/logs/skills.jsonl` and echoed to **stderr**
with a `[skills]` prefix (stdout stays clean for answers).

| Event | Fields |
|-------|--------|
| `discover` | `roots`, `skills` (names), `skipped` |
| `prompt` | `prompt` |
| `similarity_check` | `prompt`, `threshold`, `scores` (list of `{skill, score, cosine, trigger_hits}` sorted high→low), `selected` |
| `skill_executed` | `skill`, `trigger` (`auto`/`explicit`/`tool`), `score`, `path`, `loaded_files` |
| `skill_not_found` | `requested`, `available` |

All events also carry `ts` (UTC ISO-8601) and `session_id`.

## 7. CLI / REPL surface

- `--skills-dir PATH` (repeatable), `--skill-threshold FLOAT`, `--no-skills`
- `/skills` — list skills
- `/skill <name> <request>` — force a skill for this request

## 8. Lab 5 skill → Lab 4 task

- The Lab 5 workflow (spec-driven generation of AIMA vacuum-world agents:
  read `spec.md`, read the tests, write the agent file in the required verbose
  style, run the tests, fix failures) is packaged as
  `skills/vacuum-world-agent/`.
- Lab 4 (Strategy 1, `PersistentMemoryAgent`) is reproduced in a clean
  workspace `lab4_skill_run/` that contains only `spec.md` and the Lab 4 test
  file — **no** solution.
- The mini agent is run against that workspace with a plain prompt; the
  similarity check must select `vacuum-world-agent`, and the resulting
  `agent_strategy1.py` must pass `Test/test.py`.
