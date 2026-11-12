# Vacuum Robot Q-Learning Project

## Objective
Implement Q-learning for a vacuum robot in a 4x4 grid environment to navigate from the start position (0,0) to the reward location (3,3).

## Environment Specifications
- **Grid Size**: 4x4 cells
- **Start Position**: (0,0)
- **Reward Location**: (3,3) - provides positive reward upon reaching
- **Obstacle**: Located at (1,1) - robot cannot move into this cell
- **Trap**: Located at (1,3) - incurs penalty if entered

## Robot Actions
Available operations:
1. **Left** - Move one cell left
2. **Right** - Move one cell right
3. **Up** - Move one cell up
4. **Down** - Move one cell down
5. **Suck** - Clean the current cell (not used initially as environment is clean)
6. **NoOp** - Stay in place (incurs cost, not beneficial)

## Constraints & Assumptions
- Environment starts clean, so Suck action is not needed initially
- NoOp action incurs a cost without progressing toward the goal, so it should be avoided
- Robot cannot move out of the environment or into obstacle cells
- Goal: Minimize cumulative cost to reach (3,3) using Q-learning

## Implementation Requirements
- Implement Q-table initialization and updates
- Handle state transitions respecting obstacles and traps
- Apply appropriate action selection (e.g., epsilon-greedy)
- Track visited states for learning progress