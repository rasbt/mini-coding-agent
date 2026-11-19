---
name: grid-validation
description: Validate the vacuum robot grid definition. Use when creating or editing the environment, grid, or terminal states.
---

# Grid Validation Procedure
1. Confirm the grid is 4x4 with start at (0,0).
2. Confirm exactly one wall at (1,1), one -1 terminal at (3,1), one +10 terminal at (3,3).
3. Confirm terminal states have no outgoing transitions.
4. Confirm a path exists from start to the goal.
5. Report pass/fail for each check.
