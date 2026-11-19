"""PreToolUse guard hook for Lab 5.

Reads the hook JSON from stdin and:
  1. denies any access to the .env secrets file,
  2. denies edits to the separate Lab 4 submission,
  3. asks for confirmation before risky Bash commands.

Deny = exit code 2 with the reason on stderr. Ask = JSON on stdout.
"""

import json
import re
import sys

SAFE_ENV_SUFFIXES = ('.example', '.sample', '.template')
ENV_NAME = re.compile(r'(?:^|[\s/\\"\'=:])\.env(?P<suffix>\.[\w-]+)?(?=$|[\s/\\"\';|&<>)])', re.I)
LAB4_NAME = re.compile(r'lab[\s_-]*4', re.I)
MUTATING = re.compile(
    r'(\brm\b|\bmv\b|\bcp\b|\bsed\s+-i|\btee\b|>|\bgit\s+(checkout|restore|rm|mv)\b|'
    r'Remove-Item|Move-Item|Copy-Item|Set-Content|Out-File|Add-Content|Rename-Item|\bdel\b|\brmdir\b)',
    re.I)
RISKY = [
    (r'\bgit\s+push\b', 'git push publishes work to the shared remote'),
    (r'\bgit\s+reset\s+--hard\b', 'git reset --hard discards uncommitted work'),
    (r'\bgit\s+clean\b', 'git clean deletes untracked files'),
    (r'\bgit\s+checkout\s+(--\s|\.)', 'git checkout discards working-tree changes'),
    (r'\bgit\s+restore\b', 'git restore discards working-tree changes'),
    (r'\bgit\s+branch\s+-D\b', 'git branch -D force-deletes a branch'),
    (r'\brm\s+-[a-z]*[rf][a-z]*\b', 'rm with -r/-f deletes files irreversibly'),
    (r'Remove-Item\b[^|;]*-Recurse', 'Remove-Item -Recurse deletes a tree irreversibly'),
    (r'\b(rmdir|rd)\s+/s\b', 'rmdir /s deletes a tree irreversibly'),
]


def touches_env(text):
    for match in ENV_NAME.finditer(text):
        suffix = (match.group('suffix') or '').lower()
        if suffix not in SAFE_ENV_SUFFIXES:
            return True
    return False


def deny(reason):
    print(reason, file=sys.stderr)
    sys.exit(2)


def ask(reason):
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'ask',
        'permissionDecisionReason': reason}}))
    sys.exit(0)


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)  # unreadable input: do not block work

    tool = data.get('tool_name', '')
    tool_input = data.get('tool_input') or {}
    target = ' '.join(str(tool_input.get(k, '')) for k in ('file_path', 'notebook_path', 'path'))
    command = str(tool_input.get('command', ''))

    if touches_env(target) or touches_env(command):
        deny('Blocked: .env holds secrets and must not be read, edited, or committed.')

    if tool in ('Write', 'Edit', 'NotebookEdit') and LAB4_NAME.search(target):
        deny('Blocked: the Lab 4 submission is separate and must be preserved.')
    if tool in ('Bash', 'PowerShell') and LAB4_NAME.search(command) and MUTATING.search(command):
        deny('Blocked: this command appears to modify the Lab 4 submission, which must be preserved.')

    if tool in ('Bash', 'PowerShell'):
        for pattern, why in RISKY:
            if re.search(pattern, command, re.I):
                ask(f'Confirm risky command: {why}.')


if __name__ == '__main__':
    main()
