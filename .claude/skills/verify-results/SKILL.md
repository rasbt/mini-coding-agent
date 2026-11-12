---
name: verify-results
description: Sanity-check results.json for consistency and compare the learned policy with a model-based optimum, then review the claims made about it.
disable-model-invocation: true
---

# Verify Results

1. Work from the CS440-Lab5 repository root. If `results.json` is missing, say so and stop; do not create or invent results. Tell the user to run the notebook's training and recording cells.
2. Run `python scripts/verify_results.py`. It checks that outcome counts add up, that reward matches steps, and that evaluation is not better than the 6-step best case. It also compares each learned action with a value-iteration solution. That solution is used only for verification and is never given to the learner.
3. Report any `INCONSISTENT` lines first. Policy differences from optimal are findings, not failures. Note which cells differ and by how much, and that rarely visited cells are expected to be less accurate.
4. Read the Results section of `README.md` and check each number and claim against `results.json` and the script output. Flag any claim the output does not support, such as "optimal", "best", or an explanation of why a cell's action was chosen.
5. Note that one seed shows only that a configuration worked in that run, and that the policy is evaluated from the start cell only.
6. Return: the recorded timestamp, consistency result, cells that differ from optimal, README claims that need correcting, and what remains unverified. Do not edit files unless asked, and do not rerun training.
