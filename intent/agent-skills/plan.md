# Plan: mini-coding-agent can find and follow agent skills

Author: Catrina Coons. Status: draft (2026-11-16). Source: intent/agent-skills/intent.md, intent/agent-skills/spec.md

## Files that change

mini_coding_agent.py: new SkillLibrary class; changes to MiniAgent.__init__, build_tools() (load_skill), build_prefix() (skill list), prompt() (active skills section), ask() (prompt-time check, reset active set) and tool_delegate() (child shares the library); build_agent() / build_arg_parser() (new flags); main() (/skills command); HELP_DETAILS.

tests/test_skills.py (new): unit tests that use FakeModelClient and tmp_path.

skills/grid-validation/SKILL.md, skills/reward-design/SKILL.md, skills/transition-testing/SKILL.md (ported, paths updated), skills/q-learning-training/SKILL.md (new).

lab/vacuum-robot/: context/vacuum-environment.md, environment.py, q_learning.py, tests/. The agent writes these during the demo run, not by hand.
README.md: a Project 2 section at the top.

logs/ (or a copy of .mini-coding-agent/skill_log.jsonl): the evidence from the Lab run.

## Order of work <!-- each step cites requirements -->

Failing tests first (tests/test_skills.py) for: discovery and skipping bad frontmatter (R1); no skills/ gives an unchanged prompt (R2); keyword extraction and the scoring math on a hand-computed example (R5, R6); threshold, top-k and tie order (R7, R9); the skill body appears in prompt() between prefix and memory (R8); load_skill works and rejects unknown names (R10, R11); log lines have every required field (R13, R14).

SkillLibrary: discovery and frontmatter parser, terms(text), score(prompt) that returns every skill's score and matched keywords, get(name), and log(event), which appends to .mini-coding-agent/skill_log.jsonl (R1, R5, R6, R9, R13, R14).

Wire up prompt time: in ask(), reset the active set, run the check, log it, activate the matches, print the console line, and record a history event (R4, R7, R15, R16). Add the active-skills section to prompt() (R8). Add the skill list to build_prefix() only when skills exist (R2, R3).

Wire up mid-task: add the load_skill tool (not risky) and its validation in validate_tool(), plus an example in tool_example(). Handle "already active" without tripping repeated_tool_call() (R10, R11, R14).

Delegation: pass the same SkillLibrary to the child agent in tool_delegate(). Assert that the child stays read_only with approval "never" (R12, R17).

CLI: add --skill-threshold, --max-skills and /skills, and update the help text (Design).

Skills: port the three Lab skills (fix paths to lab/vacuum-robot/, add keywords:), and write q-learning-training (R18).

Calibrate: run 8–10 realistic Lab prompts, read the scores in the log, and adjust the threshold or skill keywords until each prompt picks the right skill and off-topic prompts pick none. Record the final values in the README (R6, area of concern 1–2).

Run the Lab with the agent, a sequence of prompts at --approval ask, so the agent builds the environment, validates it, writes and runs the tests, records the hyperparameters, and trains Q-learning (R19, R20). Keep the log (R21).

README and video.

## Risks

The small model may not follow skill rules, or may write broken code. If so, break the Lab into smaller prompts, raise --max-steps and --max-new-tokens, or try a bigger Ollama model. Document whichever was used.

Adding a tool and a prefix section changes the prompt for every user. Mitigated by R2: with no skills, the prompt is byte-for-byte unchanged, and a test checks this.

Threshold tuning is guesswork. Mitigated by logging every skill's score, not just the winner, so tuning is based on data.

## Proof <!-- the tests that prove it is done -->

python -m pytest tests/ passes, both the original tests and test_skills.py (R1–R17).
.mini-coding-agent/skill_log.jsonl from the Lab run contains similarity_check lines with scores for all four skills, and skill_executed lines for both triggers (R13, R14, R21).
python -m pytest lab/vacuum-robot/tests passes, and python lab/vacuum-robot/q_learning.py prints a greedy policy that goes from (0,0) to (3,3) around the wall and avoids (3,1) (R19, R20).
