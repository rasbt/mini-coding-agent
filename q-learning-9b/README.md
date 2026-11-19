# CS440 Lab 5: Q-learning with Isolate

CS440 - Artificial Intelligence
Colorado State University
Fall 2026

## Overview

This repository builds on Isolate to solve the vacuum robot problem with Q-learning. Lab 5 includes subagents, hooks, and skills for Claude Code.

A main agent splits the work and gives each part to a specialist. Each specialist receives only the context needed for its task and returns a short summary.

## Problem Description

The vacuum robot operates in a 4x4 grid.

| start | 0  | 0 | 0  |
|-------|----|---|----|
| 0     | X  | 0 | 0  |
| 0     | 0  | 0 | 0  |
| 0     | -1 | 0 | 10 |

The robot will use Q-learning without receiving explicit T and R tables.

Movement is 80% in the chosen direction and 10% in each perpendicular direction. Both -1 and +10 end an episode.

The repository includes the three code feature configurations: hooks, skills, and subagents. The notebook implements tabular Q-learning with epsilon-greedy exploration, trains the robot, and evaluates the learned policy without exploration.

## Project Structure

```text
CS440-Lab5/
├── CLAUDE.md
├── README.md
├── q_learning.ipynb
├── results.json          (written by the notebook's recording cell)
├── requirements.txt
├── aima/
├── context/
│   ├── environment.md
│   └── requirements.md
├── scripts/
│   ├── check_project.py
│   ├── guard_tools.py
│   ├── verify_results.py
│   ├── sweep_hyperparameters.py
│   ├── test_code_features.py
│   ├── test_guard_tools.py
│   └── test_q_learning.py
└── .claude/
    ├── settings.json
    ├── skills/
    │   ├── check-vacuum/SKILL.md
    │   ├── verify-results/SKILL.md
    │   └── compare-hyperparameters/SKILL.md
    └── agents/
        ├── environment-specialist.md
        ├── requirements-specialist.md
        └── configuration-reviewer.md
```

## File Descriptions

### q_learning.ipynb

Contains the environment simulator (`MDPEnvironment`), the Q-learning trainer, the evaluator, and the policy display. It ends with a recording cell that saves `results.json` and a Tests section that runs the test suites. The learner interacts with the simulator only through `reset` and `execute_action`; it does not read the grid, the slip probabilities, or the reward map. The course AIMA package is included in `aima/`.

### scripts/

- `check_project.py`: the checker used by the PostToolUse hook and `/check-vacuum`.
- `guard_tools.py`: the PreToolUse guard hook (see Hooks).
- `test_q_learning.py`: tests for the notebook's environment and Q-learning code.
- `test_guard_tools.py` and `test_code_features.py`: tests for the guard hook, checker, hook, skill, and subagent files.

### aima/

