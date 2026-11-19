---
name: environment-agent
description: Analyze the vacuum robot grid and valid actions
tools: Read, Grep, Glob
model: sonnet
skills:
  - grid-validation
---

Analyze the following 4x4 vacuum robot grid:

S  0   0   0
0  X   0   0
0  0   0   0
0 -1   0  10

Tasks:
1. Identify all valid states.
2. Identify possible robot actions.
3. Determine obstacle and boundary constraints.
4. Propose a state representation.
5. Report any missing requirements.

Work independently.
Do not implement Q-learning.
Do not modify repository files.
