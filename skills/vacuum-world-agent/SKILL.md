---
name: vacuum-world-agent
description: Implement or fix a Python agent for the AIMA 4x4 vacuum world from a spec.md file (persistent memory agent, sub-agent orchestrator, or Q-learning agent), then run the pytest tests until they pass.
triggers: vacuum world, vacuum agent, vacuum-world, spec.md, persistent memory agent, PersistentMemoryAgent, SubAgentOrchestrator, q-learning, agent_strategy
context: spec.md, Test/*.py, tests/*.py
resources: reference.md
---

# Skill: vacuum-world-agent (CS440 Lab 5)

Spec-driven workflow from Lab 5: the spec.md is the contract, the tests are
the judge. `spec.md`, the test files and `reference.md` are already loaded
below under "Skill files". Do not call read_file on them. One tool call per
reply.

## Step 1 - Plan (no tool call needed)
From the loaded spec.md and tests, find:
- the exact file name to create (for example `agent_strategy1.py`),
- the exact class name and every method the tests call,
- the exact keys of `self.memory` and their initial values,
- the decision rules in priority order.
The tests decide the exact API. Copy names exactly.

## Step 2 - Write the agent file in ONE write_file call
Use the XML form:
`<tool name="write_file" path="agent_strategy1.py"><content>...</content></tool>`
The file must:
- use only the Python standard library,
- define the class with `__init__(self, env)` that stores `self.env = env`
  and builds `self.memory` with EVERY key from the spec, one per line, each
  with a comment,
- implement `update_memory(percept)` as small numbered blocks that each call
  `self._log(...)`, and increase `step_count` by exactly 1 per call,
- implement `program(percept)` as `if/elif` branches in the spec's rule order,
  each with a `# Rule N:` comment, logging why the action was chosen,
- never read `env.grid`; only use the percept and memory,
- only return a move toward a neighbor whose percept value is not None,
- copy `_log`, `_neighbor_coord`, `_bfs_next_step` and `DIRECTIONS` from
  reference.md,
- give every public method a docstring,
- end with an `if __name__ == "__main__":` demo that does not crash. The
  demo must define its own small environment class IN THIS FILE (a 4x4 grid
  with a `percept()` method like the one in the tests); never use a class
  that only exists in the test file.

## Step 3 - Run the tests
Call run_shell with
`{"command":"python -m pytest -q Test/*.py","timeout":60}`
(list the files explicitly: a file named `test.py` is not collected when
you pass only the folder).
Then call run_shell with `{"command":"python agent_strategy1.py","timeout":30}`
(use the real file name) to check that the demo runs without a traceback.

## Step 4 - Fix and re-run
If any test fails or the demo crashes, read the assertion message, fix the smallest piece with
patch_file (or rewrite the file with write_file), then run the tests again.
Repeat until all tests pass.

## Step 5 - Finish
Reply with `<final>` listing the file written, the class name and the test
result line (for example `5 passed`).