Contains the unmodified course AIMA Python package from [carsonloedel/CS440](https://github.com/carsonloedel/CS440/tree/master/aima). Its license and exact source revision are recorded inside the folder.

### requirements.txt

Lists the dependencies for the notebook's AIMA import and Python kernel.

### CLAUDE.md

Contains the main instructions, specialist assignments, and delegation rules.

### context/environment.md

Documents the vacuum robot's grid, important locations, movement, and rewards.

### context/requirements.md

Documents the Lab 5 scope, proposed hyperparameters, and submission requirements.

### .claude/agents/environment-specialist.md

Defines the specialist that checks the grid and identifies unknown environment details.

### .claude/agents/requirements-specialist.md

Defines the specialist that checks the assignment scope and submission requirements.

### .claude/agents/configuration-reviewer.md

Defines the specialist that reviews selected configuration files for errors and contradictions.

## Code Features

### Hooks

`.claude/settings.json` runs the Python checker after Claude uses Write, Edit, or NotebookEdit on a relevant project file. The checker reads the notebook without executing it, checks Python syntax and hyperparameter ranges, and reports unfinished TODOs. Errors ask Claude to correct the edit; the hook does not undo an edit or guarantee correct learning behavior. Manual edits in VS Code do not trigger this Claude hook.

A second, PreToolUse hook runs `scripts/guard_tools.py` before Claude uses Read, Write, Edit, NotebookEdit, Grep, Glob, Bash, or PowerShell. It:

- blocks access to `.env` (`.env.example`, `.env.sample`, and `.env.template` are allowed),
- blocks edits to anything that looks like the separate Lab 4 submission (paths matching `lab4`, `lab 4`, or `lab_4`), and
- asks for confirmation before risky commands such as `git push`, `git reset --hard`, `git clean`, `rm -rf`, and `Remove-Item -Recurse`.

The guard matches names in paths and command text. It cannot stop a directory-wide search from reaching `.env`, and the Lab 4 pattern is a guess at the folder name.

The hooks use `python` from the Claude Code environment's PATH. Check `python --version` before starting Claude. Its script path uses the project directory placeholder so paths containing spaces work.

### Skills

`.claude/skills/check-vacuum/SKILL.md` defines `/check-vacuum`. It runs the checker, requests focused reviews from the three specialists, and summarizes findings. Its report covers the checks, specialist findings, and remaining work.

Two more skills, both manual-only like `/check-vacuum`:

- `/verify-results` runs `scripts/verify_results.py`, which checks that `results.json` is internally consistent and compares the learned policy with a value-iteration solution (verification only; the learner never sees it). It then checks the README's Results claims against the output.
- `/compare-hyperparameters` runs `scripts/sweep_hyperparameters.py`, which trains the notebook's Q-learner over a small grid of alpha, epsilon, and gamma values and several seeds, and summarizes the trade-offs. Pass options such as `--alpha 0.05 0.1 --seeds 10`. It never modifies the notebook or `results.json`.

### Subagents

The environment specialist checks the rules against the environment code, the requirements specialist checks Lab 5 deliverables, and the configuration reviewer checks the feature setup and selected learning-code excerpts. Each receives only the relevant files or excerpts and returns a short review. Their tools remain read-only.

## How the Strategy Works

1. You give Claude Code a task.
2. Claude reads CLAUDE.md and selects the appropriate specialists.
3. Each specialist receives a focused task and the relevant sources, rather than the full chat history.
4. Each specialist returns a short summary.
5. The main agent combines the findings into an answer.

All three specialists are read-only.

## Notebook Setup

From the CS440-Lab5 directory, install the notebook dependencies:

```sh
python -m pip install -r requirements.txt
```

Open `q_learning.ipynb` in VS Code and select that Python environment as the notebook kernel. The local `aima/` folder supplies `aima.agents`; `bootstrap.ipynb` is not needed for this import.

## Running Training and Evaluation

Run the notebook from top to bottom (run it with the CS440-Lab5 directory as the working directory):

1. The environment, parameters, and Q-learning cells define the code.
2. The training cell trains for `TRAIN_EPISODES` episodes (seed `TRAIN_SEED`), prints the outcomes of the last 100 training episodes, prints the learned policy, and then evaluates it for `EVAL_EPISODES` episodes (seed `EVAL_SEED`) with no exploration and no Q-value updates.
3. The recording cell writes the hyperparameters, training summaries, evaluation summary, and policy to `results.json`.
4. The Tests section runs the test suites.

Hyperparameters are set in the notebook's parameters cell: `ALPHA`, `GAMMA`, `EPSILON`, `EVALUATION_EPSILON`, `LIVING_REWARD`, the episode counts, `MAX_STEPS`, and the two seeds.

## Results

This demo starts with Q-learning TODOs. Fresh metrics and policy will be recorded in `results.json` after the notebook runs successfully.

## Checks and Tests

From the repository root:

```sh
python scripts/check_project.py
python -m unittest scripts.test_q_learning scripts.test_guard_tools scripts.test_code_features
```

- `test_q_learning` checks the environment rules (rewards, terminal cells, obstacle, 80/10/10 slips), epsilon-greedy selection and tie-breaking, the Q-update (including no bootstrapping from terminal states), reproducibility with seeds, evaluation without Q-value changes, an end-to-end training check, and that the learner code does not reference simulator internals.
- `test_guard_tools` checks the `.env`, Lab 4, and risky-command rules of the guard hook.
- `test_code_features` checks the checker, the PostToolUse hook, and the skill and subagent files.

The same suites run from the notebook's Tests section. The checker and the feature tests use only Python's standard library. `test_q_learning` also needs the packages in `requirements.txt`, because it loads the notebook's `aima` import. None of these tests proves the policy is optimal.

## Demonstration

1. Open a terminal in the CS440-Lab5 directory and start `claude`. Install Claude Code first if the command is unavailable.
2. Trust this project and review/approve its hook configuration when prompted. Start a fresh session after adding the feature files.
3. Use `/agents` to confirm the three specialists and `/hooks` to inspect the PreToolUse guard and PostToolUse checker hooks.
4. Run `/check-vacuum`. Inspect the actual specialist calls and compare their findings with the source files.
5. Ask Claude to make a harmless comment edit in the notebook or checker. Confirm that the PostToolUse check runs after that edit. The hook reports checks to Claude; ask it to show the feedback if needed.
6. Explain the hook, skill, and specialist decisions in the video, alongside the running Q-learning solution.

## Expected Behavior

Claude should:

- Identify the start at (0, 0), obstacle, and reward cells correctly.
- Keep explicit T and R tables separate from the learning agent.
- Use Q-learning for the Lab 5 implementation.
- Give each specialist only the context needed for its task.
- Report missing information instead of inventing rules.

## Why This Is Context Engineering

The Isolate strategy separates tasks into focused contexts. This reduces irrelevant information and helps each specialist stay on its assigned task.

## Limitations

Results are from a single seed (see Results). The hyperparameters are the proposed starting values from `context/requirements.md`; this README does not claim they are optimal, and no other settings have been compared yet.

File boundaries are instructions, not enforced access restrictions. Responses and actual delegation should still be verified. The checker and hook can be tested independently with the commands above. Claude Code discovery, actual hook triggering, and specialist invocation still require a live Claude Code demonstration.

Configuration references: [hooks](https://code.claude.com/docs/en/hooks), [skills](https://code.claude.com/docs/en/skills), and [subagents](https://code.claude.com/docs/en/sub-agents).
