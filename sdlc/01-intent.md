# 01 — Intent

**SDLC stage:** Requirements / Intent
**Project:** Mini-Coding-Agent — Component 7: Agent Skills

## Problem

The mini coding agent (rasbt/mini-coding-agent) is built around six components:

1. Live repo context
2. Prompt shape and cache reuse
3. Structured tools, validation, and permissions
4. Context reduction and output management
5. Transcripts, memory, and resumption
6. Delegation and bounded subagents

It has no way to load **reusable, task-specific know-how**. Every time we ask
it to do something we have done before (e.g. "build a vacuum-world agent from a
spec", "review this PR"), we must re-explain the whole procedure in the prompt.
With a 4B local model this matters a lot: the model needs explicit, step-by-step
instructions to succeed.

## Goal

Add a seventh component, **Agent Skills**, so that the agent can:

- **Discover** skills stored as folders, one skill per folder, each with a
  `SKILL.md` file (e.g. `skills/pr-review/SKILL.md`,
  `skills/vacuum-agent-from-spec/SKILL.md`).
- **Select** the right skill automatically when a user prompt is similar enough
  to a skill's description (a *similarity check*).
- **Trigger** a skill on demand during execution, when the model decides it
  needs one (a `use_skill` tool).
- **Execute** the skill: inject the `SKILL.md` instructions into the prompt so
  the model follows them step by step.
- **Log** every decision: the prompt, the similarity scores for every skill,
  and which skill was executed (and how it was triggered).

## Success criteria

| # | Criterion | How we check it |
|---|-----------|-----------------|
| S1 | Skills are discovered from `skills/<name>/SKILL.md` (and `skill/<name>/SKILL.md`) | unit test |
| S2 | A matching prompt auto-activates the right skill; an unrelated prompt does not | unit test |
| S3 | The model can activate a skill mid-run with `use_skill` | unit test with FakeModelClient |
| S4 | Prompt, similarity check and executed skill are logged to a JSONL file and the console | unit test + live run log |
| S5 | The Lab 5 skill is packaged as a skill folder | file exists, parsed by registry |
| S6 | The mini agent, using that skill, solves Lab 4 (Strategy 1 persistent-memory vacuum agent) and the Lab 4 test suite passes | live run with Ollama `qwen3.5:4b` |
| S7 | All existing tests still pass; no new runtime dependencies (stdlib only) | `pytest` |

## Non-goals

- Embedding models / vector databases. The similarity check must be stdlib-only
  to keep the project dependency-free like the original.
- Skills that run arbitrary code automatically. A skill is *instructions*; any
  command still goes through the existing tool + approval layer (component 3).
- Changing how the other six components work.

## Stakeholders

- Students / instructor of CS440 (grading the component and the SDLC artifacts).
- Users of the mini agent who want reusable workflows.
