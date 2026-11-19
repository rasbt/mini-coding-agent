"""Compare Q-learning hyperparameters over several seeds.

Runs the notebook's own q_learning and evaluate_agent functions (definition
cells only; the driver cell is skipped). Training seeds and evaluation seeds
are disjoint. Nothing in the notebook or results.json is modified unless
--out is given.

    python scripts/sweep_hyperparameters.py
    python scripts/sweep_hyperparameters.py --alpha 0.05 0.1 0.3 --epsilon 0.1 0.2 --seeds 10
    python scripts/sweep_hyperparameters.py --out sweep_results.json
"""

import argparse
import contextlib
import io
import itertools
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / 'q_learning.ipynb'
DEFINITION_CELLS = ('imports', 'environment', 'parameters', 'learning-todos')


def load_notebook():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    cells = {c.get('id'): ''.join(c['source']) for c in json.loads(NOTEBOOK.read_text(encoding='utf-8'))['cells']}
    namespace = {'__name__': 'q_learning_sweep'}
    for cell_id in DEFINITION_CELLS:
        exec(compile(cells[cell_id], f'<{cell_id}>', 'exec'), namespace)
    return namespace


def main():
    ns = load_notebook()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--alpha', type=float, nargs='+', default=[0.05, ns['ALPHA'], 0.3])
    parser.add_argument('--epsilon', type=float, nargs='+', default=[0.05, ns['EPSILON'], 0.4])
    parser.add_argument('--gamma', type=float, nargs='+', default=[ns['GAMMA']])
    parser.add_argument('--episodes', type=int, default=ns['TRAIN_EPISODES'])
    parser.add_argument('--eval-episodes', type=int, default=ns['EVAL_EPISODES'])
    parser.add_argument('--seeds', type=int, default=5, help='number of independent training runs per setting')
    parser.add_argument('--out', help='optional JSON file for the full table')
    args = parser.parse_args()

    train_seeds = list(range(1000, 1000 + args.seeds))
    eval_seeds = list(range(2000, 2000 + args.seeds))
    assert not set(train_seeds) & set(eval_seeds)

    rows = []
    print(f"{args.seeds} seeds per setting, {args.episodes} training episodes, "
          f"{args.eval_episodes} evaluation episodes, living reward {ns['LIVING_REWARD']}\n")
    print(f"{'alpha':>6} {'epsilon':>8} {'gamma':>6} | {'success':>8} {'eval reward':>12} "
          f"{'eval steps':>11} {'train traps/100':>16} | success range")
    for alpha, epsilon, gamma in itertools.product(args.alpha, args.epsilon, args.gamma):
        success, reward, steps, late_traps = [], [], [], []
        for train_seed, eval_seed in zip(train_seeds, eval_seeds):
            env = ns['MDPEnvironment'](living_reward=ns['LIVING_REWARD'])
            q, training = ns['q_learning'](env, args.episodes, ns['MAX_STEPS'], alpha=alpha,
                                           gamma=gamma, epsilon=epsilon, seed=train_seed)
            with contextlib.redirect_stdout(io.StringIO()):
                summary = ns['evaluate_agent'](env, q, args.eval_episodes, ns['MAX_STEPS'],
                                               seed=eval_seed, show_paths=0)
            success.append(summary['success_rate'])
            reward.append(summary['average_reward'])
            steps.append(summary['average_steps'])
            late_traps.append(sum(r['outcome'] == 'trap' for r in training[-100:]))
        row = {'alpha': alpha, 'epsilon': epsilon, 'gamma': gamma,
               'success_mean': statistics.mean(success), 'success_min': min(success),
               'success_max': max(success), 'eval_reward_mean': statistics.mean(reward),
               'eval_steps_mean': statistics.mean(steps), 'late_traps_mean': statistics.mean(late_traps)}
        rows.append(row)
        print(f"{alpha:>6} {epsilon:>8} {gamma:>6} | {row['success_mean']:>8.1%} "
              f"{row['eval_reward_mean']:>12.2f} {row['eval_steps_mean']:>11.1f} "
              f"{row['late_traps_mean']:>16.1f} | {row['success_min']:.1%}-{row['success_max']:.1%}")

    best = max(rows, key=lambda r: (r['eval_reward_mean'], r['success_mean']))
    print(f"\nHighest mean evaluation reward: alpha {best['alpha']}, epsilon {best['epsilon']}, "
          f"gamma {best['gamma']} ({best['eval_reward_mean']:.2f}).")
    print("Differences between neighbouring settings may be within seed-to-seed noise; "
          "check the success range before drawing conclusions.")

    if args.out:
        Path(args.out).write_text(json.dumps({'train_seeds': train_seeds, 'eval_seeds': eval_seeds,
                                              'rows': rows}, indent=2), encoding='utf-8')
        print(f"Saved {args.out}")


if __name__ == '__main__':
    main()
