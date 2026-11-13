import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agent_strategy1 import PersistentMemoryAgent

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


def test_memory_schema_is_initialized():
    agent = PersistentMemoryAgent(DummyVacuumWorld())

    assert set(agent.memory) == {
        "visited",
        "obstacles",
        "rewards",
        "dirty_known",
        "clean_known",
        "last_pos",
        "last_action",
        "step_count",
        "history",
    }
    assert agent.memory["visited"] == set()
    assert agent.memory["obstacles"] == set()
    assert agent.memory["rewards"] == {}
    assert agent.memory["dirty_known"] == set()
    assert agent.memory["clean_known"] == set()
    assert agent.memory["last_pos"] is None
    assert agent.memory["last_action"] is None
    assert agent.memory["step_count"] == 0
    assert agent.memory["history"] == []


def test_update_memory_records_obstacles_and_dirty_state():
    env = DummyVacuumWorld()
    env.pos = (1, 0)
    agent = PersistentMemoryAgent(env)
    percept = env.percept()

    agent.update_memory(percept)

    assert (1, 0) in agent.memory["visited"]
    assert (1, 1) in agent.memory["obstacles"]
    assert (1, 0) in agent.memory["clean_known"]
    assert len(agent.memory["history"]) >= 1
    assert agent.memory["step_count"] == 1


def test_agent_sucks_when_current_cell_is_dirty():
    env = DummyVacuumWorld()
    env.pos = (0, 1)
    agent = PersistentMemoryAgent(env)
    percept = env.percept()

    action = agent.program(percept)

    assert action == "SUCK"


def test_agent_avoids_known_obstacles_and_moves_legally():
    env = DummyVacuumWorld()
    env.pos = (0, 0)
    agent = PersistentMemoryAgent(env)
    percept = env.percept()
    agent.update_memory(percept)

    action = agent.program(percept)

    assert action in {"DOWN", "RIGHT"}
    assert action != "UP"
    assert action != "LEFT"


def test_bfs_next_step_for_reachable_target():
    env = DummyVacuumWorld()
    agent = PersistentMemoryAgent(env)
    agent.memory["obstacles"] = {(1, 1)}

    assert agent._bfs_next_step((0, 0), (0, 3)) == "RIGHT"
    assert agent._bfs_next_step((0, 0), (3, 0)) == "DOWN"