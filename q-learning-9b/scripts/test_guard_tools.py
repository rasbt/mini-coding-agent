"""Tests for the PreToolUse guard hook (scripts/guard_tools.py)."""

import json
from pathlib import Path
import subprocess
import sys
import unittest

GUARD = Path(__file__).resolve().parent / 'guard_tools.py'


def run_guard(tool, **tool_input):
    result = subprocess.run([sys.executable, str(GUARD)], text=True, capture_output=True, timeout=10,
                            input=json.dumps({'tool_name': tool, 'tool_input': tool_input}))
    return result.returncode, result.stdout


class GuardTests(unittest.TestCase):
    def assertDenied(self, tool, **tool_input):
        self.assertEqual(run_guard(tool, **tool_input)[0], 2, (tool, tool_input))

    def assertAllowed(self, tool, **tool_input):
        code, out = run_guard(tool, **tool_input)
        self.assertEqual((code, out), (0, ''), (tool, tool_input))

    def assertAsks(self, tool, **tool_input):
        code, out = run_guard(tool, **tool_input)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['hookSpecificOutput']['permissionDecision'], 'ask')

    def test_env_file_denied(self):
        self.assertDenied('Read', file_path='C:\\proj\\.env')
        self.assertDenied('Edit', file_path='proj/.env.local')
        self.assertDenied('Bash', command='cat .env')
        self.assertDenied('PowerShell', command='Get-Content ./.env')
        self.assertDenied('Bash', command='git add .env')

    def test_env_lookalikes_allowed(self):
        self.assertAllowed('Read', file_path='proj/.env.example')
        self.assertAllowed('Read', file_path='proj/.envrc.md')
        self.assertAllowed('Bash', command='echo environment')
        self.assertAllowed('Read', file_path='proj/dotenv.py')

    def test_lab4_protected(self):
        self.assertDenied('Edit', file_path='proj/Lab4/solution.py')
        self.assertDenied('Write', file_path='proj/lab 4/notes.md')
        self.assertDenied('Bash', command='rm -r lab4')
        self.assertAllowed('Read', file_path='proj/Lab4/solution.py')
        self.assertAllowed('Bash', command='ls lab4')

    def test_risky_bash_asks(self):
        self.assertAsks('Bash', command='git push origin main')
        self.assertAsks('Bash', command='git reset --hard HEAD~1')
        self.assertAsks('Bash', command='rm -rf build')
        self.assertAsks('PowerShell', command='Remove-Item build -Recurse -Force')

    def test_normal_work_allowed(self):
        self.assertAllowed('Bash', command='git status')
        self.assertAllowed('Edit', file_path='q_learning.ipynb')
        self.assertAllowed('Read', file_path='context/environment.md')

    def test_bad_input_does_not_block(self):
        result = subprocess.run([sys.executable, str(GUARD)], text=True, capture_output=True, input='not json')
        self.assertEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
