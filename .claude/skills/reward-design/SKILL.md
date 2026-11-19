---
name: reward-design
description: Choose, check, and justify the reward and hyperparameter values (living reward, discount factor, learning rate, epsilon) for the vacuum robot. Use when setting or changing reward values or Q-learning hyperparameters.
---

# Reward and Hyperparameter Design Procedure

## Current values (source of truth: context/vacuum-environment.md)
- Living reward: -0.04 per step
- Discount (gamma): 0.9
- Learning rate (alpha): 0.1
- Epsilon: 0.1

## Steps
1. Read context/vacuum-environment.md and confirm the values above match it. If they differ, report the mismatch and do not silently pick one.
2. Check each value against these rules:
   - Living reward must be small and negative compared to the terminal rewards (+10 goal, -1 pit), so the robot prefers short paths but still reaches the goal.
   - Gamma must be strictly between 0 and 1. Too low and the +10 will not propagate back to the start.
   - Alpha must be between 0 and 1. Smaller is more stable, larger learns faster but is noisier.
   - Epsilon must be between 0 and 1. Note any plan to decay it.
3. Write a 1-2 sentence justification for each value.
4. Remember the robot does NOT know R or T. The reward function belongs to the environment. The agent only sees rewards returned by step(). Never let agent code read the reward table directly.
5. If a value is changed, record the old value, new value, and reason in the Decision Log in context/vacuum-environment.md.
6. Report a short summary table: parameter, value, justification, pass/fail.
