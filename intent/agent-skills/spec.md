# Spec: mini-coding-agent can find and follow agent skills

Author: Catrina Coons. Status: draft (2026-11-16). Source: intent/agent-skills/intent.md

Constraints carried in: standard library only; keyword-based similarity; "ask" stays the default and skills never bypass approval; no behavior change when skills/ is absent; class skill format.

## Definitions

Skill: a folder skills/<name>/ (relative to the workspace repo root) that contains SKILL.md.

SKILL.md: a frontmatter block between --- lines with name and description (required) and keywords (optional, comma-separated), followed by a markdown body.

Skill terms: the keyword set built from a skill's name, description and keywords.

Prompt terms: the keyword set built from the user's request.

## Requirements <!-- numbered, so tests can cite them -->

### Discovery

R1. At startup, the agent loads every skills/*/SKILL.md under the workspace repo root. A skill with missing or broken frontmatter is skipped, and a warning is logged. The agent does not crash.

R2. If there is no skills/ folder, or it is empty, the agent behaves exactly as it did before: same prompt and same tools. All existing tests still pass.

R3. The stable prompt prefix includes a short "Available skills" list (name plus description only). This lets the model know which skills exist without loading their bodies.

### Similarity check (trigger 1: prompt time)

R4. At the start of every ask(), the user's request is checked against every skill before the first model call.

R5. Keywords are extracted the same way for the prompt and for each skill: lowercase the text, split on anything that isn't a letter or digit (so q-learning becomes q, learning), drop stopwords and tokens shorter than 2 characters, and strip a trailing plural s from tokens longer than 3 characters.

R6. Score = |prompt terms ∩ skill terms| / |prompt terms|. This is the share of the request's keywords that the skill covers, from 0.0 to 1.0. A skill matches when score ≥ threshold and it shares at least 2 keywords with the prompt. The threshold defaults to 0.25 and can be set with --skill-threshold.

R7. At most --max-skills matching skills are loaded (default 1), highest score first. Ties are broken by name, so the result is deterministic.

R8. Each matched skill's full body is added to the prompt in an "Active skills" section. It goes after the stable prefix and before memory and the transcript, and stays there for every model call in that ask(). Each body is limited to 3,000 characters.

R9. Matching is deterministic: the same request and the same skills always give the same scores and the same selection.

### Trigger 2: during execution

R10. A new tool, load_skill(name: str), is available and is not risky (it only reads a file). It returns the skill body, or an error that lists the valid names.

R11. A skill loaded with load_skill is added to the active set for the rest of the current ask(). Loading an already-active skill returns a short "already active" message and does not count as a repeated call.

R12. Delegated child agents run the same prompt-time check on their delegated task and can use load_skill. They stay read-only, and skills do not change that.

### Logging

R13. Every similarity check appends one JSON line to .mini-coding-agent/skill_log.jsonl with event: "similarity_check", timestamp, session_id, depth, trigger ("prompt"), prompt, threshold, scores (every skill: name, score rounded to 3 decimals, matched keywords) and selected (names, possibly empty).

R14. Every time a skill becomes active, whether from the check or from load_skill, one JSON line is appended with event: "skill_executed", timestamp, session_id, depth, trigger ("prompt" or "load_skill"), skill, path and score (null for load_skill).

R15. Skill activation is also printed as one console line, e.g. [skill] reward-design (score 0.43, prompt match). Logs are added to and never overwritten.

R16. The skill events are also recorded in the session history, so --resume and /memory show which skill was used.

### Safety

R17. Skills are instructions only. They never change the approval policy, tool risk levels, or path checks. Any risky action a skill asks for still goes through approve().

### Demonstration (the Lab)

R18. The repo contains four Lab skills: grid-validation, reward-design, transition-testing (from the earlier Lab, with paths updated to lab/vacuum-robot/) and a new q-learning-training.

R19. Using those skills, the agent builds the Lab in lab/vacuum-robot/:

An environment for the 4×4 grid: start (0,0), wall (1,1), −1 terminal (3,1), +10 terminal (3,3). It is deterministic. step(state, action) returns (next_state, reward, done) and does not expose R or T.

A Q-learning agent that learns only from step().

Tests.

A run that prints the learned Q-values and the greedy policy.

R20. Hyperparameters, with their reasons recorded in lab/vacuum-robot/context/vacuum-environment.md:

Parameter	Value	Justification

Living reward	−0.04	Small cost per step makes the robot prefer short paths without outweighing +10 or −1.

Discount γ	0.9	Long enough horizon for +10 to reach the start about 6 steps away, and still converges quickly.

Learning rate α	0.1	Stable updates. The environment is deterministic, so a modest rate converges reliably.

Epsilon ε	0.1	10% exploration. Can decay toward 0.01 over episodes so the final policy is greedy.

R21. The log from at least one real Lab run shows a prompt-time match and a load_skill activation, and that log is committed (or captured) as evidence.

Design

Where the code lives: a small SkillLibrary class in mini_coding_agent.py (the project keeps everything in one file). It handles discovery, parsing, keyword extraction, scoring and log writing. MiniAgent holds one instance.

When it triggers: (1) in ask(), right after the user message is recorded and before the loop starts; (2) when the model calls load_skill during the loop. This answers the class question "what is the exact moment the skills component is triggered?"

Prompt placement: prompt() becomes prefix → active skills → memory → transcript → request. The prefix only gets the short skill list (R3), so it stays stable and can still be reused from cache. Bodies change per request, so they sit outside the prefix.

Active set: stored for the current ask(). It is cleared at the start of the next ask() and then rebuilt by the new similarity check.

Frontmatter parsing: a minimal standard-library parser that reads key: value lines between the first two --- lines. Full YAML is not supported.

CLI: two new flags, --skill-threshold (float, default 0.25) and --max-skills (int, default 1). A new /skills REPL command lists the loaded skills.

Answers to the intent's open questions

"Similar enough" is defined by R5 and R6: share of prompt keywords covered, at least 2 shared keywords, threshold 0.25.

Several skills can load at once, but the default is 1 (R7). This keeps the prompt small for a 4B model.

The skill text goes after the prefix and before memory (R8).

Yes. A skill loaded mid-task stays active for the rest of that request (R11).

Yes. Delegated agents get skills and stay read-only (R12).

## Areas of concern <!-- each one has an owner -->

Keyword matching misses synonyms ("train the robot" vs "Q-learning"). The fix is the optional keywords: field in the skill frontmatter, plus load_skill as a fallback. Owner: Yulisa Medrano (skill author).

False positives on generic words ("test", "file"). The fix is the stopword list, the 2-shared-keyword minimum, and tuning the threshold against logged scores. Owner: Yulisa Medrano.

A small model ignores or partly follows a skill. Skills are advisory (R17). The fix is short, numbered rules that end in a check that leaves evidence, and the log shows whether the skill was loaded. Owner: Yulisa Medrano.

Prompt size. The default --max-new-tokens 512 and --max-steps 6 may be too small for the Lab, so the README documents the flags to raise for the Lab run. Owner: Yulisa Medrano.
Prompt injection through skill files. A skill can tell the model to run commands. Approval stays in force (R17), and the README says to review skills before using --approval auto. Owner: Catrina Coons (spec), Yulisa Medrano (README).
