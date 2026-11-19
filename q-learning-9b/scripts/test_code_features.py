"""Integration checks for the Lab 5 checker and hook, not the learning robot."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CodeFeatureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='lab5-features-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'project with spaces'
        self.root.mkdir()
        for name in ('scripts', '.claude', 'context'):
            shutil.copytree(ROOT / name, self.root / name, ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('CLAUDE.md', 'q_learning.ipynb'):
            shutil.copy2(ROOT / name, self.root / name)
        # The checker only checks presence; these fixtures never import AIMA.
        (self.root / 'aima').mkdir()
        for name in ('__init__.py', 'agents.py', 'utils.py'):
            (self.root / 'aima' / name).write_text('', encoding='utf-8')
        self.notebook = self.root / 'q_learning.ipynb'

    def run_check(self, payload=None):
        args = [sys.executable, str(self.root / 'scripts/check_project.py')]
        if payload is not None:
            args.append('--hook')
        return subprocess.run(args, input=json.dumps(payload) if payload is not None else None,
                              text=True, capture_output=True, timeout=20, cwd=self.root.parent)

    def append_cell(self, text):
        notebook = json.loads(self.notebook.read_text(encoding='utf-8'))
        notebook['cells'].append({'cell_type': 'code', 'source': [text]})
        self.notebook.write_text(json.dumps(notebook), encoding='utf-8')

    def event(self, key='notebook_path', path=None):
        return {'hook_event_name': 'PostToolUse', 'tool_name': 'NotebookEdit',
                'cwd': str(self.root), 'tool_input': {key: str(path or self.notebook)}}

    def test_starter_reports_incomplete_without_running_todos(self):
        self.append_cell('def unfinished_fixture():\n    raise NotImplementedError("TODO")\n')
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn('Unfinished TODO', result.stdout)
        self.assertIn('did not execute or train', result.stdout)

    def test_syntax_error_fails_cli_and_requests_hook_correction(self):
        self.append_cell('def broken(:\n')
        self.assertEqual(self.run_check().returncode, 1)
        result = self.run_check(self.event())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['decision'], 'block')

    def test_out_of_range_hyperparameter_fails(self):
        self.append_cell('EPSILON = 1.5\n')
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn('EPSILON must be between 0 and 1', result.stdout)

    def test_nonfinite_learning_rate_fails(self):
        self.append_cell('ALPHA = 1e999\n')
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn('ALPHA must be a finite number', result.stdout)

    def test_valid_hook_supports_both_tool_path_fields_and_spaces(self):
        for key in ('file_path', 'notebook_path'):
            result = self.run_check(self.event(key))
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            self.assertNotIn('decision', output)
            self.assertIn('Lab 5 checks: PASS', output['hookSpecificOutput']['additionalContext'])

    def test_hook_skips_files_outside_project(self):
        result = self.run_check(self.event(path=self.root.parent / 'outside.py'))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')

    def test_missing_skill_fails(self):
        (self.root / '.claude/skills/check-vacuum/SKILL.md').unlink()
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn('Missing file: .claude/skills/check-vacuum/SKILL.md', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
