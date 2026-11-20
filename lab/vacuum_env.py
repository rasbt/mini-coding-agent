"""4x4 vacuum robot gridworld environment.

Grid (row, col), start at top-left:

    S   0   0   0
    0   X   0   0
    0   0   0   0
    0  -1   0  10

Confirmed facts (context/vacuum-environment.md):
  - 4x4 grid, start (0,0), wall (1,1) not enterable.
  - (3,1) is a -1 terminal (pit), (3,3) is a +10 terminal (goal).
  - Actions up/down/left/right; bumping a wall or edge = stay in place.
  - Living reward -0.04.

Design decisions confirmed by the user (not in the assignment text):
  - Movement is stochastic and configurable: with probability p_intended the
    robot moves in the chosen direction, otherwise it slips to one of the two
    perpendicular directions with equal probability. Default p_intended = 0.8
    (0.8 / 0.1 / 0.1). p_intended = 1.0 gives deterministic movement.
  - Terminal rewards use a separate EXIT action: entering a terminal square is
    an ordinary move (living reward, done=False). In a terminal square the only
    legal action is EXIT, which pays +10 / -1 and ends the episode (done=True).
  - A bump (wall or edge) is an ordinary move: it pays the living reward.

The reward table and transition model are private to the environment. A
learning agent should only use reset(), legal_actions() and step().
"""

import random

UP, DOWN, LEFT, RIGHT, EXIT = "up", "down", "left", "right", "exit"
MOVE_ACTIONS = (UP, DOWN, LEFT, RIGHT)

_DELTAS = {UP: (-1, 0), DOWN: (1, 0), LEFT: (0, -1), RIGHT: (0, 1)}
_PERPENDICULAR = {
    UP: (LEFT, RIGHT),
    DOWN: (LEFT, RIGHT),
    LEFT: (UP, DOWN),
    RIGHT: (UP, DOWN),
}


class VacuumEnv:
    ROWS = 4
    COLS = 4
    START = (0, 0)
    WALLS = frozenset({(1, 1)})

    def __init__(self, p_intended=0.8, living_reward=-0.04, seed=None):
        if not 0.0 <= p_intended <= 1.0:
            raise ValueError("p_intended must be between 0 and 1")
        self.p_intended = p_intended
        self.living_reward = living_reward
        self._terminal_rewards = {(3, 1): -1.0, (3, 3): 10.0}
        self._rng = random.Random(seed)

    # ---- public interface -------------------------------------------------

    def reset(self):
        """Start a new episode; returns the start state."""
        return self.START

    def states(self):
        """All enterable cells (the wall is not a state)."""
        return [
            (r, c)
            for r in range(self.ROWS)
            for c in range(self.COLS)
            if (r, c) not in self.WALLS
        ]

    def is_terminal(self, state):
        return state in self._terminal_rewards

    def legal_actions(self, state):
        return (EXIT,) if self.is_terminal(state) else MOVE_ACTIONS

    def step(self, state, action):
        """Apply action in state. Returns (next_state, reward, done).

        After EXIT the episode is over and next_state is None.
        """
        if state not in self.states():
            raise ValueError(f"invalid state {state!r}")
        if action not in self.legal_actions(state):
            raise ValueError(f"action {action!r} not legal in state {state!r}")

        if action == EXIT:
            return None, self._terminal_rewards[state], True

        direction = self._sample_direction(action)
        return self._move(state, direction), self.living_reward, False

    # ---- private helpers -------------------------------------------------

    def _move(self, state, direction):
        dr, dc = _DELTAS[direction]
        r, c = state[0] + dr, state[1] + dc
        if not (0 <= r < self.ROWS and 0 <= c < self.COLS) or (r, c) in self.WALLS:
            return state  # bump: stay in place
        return (r, c)

    def _sample_direction(self, action):
        u = self._rng.random()
        if u < self.p_intended:
            return action
        left_slip, right_slip = _PERPENDICULAR[action]
        slip = (1.0 - self.p_intended) / 2.0
        return left_slip if u < self.p_intended + slip else right_slip
