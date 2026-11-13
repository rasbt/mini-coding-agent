# vacuum-world-agent — reference snippets (Lab 5)

## Percept format (what the agent receives every step)

```python
percept = {
    "pos": (row, col),          # 0-indexed, grid is 4x4
    "cell": 0,                  # 0, -1, 10, or "start"
    "dirty": False,             # True means the agent should SUCK
    "neighbors": {              # None = wall / out of bounds / obstacle "X"
        "UP": 0, "DOWN": None, "LEFT": None, "RIGHT": 0,
    },
}
```

## Direction table

```python
DIRECTIONS = {
    "UP": (-1, 0),
    "DOWN": (1, 0),
    "LEFT": (0, -1),
    "RIGHT": (0, 1),
}
GRID_SIZE = 4
```

## Helper methods (put these inside the agent class)

```python
    def _log(self, pos, note):
        """Append a history entry and print a trace line."""
        step = self.memory["step_count"]
        self.memory["history"].append((step, pos, self.memory["last_action"], note))
        print(f"[step {step}] pos={pos} action={self.memory['last_action']} -> {note}")

    def _neighbor_coord(self, pos, direction):
        """Return the (r, c) one step in direction, or None if out of bounds."""
        dr, dc = DIRECTIONS[direction]
        r, c = pos[0] + dr, pos[1] + dc
        if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
            return (r, c)
        return None

    def _bfs_next_step(self, start, goal):
        """Return the first action of a BFS path from start to goal, or None."""
        from collections import deque
        if start == goal:
            return None
        queue = deque([(start, None)])
        seen = {start}
        while queue:
            pos, first = queue.popleft()
            for direction in ("UP", "DOWN", "LEFT", "RIGHT"):
                nxt = self._neighbor_coord(pos, direction)
                if nxt is None or nxt in seen or nxt in self.memory["obstacles"]:
                    continue
                step = first or direction
                if nxt == goal:
                    return step
                seen.add(nxt)
                queue.append((nxt, step))
        return None
```

## Decision rule pattern (`program`)

```python
    def program(self, percept):
        """Return the next action using memory + percept."""
        pos = percept["pos"]
        self.update_memory(percept)

        # Rule 1: current cell is dirty -> SUCK
        if percept["dirty"]:
            action = "SUCK"
            self._log(pos, "chose SUCK (reason: current cell dirty)")
        # Rule 2: move toward a known dirty cell
        elif ...:
            ...
        # Rule 3: explore an unvisited, open neighbor
        elif ...:
            ...
        # Rule 4: BFS toward nearest unvisited known-safe cell
        elif ...:
            ...
        # Rule 5: any legal move
        else:
            ...
        self.memory["last_action"] = action
        return action
```

A neighbor is legal only if `percept["neighbors"][direction] is not None`.
Never return "UP"/"LEFT" from (0, 0).

## Q-learning update (Lab 5)

```python
new_q = old_q + alpha * (reward + gamma * max_future_q - old_q)
```
Epsilon-greedy: with probability epsilon pick a random valid action,
otherwise the action with the highest Q value (break ties randomly).
