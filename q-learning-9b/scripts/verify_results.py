"""Sanity-check results.json against the environment rules.

Verification only: this script knows the grid and slip rules and solves the
environment with value iteration to compare against the learned policy. The
learner in q_learning.ipynb never sees any of this.

    python scripts/verify_results.py [path/to/results.json]

Exit code 1 if the recorded numbers are internally inconsistent, else 0.
Policy differences from optimal are reported but are not failures.
"""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
GRID = [['s', 0, 0, 0], [0, 'X', 0, 0], [0, 0, 0, 0], [0, -1, 0, 10]]
MOVES = {'Up': (-1, 0), 'Down': (1, 0), 'Left': (0, -1), 'Right': (0, 1)}
SIDEWAYS = {'Up': ('Right', 'Left'), 'Down': ('Left', 'Right'),
            'Left': ('Up', 'Down'), 'Right': ('Up', 'Down')}
TERMINAL = {(3, 3): 10, (3, 1): -1}
TOL = 1e-6


def step(state, action):
    r, c = state[0] + MOVES[action][0], state[1] + MOVES[action][1]
    ok = 0 <= r < 4 and 0 <= c < 4 and GRID[r][c] != 'X'
    return (r, c) if ok else state


def action_value(state, action, values, gamma, living):
    total = 0.0
    for prob, actual in ((0.8, action), (0.1, SIDEWAYS[action][0]), (0.1, SIDEWAYS[action][1])):
        nxt = step(state, actual)
        total += prob * (TERMINAL[nxt] if nxt in TERMINAL else living + gamma * values[nxt])
    return total


def solve(gamma, living):
    cells = [(r, c) for r in range(4) for c in range(4)
             if GRID[r][c] != 'X' and (r, c) not in TERMINAL]
    values = {s: 0.0 for s in cells}
    for _ in range(3000):
        values = {s: max(action_value(s, a, values, gamma, living) for a in MOVES) for s in cells}
    best = {s: max(MOVES, key=lambda a: action_value(s, a, values, gamma, living)) for s in cells}
    return values, best


def policy_value(policy, gamma, living):
    values = {s: 0.0 for s in policy}
    for _ in range(3000):
        values = {s: action_value(s, policy[s], values, gamma, living) for s in policy}
    return values


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'results.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    hp = data['hyperparameters']
    gamma, living = hp['GAMMA'], hp['LIVING_REWARD']
    problems = []

    print(f"Results recorded at {data.get('recorded_at', '?')}")
    for name in ('training_first_100', 'training_last_100', 'evaluation'):
        row = data[name]
        n = row['episodes']
        if row['goal'] + row['trap'] + row['timeout'] != n:
            problems.append(f'{name}: outcome counts do not add up to {n}')
        if row['timeout'] == 0 and row['trap'] == 0:  # all goals: reward is fixed by steps
            expected = 10 + living * (row['average_steps'] - 1)
            if abs(row['average_reward'] - expected) > 1e-3:
                problems.append(f"{name}: reward {row['average_reward']:.4f} != {expected:.4f} implied by steps")
        print(f"  {name}: goal {row['goal']}, trap {row['trap']}, timeout {row['timeout']}, "
              f"avg reward {row['average_reward']:.3f}, avg steps {row['average_steps']:.2f}")

    ev = data['evaluation']
    if abs(ev['success_rate'] - ev['goal'] / ev['episodes']) > TOL:
        problems.append('evaluation: success_rate does not match goal count')
    if ev['average_steps'] < 6:
        problems.append('evaluation: average steps below the 6-step shortest path')
    if ev['average_reward'] > 10 + living * 5 + TOL:
        problems.append('evaluation: average reward above the best possible 6-step reward')

    optimal_values, optimal = solve(gamma, living)
    learned = {tuple(int(x) for x in k.split(',')): v for k, v in data['policy'].items()}
    missing = sorted(set(optimal) - set(learned))
    if missing:
        print(f'  Unvisited cells with no learned action: {missing}')
    learned_values = policy_value({s: a for s, a in learned.items() if s in optimal}, gamma, living) \
        if not missing else None

    print('\nLearned action vs optimal action (discounted values):')
    differ = 0
    for s in sorted(optimal):
        if s not in learned:
            continue
        same = learned[s] == optimal[s]
        differ += not same
        note = '' if same else (f"  differs: optimal {optimal[s]} "
                                f"({action_value(s, optimal[s], optimal_values, gamma, living):.2f}) vs "
                                f"{learned[s]} ({action_value(s, learned[s], optimal_values, gamma, living):.2f})")
        print(f'  {s}: {learned[s]}{note}')
    print(f'\n{differ} of {len(learned)} learned actions differ from optimal.')
    print(f'Optimal value at start: {optimal_values[(0, 0)]:.3f}')
    if learned_values:
        print(f'Learned policy value at start: {learned_values[(0, 0)]:.3f}')

    if problems:
        print('\nINCONSISTENT:')
        for p in problems:
            print('  -', p)
        return 1
    print('\nResults are internally consistent.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
