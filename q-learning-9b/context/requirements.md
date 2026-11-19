# CS440 Lab 5 Requirements

## Assignment

Lab 5: Solve Lab 4 Using Q-learning

## Objective

Implement the Q-learning vacuum robot using the Lab 4 environment.

The assignment requires three of these four code features: hooks, MCP, skills, and subagents.

This repository will use:

1. Subagents (building on Isolate)
2. Hooks
3. Skills

Write is not a separate demonstration in this repository.

## Environment

The vacuum robot uses the following 4x4 grid:

| start | 0  | 0 | 0  |
|-------|----|---|----|
| 0     | X  | 0 | 0  |
| 0     | 0  | 0 | 0  |
| 0     | -1 | 0 | 10 |

The learning agent does not receive explicit T and R tables. It learns from observed transitions and rewards.

Use the agreed 80/10/10 movement and reward rules in `environment.md`.

## Current Lab Scope

Focus on:
- Implementing and evaluating the Q-learning robot
- Using and demonstrating subagents, hooks, and skills
- Selecting and explaining the hyperparameters
- Showing the running solution and documenting how to run it

## Proposed Hyperparameters

Starting values to test:

- Living reward: -0.04 on nonterminal steps, encouraging shorter paths.
- Discount factor: 0.95, giving future rewards substantial value.
- Learning rate: 0.1, updating action values gradually.
- Epsilon: 0.2 during training, exploring on 20% of action selections.
- Evaluation epsilon: 0, following the learned policy while movement remains stochastic.

These are proposed starting values, not verified optimal settings. Report the actual values used and measured results.

## Required Submission

The group must submit the following on Canvas:

### 1. Repository Links

A text file containing the link to the repository configured with the selected code features.

### 2. README

A README file documenting the project structure, setup, and how to run the solution.

### 3. Video Presentation

A video showing the running solution and explaining the code features and hyperparameters.

Requirements:
- Maximum duration: 3 minutes
- Every group member must present for a fair amount of time
- Students must show their faces while presenting
- Use a professional background
- Explain the code feature decisions
- Explain the hyperparameter decisions
- Show the running solution

The video must be private and shared only with the instructor team.

If submitting a video link, put it in group_name.txt for a group submission or firstName_lastName.txt for an individual submission.

A private video link or a video file such as MP4 may be submitted. The link must work for the instructor team and must not allow other students access.

Submissions without a video receive zero points. The instructor team may ask any participant questions about the implementation.

## AI Policy

The use of AI is allowed for this assignment.

## Strategy 4 Objective

Demonstrate how Claude Code delegates focused tasks to specialists, each receiving only the context needed for its role.

The demonstration should show separate specialist calls, relevant source files, and short summaries returned to the main agent.