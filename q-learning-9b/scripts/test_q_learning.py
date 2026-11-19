"""Tests for the Q-learning code in q_learning.ipynb.

The notebook's definition cells are executed into a namespace; the driver cell
that trains and prints results is skipped. Run from the project root:

    python -m unittest scripts.test_q_learning -v
"""

import contextlib
import copy
import io
import json
from pathlib import Path
import random
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / 'q_learning.ipynb'
DEFINITION_CELLS = ('imports', 'environment', 'parameters', 'learning-todos', 'policy-display')
LEARNER_CELL = 'learning-todos'


def cell_source(cell_id):
    cells = json.loads(NOTEBOOK.read_text(encoding='utf-8'))['cells']
    for cell in cells:
        if cell.get('id') == cell_id:
            return ''.join(cell['source'])
    raise KeyError(cell_id)


def load_notebook_namespace():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    namespace = {'__name__': 'q_learning_notebook'}
    for cell_id in DEFINITION_CELLS:
        exec(compile(cell_source(cell_id), f'<{cell_id}>', 'exec'), namespace)
    return namespace


NS = load_notebook_namespace()
MDPEnvironment, Agent = NS['MDPEnvironment'], NS['Agent']
ACTIONS = NS['ACTIONS']


def new_robot(env):
    robot = Agent(lambda percept: None)
    env.reset(robot)
    return robot


class ScriptedEnv:
    """Deterministic stand-in environment: transitions[(state, action)] = (next, reward, done)."""

    def __init__(self, transitions, start='A'):
        self.transitions, self.start, self.state, self.done = transitions, start, start, False

    def reset(self, robot):
        self.state, self.done = self.start, False
        return self.state

    def execute_action(self, robot, action):
        self.state, reward, self.done = self.transitions[(self.state, action)]
        return self.state, reward, self.done


def every_action(state, nxt, reward, done):
    return {(state, a): (nxt, reward, done) for a in ACTIONS}


class EnvironmentTests(unittest.TestCase):
    def test_reset_returns_start_and_clears_score(self):
        env = MDPEnvironment()
        robot = Agent(lambda p: None)
        robot.performance = 5
        self.assertEqual(env.reset(robot), (0, 0))
        self.assertEqual((robot.location, robot.performance, robot.alive, env.done), ((0, 0), 0, True, False))

    def test_ordinary_and_blocked_moves_get_living_reward(self):
        env = MDPEnvironment(living_reward=-0.04)
        robot = new_robot(env)
        for _ in range(30):  # at the top-left corner, Up/Left are blocked or slip into walls
            loc, reward, done = env.execute_action(robot, 'Up')
            self.assertEqual((reward, done), (-0.04, False))
            self.assertIn(loc, [(0, 0), (0, 1)])
            robot.location = (0, 0)

    def test_terminal_cells_pay_exactly_their_reward_and_end_episode(self):
        for cell, expected_alive in ((10, True), (-1, False)):
            env = MDPEnvironment(env=[['start', cell]], living_reward=-0.5)
            env._attempt = lambda agent, intended, *_: intended(agent)  # no slips
            robot = new_robot(env)
            loc, reward, done = env.execute_action(robot, 'Right')
            self.assertEqual((loc, reward, done, robot.alive), ((0, 1), cell, True, expected_alive))

    def test_action_after_episode_end_raises(self):
        env = MDPEnvironment(env=[['start', 10]])
        env._attempt = lambda agent, intended, *_: intended(agent)
        robot = new_robot(env)
        env.execute_action(robot, 'Right')
        with self.assertRaises(RuntimeError):
            env.execute_action(robot, 'Right')
        env.reset(robot)  # reset makes it usable again
        env.execute_action(robot, 'Right')

    def test_unknown_action_raises(self):
        env = MDPEnvironment()
        with self.assertRaises(ValueError):
            env.execute_action(new_robot(env), 'Jump')

    def test_obstacle_is_never_entered(self):
        env = MDPEnvironment()
        random.seed(3)
        robot = new_robot(env)
        for _ in range(500):
            if env.done:
                env.reset(robot)
            loc, _, _ = env.execute_action(robot, random.choice(ACTIONS))
            self.assertNotEqual(loc, (1, 1))

    def test_slip_probabilities_are_80_10_10(self):
        env = MDPEnvironment()
        random.seed(0)
        counts = {}
        n = 20000
        for _ in range(n):
            robot = new_robot(env)
            robot.location = (2, 2)
            loc, _, _ = env.execute_action(robot, 'Right')
            env.done = False
            counts[loc] = counts.get(loc, 0) + 1
        self.assertEqual(set(counts), {(2, 3), (1, 2), (3, 2)})
        self.assertAlmostEqual(counts[(2, 3)] / n, 0.8, delta=0.015)
        self.assertAlmostEqual(counts[(1, 2)] / n, 0.1, delta=0.015)
        self.assertAlmostEqual(counts[(3, 2)] / n, 0.1, delta=0.015)


