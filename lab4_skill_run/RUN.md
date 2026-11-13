# Lab 4 solved by the mini agent using the Lab 5 skill

This folder is the workspace after the final run (run 3) described in
[`../sdlc/05-verification.md`](../sdlc/05-verification.md).

| File | Origin |
|------|--------|
| `spec.md`, `Test/test.py` | copied from `Lab4-PersistentMemory-CS440` (input) |
| `README.md` | two-line workspace README (input) |
| `agent_strategy1.py` | **written by the mini agent** (qwen3.5:4b) |
| `logs/skills.jsonl` | skill component log: discover → prompt → similarity_check → skill_executed |
| `logs/console_stderr.txt` | `[skills]` console log lines |
| `logs/console_stdout.txt` | agent banner + final answer |
| `logs/session.json` | full transcript (user, skill activation, tool calls, final) |
| `logs/earlier_iterations/` | evidence from runs 1 and 2 |

Check it:

```bash
python -m pytest -q Test/test.py
```
