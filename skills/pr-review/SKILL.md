---
name: pr-review
description: Review a pull request or the current git diff for bugs, missing tests and risky changes, and write a short review.
triggers: pull request, pr review, review the pr, code review, review my diff, git diff
---

# Skill: pr-review

One tool call per reply.

1. Run `git status --short` and `git diff --stat` with run_shell to see what changed.
2. Run `git diff` (add a path if the diff is long) and read each changed hunk.
3. For each changed file, read the surrounding code with read_file when the
   hunk alone is not enough to judge it.
4. Check: logic errors, unhandled None / empty inputs, off-by-one, changed
   behaviour without a test, secrets or debug prints left in.
5. If tests exist, run them with run_shell (`python -m pytest -q`).
6. Reply with `<final>` containing:
   - **Summary** — one sentence on what the change does.
   - **Issues** — numbered, each with `file:line`, what is wrong, and a fix.
   - **Tests** — what ran and the result.
   - **Verdict** — approve / request changes.
