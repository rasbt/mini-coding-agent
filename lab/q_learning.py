"""Tabular Q-learning for the 4x4 vacuum robot.

The agent never reads the environment's reward table or transition model.
It only sees rewards and next states returned by env.step().

Run:  py q_learning.py  [--episodes N] [--p-intended P] [--seed S]
"""

import argparse
import random
from collections import defaultdict

from vacuum_env import DOWN, EXIT, LEFT, MOVE_ACTIONS, RIGHT, UP, VacuumEnv

# Hyperparameters from intent/agent-skills/spec.md
GAMMA = 0.9
ALPHA = 0.1
EPSILON = 0.1

# Training setup confirmed by the user
EPISODES = 5000
MAX_STEPS = 100
SEED = 0


class QLearningAgent:
    def __init__(self, alpha=ALPHA, gamma=GAMMA, epsilon=EPSILON, seed=None):
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.q = defaultdict(float)  # (state, action) -> value, starts at 0
        self._rng = random.Random(seed)

    def value(self, state, legal):
        return max(self.q[(state, a)] for a in legal)

    def greedy_action(self, state, legal):
        """Best action; ties broken by the order of `legal` (deterministic)."""
        return max(legal, key=lambda a: self.q[(state, a)])

    def choose_action(self, state, legal):
        """Epsilon-greedy; greedy ties broken at random."""
        if self._rng.random() < self.epsilon:
            return self._rng.choice(legal)
        best = self.value(state, legal)
        return self._rng.choice([a for a in legal if self.q[(state, a)] == best])

    def update(self, state, action, reward, next_state, done, next_legal):
        if done:
            target = reward
        else:
            target = reward + self.gamma * self.value(next_state, next_legal)
        key = (state, action)
        self.q[key] += self.alpha * (target - self.q[key])


def train(env, agent, episodes=EPISODES, max_steps=MAX_STEPS):
    """Run Q-learning. Returns the undiscounted return of each episode."""
    returns = []
    for _ in range(episodes):
        state = env.reset()
        total = 0.0
        for _ in range(max_steps):
            action = agent.choose_action(state, env.legal_actions(state))
            next_state, reward, done = env.step(state, action)
            next_legal = () if done else env.legal_actions(next_state)
            agent.update(state, action, reward, next_state, done, next_legal)
            total += reward
            if done:
                break
            state = next_state
        returns.append(total)
    return returns


# ---- text output -------------------------------------------------------

_ARROWS = {UP: "^", DOWN: "v", LEFT: "<", RIGHT: ">"}


def format_policy(env, agent):
    rows = []
    for r in range(env.ROWS):
        cells = []
        for c in range(env.COLS):
            s = (r, c)
            if s in env.WALLS:
                cells.append("#")
            elif env.is_terminal(s):
                cells.append("EXIT")
            else:
                cells.append(_ARROWS[agent.greedy_action(s, MOVE_ACTIONS)])
        rows.append(" ".join(f"{x:>5}" for x in cells))
    return "\n".join(rows)


def format_values(env, agent):
    rows = []
    for r in range(env.ROWS):
        cells = []
        for c in range(env.COLS):
            s = (r, c)
            if s in env.WALLS:
                cells.append(f"{'#':>7}")
            else:
                cells.append(f"{agent.value(s, env.legal_actions(s)):7.3f}")
        rows.append(" ".join(cells))
    return "\n".join(rows)


def format_q_table(env, agent):
    header = f"{'state':<8}" + "".join(f"{a:>9}" for a in MOVE_ACTIONS + (EXIT,))
    lines = [header]
    for s in env.states():
        legal = env.legal_actions(s)
        cells = [
            f"{agent.q[(s, a)]:9.3f}" if a in legal else f"{'-':>9}"
            for a in MOVE_ACTIONS + (EXIT,)
        ]
        lines.append(f"{str(s):<8}" + "".join(cells))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--episodes", type=int, default=EPISODES)
    parser.add_argument("--max-steps", type=int, default=MAX_STEPS)
    parser.add_argument(
        "--p-intended",
        type=float,
        default=0.8,
        help="probability the move goes in the chosen direction",
    )
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    env = VacuumEnv(p_intended=args.p_intended, seed=args.seed)
    agent = QLearningAgent(seed=args.seed + 1)
    returns = train(env, agent, args.episodes, args.max_steps)

    print(
        f"Q-learning: {args.episodes} episodes, gamma={GAMMA}, alpha={ALPHA}, "
        f"epsilon={EPSILON}, p_intended={args.p_intended}, seed={args.seed}"
    )
    last = returns[-100:]
    print(
        f"Average return over last {len(last)} episodes: {sum(last) / len(last):.3f}\n"
    )
    print("Q-table:")
    print(format_q_table(env, agent))
    print("\nGreedy policy:")
    print(format_policy(env, agent))
    print("\nState values  V(s) = max_a Q(s, a):")
    print(format_values(env, agent))


if __name__ == "__main__":
    main()
