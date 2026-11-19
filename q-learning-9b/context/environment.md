# Vacuum Robot Environment

## Overview

The vacuum robot operates in a 4x4 grid environment.

Lab 5 uses the grid provided in Lab 4, with the movement and reward rules agreed by the group.

## Grid Layout

| start | 0  | 0 | 0  |
|-------|----|---|----|
| 0     | X  | 0 | 0  |
| 0     | 0  | 0 | 0  |
| 0     | -1 | 0 | 10 |

## Coordinate System

For documentation purposes, positions use zero-based (row, column) coordinates.

The top-left cell is (0, 0).

## Important Locations

| Position | Value | Description |
|----------|-------|-------------|
| (0, 0)   | start | Robot's starting position |
| (1, 1)   | X     | Obstacle |
| (3, 1)   | -1    | Negative reward cell |
| (3, 3)   | 10    | Positive reward cell |
| Other    | 0     | Normal cells |

## Environment Characteristics

The environment contains:

- 16 total grid positions
- One obstacle
- One starting position
- One negative reward cell
- One positive reward cell

The robot will use Q-learning to learn how to interact with this environment.

## Movement

- Actions: Up, Down, Left, and Right.
- Move in the chosen direction with probability 80%.
- Move in either perpendicular direction with probability 10% each.
- If the resulting move hits the obstacle or a grid boundary, stay in place.

## Rewards and Episodes

- Start each episode at (0, 0).
- Ordinary moves receive the living reward, initially proposed as -0.04.
- Blocked moves also receive the living reward.
- Entering (3, 1) gives -1 and ends the episode.
- Entering (3, 3) gives +10 and ends the episode.
- Do not add the living reward to a terminal reward.

## Q-learning

The simulator uses these movement and reward rules. The learning agent observes its current position, takes an action, and receives the reward, next position, and episode status. It does not read explicit T and R tables or the environment's reward map.

The environment should include a dedicated function to find the recharge location, addressing the Lab 3 feedback. This function belongs to the environment and does not provide a route to the learning agent.
