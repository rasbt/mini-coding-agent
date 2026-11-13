# spec.md — Strategy 1: Persistent Memory Vacuum Agent

## Goal

Implement a Python agent for the AIMA vacuum world that uses a
persistent-memory architecture. Today: scaffolding only, NO Q-learning.

## Environment Contract (implemented in vacuum_env.py, do not modify here)

- Grid: 4x4. Coordinates are (row, col), 0-indexed.
- Cells: 'start' (robot start, at (0,0)), 'X' (obstacle),
  -1 (penalty), 10 (reward), 0 (plain).
- The robot occupies one cell at a time.
- Actions: 'UP', 'DOWN', 'LEFT', 'RIGHT', 'SUCK', 'NO-OP'.
- Percepts available to the agent each step:
    {
      "pos": (row, col),
      "cell": <cell value>,          # 0, -1, 10, or 'start'
      "dirty": bool,                  # True if cell needs SUCK
      "neighbors": {                  # what the agent can sense adjacently
          "UP": <cell value or None>,  # None = out of bounds / obstacle
          "DOWN": ..., "LEFT": ..., "RIGHT": ...
      }
    }

## Agent Contract (agent_strategy1.py)

Define class `PersistentMemoryAgent` with:

### State

- `self.memory: dict` — persistent memory. At minimum:
  - `visited: set[(r,c)]`
  - `obstacles: set[(r,c)]`
  - `rewards: dict[(r,c) -> value]`
  - `dirty_known: set[(r,c)]`
- `self.last_action: str | None`
- `self.last_pos: (r,c) | None`

### Methods

- `__init__(self, env)` — store env reference, init memory.
- `update_memory(self, percept)` — merge percept into memory.
  Rules:
  - mark `pos` visited
  - if `neighbors[d]` is None → add neighbor coord to obstacles
  - if `neighbors[d]` in (-1, 10) → record in rewards
  - if `dirty` is True → add pos to dirty_known
- `program(self, percept) -> str` — return next action.
  Decision priority (in order):
    1. If `percept["dirty"]` → return 'SUCK'
    2. If a cell in `dirty_known` is reachable → move one step toward it
    3. Otherwise → explore: pick an unvisited, non-obstacle neighbor
    4. If no unvisited neighbor → move toward nearest unvisited cell
       via BFS over known-safe cells
    5. If all else fails → return a valid random move
- `_bfs_next_step(self, start, goal) -> str` — helper: BFS over
  cells that are NOT in self.memory["obstacles"]; return first action.

## Constraints

- Pure Python 3.9+, standard library only (no numpy).
- The agent MUST NOT look at the full grid directly — only via percepts.
- Memory must actually be used: the agent must not re-enter a cell it
  already knows is an obstacle, and must not re-SUCK a known-clean cell.
- Keep functions short; add docstrings to each public method.

## Deliverable for this file

Only `agent_strategy1.py`. Do not touch `vacuum_env.py`,
`agent_strategy4.py`, or `main.py` in this step.

## Test Expectations

Running `main.py` with `PersistentMemoryAgent` for 30 steps should:

- end with at least 3 cells cleaned (dirty_known drained to empty or
  the robot stuck without new dirt),
- never crash on out-of-bounds moves,
- print the memory dict at the end.

## Persistent Memory — Verbosity & Explicitness Requirements

The persistent memory is the core of Strategy 1. It MUST be verbose and
explicit. Do NOT compress it into a single dict literal or a one-liner.

### Required memory schema (explicit, named fields)

`self.memory` MUST be a dict with ALL of the following keys, each
initialized explicitly in `__init__` with a comment explaining its role:

    self.memory = {
        "visited": set(),        # (r,c) cells the robot has stood on
        "obstacles": set(),      # (r,c) cells known to be 'X' / OOB
        "rewards": {},           # (r,c) -> -1 or 10, observed values
        "dirty_known": set(),    # (r,c) cells observed dirty and not yet sucked
        "clean_known": set(),    # (r,c) cells observed clean after SUCK
        "last_pos": None,        # (r,c) of previous step, for loop detection
        "last_action": None,     # str, previous action
        "step_count": 0,         # int, monotonic step counter
        "history": [],           # list of (step, pos, action, note) log entries
    }

### Explicit-update rules

`update_memory(percept)` MUST:

1. Be written as a sequence of small, named, commented steps — one
   logical update per block. No chained one-liners.
2. Append an entry to `self.memory["history"]` on EVERY step with:
   `(step_count, pos, last_action, <short human-readable note>)`.
   Example note: `"sensed obstacle at (1,1)"` or `"SUCK on dirty (0,0)"`.
3. Never overwrite `last_pos` / `last_action` before using them in the
   history log (order matters).
4. Add a `print()` (or a `log()` helper) that emits one line per update
   so the run is traceable in the terminal, e.g.:
   `[step 3] pos=(0,1) action=RIGHT → marked visited, sensed dirty=False`

### Explicit decision rules

`program(percept)` MUST:

1. Return via clearly separated `if/elif` branches, each with a comment
   naming the rule (e.g. `# Rule 2: move toward nearest known-dirty cell`).
2. When choosing an action, log WHY it was chosen:
   `[step 4] chose UP (reason: nearest dirty at (0,2), BFS next step)`
3. Never inline a lambda or a comprehension that hides a decision.

### Forbidden patterns

- `self.memory = {}` (empty dict, no schema)
- `self.memory["visited"].add(pos)` with no comment / no log entry
- Any `;`-joined or chained-assignment memory update
- Silent `try/except` that swallows a memory update
- Reassigning `self.memory = {...}` mid-run (mutate in place only)

### Required reference example (this is the style to match)

Include this snippet in the generated file as a style anchor:

    def update_memory(self, percept):
        pos = percept["pos"]

        # --- 1. Record current position as visited ---
        if pos not in self.memory["visited"]:
            self.memory["visited"].add(pos)
            self._log(pos, "visited")

        # --- 2. Record obstacles from neighbor senses ---
        for direction, cell in percept["neighbors"].items():
            nbr = self._neighbor_coord(pos, direction)
            if cell is None and nbr is not None:
                if nbr not in self.memory["obstacles"]:
                    self.memory["obstacles"].add(nbr)
                    self._log(pos, f"sensed obstacle at {nbr}")

        # --- 3. Record rewards observed ---
        for direction, cell in percept["neighbors"].items():
            nbr = self._neighbor_coord(pos, direction)
            if cell in (-1, 10) and nbr is not None:
                self.memory["rewards"][nbr] = cell
                self._log(pos, f"recorded reward {cell} at {nbr}")

        # --- 4. Track dirty / clean ---
        if percept["dirty"]:
            self.memory["dirty_known"].add(pos)
            self._log(pos, "observed dirty cell")
        else:
            self.memory["dirty_known"].discard(pos)
            self.memory["clean_known"].add(pos)
            self._log(pos, "observed clean cell")

        # --- 5. Update step log AFTER using last_pos/last_action ---
        self.memory["history"].append(
            (self.memory["step_count"], pos,
             self.memory["last_action"], "memory updated")
        )
        self.memory["last_pos"] = pos
        self.memory["step_count"] += 1

### Required helper methods

Define these explicitly (do not inline them):

- `_log(self, pos, note)` — appends to history and prints a trace line.
- `_neighbor_coord(self, pos, direction)` — returns the (r,c) one step
  in `direction`, or None if out of bounds.
- `_bfs_next_step(self, start, goal)` — returns the first action toward
  `goal`, using BFS over cells NOT in `self.memory["obstacles"]`.
