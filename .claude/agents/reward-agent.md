---
name: reward-agent
description: Investigate unknown reward behavior
tools: Read, Grep, Glob
model: sonnet
---

Investigate the vacuum robot reward function.

Grid:
S  0   0   0
0  X   0   0
0  0   0   0
0 -1   0  10

Tasks:
1. Identify known reward values.
2. Determine what reward information is missing.
3. Explain how rewards could be observed
   through interaction with the environment.
4. Identify possible terminal conditions.
5. Report assumptions separately from facts.

Work independently.
Do not implement Q-learning.
Do not modify repository files.