class ChooseActionTests(unittest.TestCase):
    choose = staticmethod(NS['choose_action'])

    def test_greedy_picks_best_action(self):
        q = {'s': {'Up': 0.0, 'Down': 1.0, 'Left': 0.5, 'Right': -1.0}}
        rng = random.Random(0)
        self.assertTrue(all(self.choose(q, 's', 0.0, rng) == 'Down' for _ in range(50)))

    def test_ties_are_broken_randomly_among_best_only(self):
        q = {'s': {'Up': 1.0, 'Down': 1.0, 'Left': 0.0, 'Right': 1.0}}
        rng = random.Random(0)
        picks = {self.choose(q, 's', 0.0, rng) for _ in range(200)}
        self.assertEqual(picks, {'Up', 'Down', 'Right'})

    def test_epsilon_one_explores_all_actions(self):
        q = {'s': {'Up': 9.0, 'Down': 0.0, 'Left': 0.0, 'Right': 0.0}}
        rng = random.Random(0)
        self.assertEqual({self.choose(q, 's', 1.0, rng) for _ in range(200)}, set(ACTIONS))

    def test_exploration_rate_roughly_matches_epsilon(self):
        q = {'s': {'Up': 9.0, 'Down': 0.0, 'Left': 0.0, 'Right': 0.0}}
        rng = random.Random(1)
        n = 20000
        non_greedy = sum(self.choose(q, 's', 0.2, rng) != 'Up' for _ in range(n)) / n
        self.assertAlmostEqual(non_greedy, 0.2 * 0.75, delta=0.02)  # 3 of 4 random picks are non-greedy

    def test_unseen_state_falls_back_to_random(self):
        rng = random.Random(0)
        self.assertEqual({self.choose({}, 'new', 0.0, rng) for _ in range(200)}, set(ACTIONS))


class OutcomeTests(unittest.TestCase):
    def test_labels(self):
        outcome_of = NS['outcome_of']
        self.assertEqual(outcome_of(10, True), 'goal')
        self.assertEqual(outcome_of(-1, True), 'trap')
        self.assertEqual(outcome_of(-0.04, False), 'timeout')


class QUpdateTests(unittest.TestCase):
    q_learning = staticmethod(NS['q_learning'])

    def test_terminal_update_does_not_bootstrap(self):
        env = ScriptedEnv(every_action('A', 'END', 10, True))
        q, results = self.q_learning(env, 1, 10, alpha=0.5, gamma=0.9, epsilon=0.0, seed=0)
        updated = [a for a in ACTIONS if q['A'][a] != 0.0]
        self.assertEqual(len(updated), 1)
        self.assertAlmostEqual(q['A'][updated[0]], 0.5 * 10)  # alpha * (reward - 0)
        self.assertNotIn('END', q)  # terminal state never gets its own entry
        self.assertEqual(results[0]['outcome'], 'goal')

    def test_nonterminal_update_bootstraps_from_next_state_max(self):
        transitions = {**every_action('A', 'B', -0.04, False), **every_action('B', 'END', 10, True)}
        env = ScriptedEnv(transitions)
        q, _ = self.q_learning(env, 2, 10, alpha=1.0, gamma=0.9, epsilon=0.0, seed=0)
        # episode 1: Q(B,*) becomes 10 for the chosen action; episode 2: Q(A,a) = -0.04 + 0.9 * 10
        self.assertAlmostEqual(max(q['B'].values()), 10.0)
        self.assertAlmostEqual(max(q['A'].values()), -0.04 + 0.9 * 10.0)

    def test_step_limit_gives_timeout(self):
        env = ScriptedEnv(every_action('A', 'A', -0.04, False))
        q, results = self.q_learning(env, 3, 7, seed=0)
        self.assertEqual([r['outcome'] for r in results], ['timeout'] * 3)
        self.assertEqual([r['steps'] for r in results], [7] * 3)
        self.assertAlmostEqual(results[0]['reward'], -0.04 * 7)

    def test_trap_outcome_recorded(self):
        env = ScriptedEnv(every_action('A', 'T', -1, True))
        _, results = self.q_learning(env, 2, 10, seed=0)
        self.assertEqual([r['outcome'] for r in results], ['trap', 'trap'])
        self.assertEqual(results[0]['reward'], -1)

    def test_same_seed_is_reproducible_and_different_seed_differs(self):
        env = MDPEnvironment()
        q1, r1 = self.q_learning(env, 200, 100, seed=5)
        q2, r2 = self.q_learning(env, 200, 100, seed=5)
        q3, r3 = self.q_learning(env, 200, 100, seed=6)
        self.assertEqual((q1, r1), (q2, r2))
        self.assertNotEqual(q1, q3)

    def test_one_result_per_episode(self):
        _, results = self.q_learning(MDPEnvironment(), 50, 100, seed=0)
        self.assertEqual([r['episode'] for r in results], list(range(1, 51)))


