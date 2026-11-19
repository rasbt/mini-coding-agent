# Coding Agent Skills Specification

## Repository
The upstream lightweight coding agent provides the runtime for this component.

## Objective
The code agent must be able to identify a folder skill (such as `.claude\skills\pr-review`) and trigger a skill.md file by executing the instructions when an appropriate prompt is triggered or when the code agent needs a specific agent skill during execution.
Each skill has a description which the agent will use to identify the right skill to use.
The new component must log the prompt, the similarity check, and the executed skill.

## Requirements
1. **Skill Identification**: The agent should be able to detect when a user prompt or internal need requires a specific skill folder (e.g., `.claude\skills\pr-review`).
2. **Similarity Matching**: Implement a mechanism to compare the current context/prompt against skill descriptions to determine the best matching skill.
3. **Logging**: The system must log:
   - The original prompt or trigger event
   - The similarity score/result of the skill identification process
   - The name and description of the executed skill

## Implementation Notes
- Skills should be organized in folder structures within `.claude\skills\`
- Each skill folder contains a `skill.md` file with the skill's description and instructions
- The logging mechanism should be integrated into the agent's execution flow

## Acceptance checks

- A matching ordinary prompt loads the skill body into the current model prompt.
- A model request for an installed skill can activate it during a turn.
- An unrelated subsequent prompt does not inherit the previously active skill.
- The log can connect a trigger, selection result, and activation by session ID.
- The demo attempts the Lab 4 vacuum robot problem using the original Lab 5
  skill and reports the actual edits, tests, and training results it obtains.
