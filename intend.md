# Intent: Agent Skills Component

## Project Goal

The goal of this project is to extend the existing mini coding agent by implementing an agent skills component. This component will allow the agent to identify available skills and use their instructions when relevant to a user's prompt or when a specific skill is needed during execution.

## Problem

The current mini coding agent includes several components for handling user requests and performing coding tasks, but it does not have an agent skills component. Without this functionality, the agent cannot automatically recognize and use predefined skills to assist with specific tasks.

## Proposed Solution

We plan to develop an agent skills component that integrates with the existing mini coding agent. The component will:

- Discover available skills stored in folders containing a `skill.md` file.
- Check whether a user's prompt is relevant to an available skill.
- Load and execute the appropriate skill instructions when needed.
- Log user prompts, similarity checks, and executed skills to track the agent's behavior.

## Expected Outcome

The completed component should allow the mini coding agent to recognize and use relevant skills during execution. We will demonstrate this functionality by using the skill created in Lab 5 to attempt the tasks from Lab 4.

The logging functionality will also provide a record of how the agent identifies and uses skills, helping us verify that the component is working as intended.