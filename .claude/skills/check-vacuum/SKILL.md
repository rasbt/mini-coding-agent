---
name: check-vacuum
description: Check the Lab 5 notebook and use focused specialists to review the environment, requirements, and code features.
disable-model-invocation: true
---

# Check Vacuum

1. Work from the CS440-Lab5 repository root. Run `python scripts/check_project.py`.
2. Report errors and unfinished TODOs. A passing check does not prove that Q-learning works.
3. Invoke `environment-specialist` with `context/environment.md` and only the environment cell from `q_learning.ipynb`. Ask it to check movement, rewards, reset, and terminal handling.
4. Invoke `requirements-specialist` with `context/requirements.md` and the check summary. Ask it to identify missing Lab 5 deliverables.
5. Invoke `configuration-reviewer` with `.claude/settings.json`, this skill, and the three specialist definitions. Supply the checker output and only relevant learning-function excerpts if reviewing Q-learning.
6. Combine the specialists' short findings. Use actual subagent calls and report any invocation failure.
7. Return: checks run, hyperparameters, findings, and remaining work. Do not change files unless requested or invent training results.
