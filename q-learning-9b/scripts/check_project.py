"""Check Lab 5 source without executing notebook cells or training the robot."""

import argparse
import ast
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = ('LIVING_REWARD', 'GAMMA', 'ALPHA', 'EPSILON', 'EVALUATION_EPSILON')


def check_project(root=ROOT):
    errors, notes, parameters, code = [], [], {}, []
    try:
        notebook = json.loads((root / 'q_learning.ipynb').read_text(encoding='utf-8'))
        if notebook.get('nbformat') != 4 or not isinstance(notebook.get('cells'), list):
            raise ValueError('Expected a version 4 notebook with a cells list')
        for number, cell in enumerate(notebook['cells'], 1):
            if cell.get('cell_type') != 'code':
                continue
            source = cell.get('source', [])
            if not isinstance(source, (str, list)) or (isinstance(source, list) and not all(isinstance(s, str) for s in source)):
                raise ValueError(f'Cell {number} has invalid source')
            text = source if isinstance(source, str) else ''.join(source)
            try:
                tree = ast.parse(text, filename=f'q_learning.ipynb cell {number}')
                compile(tree, f'q_learning.ipynb cell {number}', 'exec')
            except SyntaxError as exc:
                errors.append(f'Cell {number}, line {exc.lineno}: {exc.msg}')
                continue
            code.append(text)
            # Read literal top-level assignments; never execute notebook code.
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id in PARAMETERS:
                            try:
                                parameters[target.id] = ast.literal_eval(node.value)
                            except (ValueError, TypeError):
                                errors.append(f'{target.id} must be a numeric literal for this checker')
            for node in ast.walk(tree):
                if isinstance(node, ast.Raise) and node.exc is not None:
                    exc = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
                    if isinstance(exc, ast.Name) and exc.id == 'NotImplementedError':
                        notes.append(f'Unfinished TODO: cell {number}, line {node.lineno}')
        if not code:
            errors.append('Notebook contains no valid Python code cells')
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        errors.append(f'Cannot read notebook: {exc}')

    for name in PARAMETERS:
        value = parameters.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            errors.append(f'{name} must be a finite number')
        elif name == 'GAMMA' and not 0 <= value < 1:
            errors.append('GAMMA must be at least 0 and below 1')
        elif name == 'ALPHA' and not 0 < value <= 1:
            errors.append('ALPHA must be above 0 and at most 1')
        elif name in ('EPSILON', 'EVALUATION_EPSILON') and not 0 <= value <= 1:
            errors.append(f'{name} must be between 0 and 1')

    for path in (root / 'scripts').rglob('*.py'):
        try:
            compile(path.read_text(encoding='utf-8'), str(path), 'exec')
        except (OSError, SyntaxError) as exc:
            errors.append(f'{path.relative_to(root)}: {exc}')

    required = [
        'CLAUDE.md', 'context/environment.md', 'context/requirements.md',
        'aima/__init__.py', 'aima/agents.py', 'aima/utils.py',
        '.claude/settings.json', '.claude/skills/check-vacuum/SKILL.md',
        '.claude/agents/environment-specialist.md',
        '.claude/agents/requirements-specialist.md',
        '.claude/agents/configuration-reviewer.md',
    ]
    for name in required:
        if not (root / name).is_file():
            errors.append(f'Missing file: {name}')
    try:
        settings = json.loads((root / '.claude/settings.json').read_text(encoding='utf-8'))
        if not settings.get('hooks', {}).get('PostToolUse'):
            errors.append('PostToolUse hook is missing from settings')
    except (OSError, ValueError, AttributeError) as exc:
        errors.append(f'Cannot read hook settings: {exc}')
    if notes:
        notes.append('The Q-learning solution is unfinished; passing checks is not a training result.')
    return {'errors': errors, 'notes': notes, 'parameters': parameters}


def summary(report):
    lines = ['Lab 5 checks: ' + ('FAIL' if report['errors'] else 'PASS')]
    lines += ['ERROR: ' + item for item in report['errors']]
    lines += ['NOTE: ' + item for item in report['notes']]
    lines += [f'{name}={value}' for name, value in report['parameters'].items()]
    lines.append('Checked syntax, parameter ranges, and required files; did not execute or train the notebook.')
    return '\n'.join(lines)


def run_hook():
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError('Expected an object')
        data = payload.get('tool_input', {})
        if not isinstance(data, dict):
            raise ValueError('Expected tool_input to be an object')
        filename = data.get('file_path') or data.get('notebook_path')
        if not filename:
            return 0
        path = Path(filename)
        if not path.is_absolute():
            path = Path(payload.get('cwd', str(ROOT))) / path
        try:
            relative = path.resolve().relative_to(ROOT.resolve())
        except ValueError:
            return 0
        if not relative.parts or relative.parts[0] in ('aima', '.git', '.venv', 'venv'):
            return 0
        if path.suffix.lower() not in ('.py', '.ipynb', '.json', '.md'):
            return 0
    except (ValueError, TypeError, OSError) as exc:
        print(f'Invalid Lab 5 hook input: {exc}', file=sys.stderr)
        return 2
    report = check_project()
    output = {'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': summary(report)}}
    if report['errors']:
        # PostToolUse runs after the edit. This asks Claude to fix the errors;
        # it does not undo or prevent the edit that already happened.
        output.update(decision='block', reason='Lab 5 checks failed. Fix the reported errors before continuing.')
    print(json.dumps(output))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hook', action='store_true', help='Read a Claude Code PostToolUse event from stdin')
    options = parser.parse_args()
    if options.hook:
        return run_hook()
    report = check_project()
    print(summary(report))
    return 1 if report['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
