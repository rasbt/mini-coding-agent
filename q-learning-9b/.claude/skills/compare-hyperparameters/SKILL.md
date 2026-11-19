---
name: compare-hyperparameters
description: Sweep alpha, epsilon, and gamma over several seeds and summarize the trade-offs, to support the hyperparameter explanation the lab asks for.
disable-model-invocation: true
argument-hint: "[--alpha ...] [--epsilon ...] [--gamma ...] [--seeds N]"
---

# Compare Hyperparameters

1. Work from the CS440-Lab5 repository root. Run `python scripts/sweep_hyperparameters.py $ARGUMENTS`. With no arguments it sweeps alpha and epsilon around the notebook's current values over 5 seeds. Training seeds and evaluation seeds are disjoint from the notebook's own seeds.
2. Add `--out sweep_results.json` if the user wants the table saved. Otherwise do not write files. The script never changes the notebook or `results.json`.
3. Summarize the table: success rate (mean and range across seeds), average evaluation reward and steps, and late-training traps for each setting.
4. Explain the trade-offs only as far as the numbers show them:
   - alpha: how fast values move versus how noisy they are.
   - epsilon: exploration of rarely visited cells versus wasted or risky steps while training.
   - gamma: how strongly the +10 goal outweighs the per-step cost.
5. Say when differences fall within the seed-to-seed range and cannot be told apart. Do not call any setting "best" or "optimal" on that basis alone. The sweep covers a small grid and a small number of seeds.
6. Return: the settings tried, the table, what the evidence supports, and a suggested wording for the README's hyperparameter explanation. Do not edit the README or the notebook parameters unless asked, and do not invent results.
