# Vacuum Robot Project
## CS440 Lab 5: Q-learning with Isolate

You are assisting with a vacuum robot project for CS440, Artificial Intelligence, at Colorado State University.

This repository builds on Isolate using subagents, hooks, and skills for Lab 5.

The goal is to give each specialist only the context needed for its task.

## Project Overview

The vacuum robot operates in a 4x4 grid environment.

The environment contains:
- One starting position at the top-left
- One obstacle
- One cell labeled -1
- One goal cell labeled +10
- Normal cells labeled 0

The robot will learn with Q-learning from observed actions and rewards, without receiving explicit T and R tables.

Movement and reward rules are documented in `context/environment.md`.

## Project Context

The following files contain important project information:

- `context/environment.md`: grid, movement, and reward rules
- `context/requirements.md`: Lab 5 scope, proposed hyperparameters, and submission requirements

Pass each file only to the specialist that needs it. Do not import all context into every task.

## Instructions

1. Delegate grid questions to `environment-specialist` with `context/environment.md`.
2. Delegate assignment questions to `requirements-specialist` with `context/requirements.md`.
3. Delegate configuration reviews to `configuration-reviewer` with the specific files and relevant source excerpts.
4. Give each specialist a clear task, allowed files, and expected output. Do not pass the full conversation.
5. Combine their short summaries and identify missing or contradictory information.
6. Do not invent transition probabilities, reward rules, or implementation results.

## Current Lab Scope

Implement and evaluate the Q-learning vacuum robot. Use subagents, hooks, and skills, and explain the chosen hyperparameters.

Do not expose the environment's transition probabilities or reward map to the learning agent. Report actual results without inventing performance claims.

## Code Features

- Hook: `.claude/settings.json` runs `scripts/check_project.py --hook` after Claude uses Write, Edit, or NotebookEdit.
- Skill: `/check-vacuum` runs project checks and delegates focused reviews to the specialists.
- Subagents: use the three definitions in `.claude/agents/` for separate, read-only reviews.

The checker validates syntax, parameter ranges, and required files. It reports unfinished TODOs without running the notebook or proving the learned policy is correct.

## Specialists

Specialist definitions are stored in `.claude/agents/`.

Each specialist reads only the sources assigned to it and returns a short summary. All specialists are read-only.

Use actual subagent calls. If a specialist cannot run, report that limitation.

Modify project files only when requested. Preserve the separate Lab 4 submission.
