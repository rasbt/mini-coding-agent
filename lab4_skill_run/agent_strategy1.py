"""Persistent Memory Vacuum Agent for Lab 4."""

from collections import deque

DIRECTIONS = {
    "UP": (-1, 0),
    "DOWN": (1, 0),
    "LEFT": (0, -1),
    "RIGHT": (0, 1),
}
GRID_SIZE = 4


class PersistentMemoryAgent:
    """Vacuum world agent using persistent memory architecture."""

    def __init__(self, env):
        """Initialize the agent with environment reference and memory schema."""
        self.env = env
        self.memory = {
            "visited": set(),  # (r,c) cells the robot has stood on
            "obstacles": set(),  # (r,c) cells known to be 'X' / OOB
            "rewards": {},  # (r,c) -> -1 or 10, observed values
            "dirty_known": set(),  # (r,c) cells observed dirty and not yet sucked
            "clean_known": set(),  # (r,c) cells observed clean after SUCK
            "last_pos": None,  # (r,c) of previous step, for loop detection
            "last_action": None,  # str, previous action
            "step_count": 0,  # int, monotonic step counter
            "history": [],  # list of (step, pos, action, note) log entries
        }

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

    def update_memory(self, percept):
        """Merge percept into memory with explicit update blocks."""
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

    def program(self, percept):
        """Return the next action using memory + percept."""
        pos = percept["pos"]
        self.update_memory(percept)

        # Rule 1: current cell is dirty -> SUCK
        if percept["dirty"]:
            action = "SUCK"
            self._log(pos, "chose SUCK (reason: current cell dirty)")
        # Rule 2: move toward a known dirty cell
        elif self.memory["dirty_known"]:
            goal = None
            for d in ("UP", "DOWN", "LEFT", "RIGHT"):
                nxt = self._neighbor_coord(pos, d)
                if nxt in self.memory["dirty_known"] and goal is None:
                    goal = nxt
                    break
            if goal is not None:
                action = self._bfs_next_step(pos, goal)
                if action is not None:
                    self._log(pos, f"chose {action} (reason: nearest dirty at {goal})")
            else:
                action = "NO-OP"
        # Rule 3: explore an unvisited, open neighbor
        elif self.memory["visited"]:
            for d in ("UP", "DOWN", "LEFT", "RIGHT"):
                nxt = self._neighbor_coord(pos, d)
                if nxt is not None and nxt not in self.memory["visited"] and nxt not in self.memory["obstacles"]:
                    action = d
                    self._log(pos, f"chose {d} (reason: unvisited neighbor)")
                    break
        # Rule 4: BFS toward nearest unvisited known-safe cell
        else:
            goal = None
            for d in ("UP", "DOWN", "LEFT", "RIGHT"):
                nxt = self._neighbor_coord(pos, d)
                if nxt is not None and nxt not in self.memory["visited"] and nxt not in self.memory["obstacles"]:
                    goal = nxt
                    break
            if goal is not None:
                action = self._bfs_next_step(pos, goal)
                if action is not None:
                    self._log(pos, f"chose {action} (reason: BFS toward unvisited)")
            else:
                action = "NO-OP"

        # Rule 5: any legal move
        if action is None:
            for d in ("UP", "DOWN", "LEFT", "RIGHT"):
                nxt = self._neighbor_coord(pos, d)
                if nxt is not None and nxt not in self.memory["obstacles"]:
                    action = d
                    self._log(pos, f"chose {d} (reason: random legal move)")
                    break

        self.memory["last_action"] = action
        return action


if __name__ == "__main__":
    class DummyVacuumWorld:
        """Minimal environment matching the lab's percept contract."""

        def __init__(self):
            self.grid = {
                (0, 0): "start",
                (0, 1): 0,
                (0, 2): 0,
                (0, 3): 0,
                (1, 0): 0,
                (1, 1): "X",
                (1, 2): 0,
                (1, 3): 0,
                (2, 0): 0,
                (2, 1): 0,
                (2, 2): 0,
                (2, 3): 0,
                (3, 0): 0,
                (3, 1): -1,
                (3, 2): 0,
                (3, 3): 10,
            }
            self.obstacles = {(1, 1)}
            self.dirty = {(0, 1), (2, 2), (3, 1)}
            self.pos = (0, 0)

        def percept(self):
            pos = self.pos
            cell = self.grid.get(pos, 0)
            dirty = pos in self.dirty
            neighbors = {}
            for direction, delta in {
                "UP": (-1, 0),
                "DOWN": (1, 0),
                "LEFT": (0, -1),
                "RIGHT": (0, 1),
            }.items():
                next_row = pos[0] + delta[0]
                next_col = pos[1] + delta[1]
                coord = (next_row, next_col)
                if next_row < 0 or next_row >= 4 or next_col < 0 or next_col >= 4:
                    neighbors[direction] = None
                elif coord in self.obstacles:
                    neighbors[direction] = None
                else:
                    neighbors[direction] = self.grid.get(coord, 0)
            return {"pos": pos, "cell": cell, "dirty": dirty, "neighbors": neighbors}

    env = DummyVacuumWorld()
    agent = PersistentMemoryAgent(env)
    print("Running demo for 30 steps...")
    for _ in range(30):
        percept = env.percept()
        action = agent.program(percept)
        print(f"Step {agent.memory['step_count']}: action={action}")
        env.pos = (env.pos[0] + DIRECTIONS[action][0], env.pos[1] + DIRECTIONS[action][1])
    print("Memory dict:")
    print(agent.memory)