class EvaluationTests(unittest.TestCase):
    def trained(self):
        return NS['q_learning'](MDPEnvironment(), 1500, 100, seed=NS['TRAIN_SEED'])[0]

    def test_evaluation_does_not_change_q_values(self):
        q = self.trained()
        before = copy.deepcopy(q)
        with contextlib.redirect_stdout(io.StringIO()):
            NS['evaluate_agent'](MDPEnvironment(), q, 100, 100, seed=NS['EVAL_SEED'])
        self.assertEqual(q, before)

    def test_evaluation_summary_is_consistent(self):
        q = self.trained()
        with contextlib.redirect_stdout(io.StringIO()):
            s = NS['evaluate_agent'](MDPEnvironment(), q, 100, 100, seed=NS['EVAL_SEED'])
        self.assertEqual(s['goal'] + s['trap'] + s['timeout'], s['episodes'])
        self.assertAlmostEqual(s['success_rate'], s['goal'] / 100)

    def test_evaluation_is_greedy(self):
        # With a hand-built Q-table that always says Right and a no-slip world, the path is fixed.
        env = MDPEnvironment(env=[['start', 0, 10]])
        env._attempt = lambda agent, intended, *_: intended(agent)
        q = {(0, 0): {'Up': 0, 'Down': 0, 'Left': 0, 'Right': 1.0},
             (0, 1): {'Up': 0, 'Down': 0, 'Left': 0, 'Right': 1.0}}
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            s = NS['evaluate_agent'](env, q, 20, 10, seed=0, show_paths=1)
        self.assertEqual((s['goal'], s['average_steps']), (20, 2.0))
        self.assertIn('Right -> (0, 1) | Right -> (0, 2)', out.getvalue())

    def test_train_and_eval_seeds_are_separate(self):
        self.assertNotEqual(NS['TRAIN_SEED'], NS['EVAL_SEED'])


class PolicyTests(unittest.TestCase):
    def test_derive_policy_takes_argmax_per_state(self):
        q = {(0, 0): {'Up': 0.0, 'Down': 0.1, 'Left': 0.0, 'Right': 0.9}}
        self.assertEqual(NS['derive_policy'](q), {(0, 0): 'Right'})

    def test_print_policy_marks_walls_terminals_and_unvisited(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            NS['print_policy']({(0, 0): 'Right'})
        text = out.getvalue()
        for token in ('R', 'X', 'TRAP', 'RECHARGE', '?'):
            self.assertIn(token, text)


class LearningIntegrationTests(unittest.TestCase):
    """End-to-end check with the notebook's own hyperparameters."""

    @classmethod
    def setUpClass(cls):
        env = MDPEnvironment(living_reward=NS['LIVING_REWARD'])
        cls.q, cls.training = NS['q_learning'](
            env, NS['TRAIN_EPISODES'], NS['MAX_STEPS'], alpha=NS['ALPHA'], gamma=NS['GAMMA'],
            epsilon=NS['EPSILON'], seed=NS['TRAIN_SEED'])
        with contextlib.redirect_stdout(io.StringIO()):
            cls.summary = NS['evaluate_agent'](env, cls.q, NS['EVAL_EPISODES'], NS['MAX_STEPS'],
                                               seed=NS['EVAL_SEED'])

    def test_learned_policy_reaches_goal_most_of_the_time(self):
        self.assertGreaterEqual(self.summary['success_rate'], 0.9)

    def test_learned_policy_avoids_the_trap_cell(self):
        self.assertLessEqual(self.summary['trap'], 0.05 * self.summary['episodes'])

    def test_reward_improves_from_early_to_late_training(self):
        early = sum(r['reward'] for r in self.training[:100]) / 100
        late = sum(r['reward'] for r in self.training[-100:]) / 100
        self.assertGreater(late, early)

    def test_policy_next_to_goal_heads_to_goal(self):
        policy = NS['derive_policy'](self.q)
        self.assertEqual(policy[(2, 3)], 'Down')


class SpecComplianceTests(unittest.TestCase):
    def test_hyperparameters_in_valid_ranges(self):
        self.assertTrue(0 < NS['ALPHA'] <= 1)
        self.assertTrue(0 <= NS['GAMMA'] <= 1)
        self.assertTrue(0 <= NS['EPSILON'] <= 1)
        self.assertEqual(NS['EVALUATION_EPSILON'], 0.0)
        self.assertLess(NS['LIVING_REWARD'], 0)
        self.assertGreater(NS['MAX_STEPS'], 0)

    def test_learner_code_never_reads_simulator_internals(self):
        source = cell_source(LEARNER_CELL)
        for forbidden in ('.status', '_attempt', 'find_recharge_location', 'default_world', 'living_reward'):
            self.assertIsNone(re.search(re.escape(forbidden), source), forbidden)


if __name__ == '__main__':
    unittest.main()
