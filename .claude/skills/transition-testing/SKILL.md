---
name: transition-testing
description: Test the vacuum robot environment's movement and transition behavior. Use when writing, running, or reviewing tests for step(), actions, wall bumps, or terminal states.
---

# Transition Testing Procedure

Tests go in tests/. Run them with: python -m pytest tests/ (or python -m unittest if pytest is not installed).

## Cases to cover
1. **Normal moves:** from (0,0), moving right goes to (0,1) and moving down goes to (1,0).
2. **Edge bumps:** from (0,0), moving up or left leaves the state at (0,0).
3. **Wall bump:** the wall at (1,1) cannot be entered. From (1,0), moving right stays at (1,0). From (0,1), moving down stays at (0,1).
4. **Terminal states:** entering (3,3) returns reward +10 and done=True. Entering (3,1) returns reward -1 and done=True.
5. **Living reward:** a normal non-terminal move returns the living reward (-0.04).
6. **Interface:** step(state, action) returns (next_state, reward, done) and nothing else leaks out, such as the full reward table.
7. **Determinism:** unless the assignment specifies noisy movement, the same state and action must always give the same result.

## Report
List each case with pass/fail. For any failure, show the state, action, expected result, and actual result.
