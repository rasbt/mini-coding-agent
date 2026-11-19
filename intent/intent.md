# Coding Agent Skills

## Repository
This project extends the upstream lightweight coding agent with a seventh component for skills.

## Objective
The code agent must be able to identify a folder skill (such as .claude\skills\pr-review) and trigger a skill.md file by executing the instructions when an appropriate prompt is triggered or when the code agent needs a specific agent skill during execution.
Each skill has a description which the agent will use to identify the right skill to use.
The new component must log the prompt, the similarity check, and the executed skill.

Demonstrate the component by attempting the CS440 Lab 4 vacuum robot problem
with the original Lab 5 `check-vacuum` skill and a Q-learning starter.
