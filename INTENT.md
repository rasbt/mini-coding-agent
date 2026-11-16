Intent: mini-coding-agent can find and follow agent skills

Author: Catrina Coons. Status: draft (2026-11-16).

Problem <!-- what can't be done today -->

mini-coding-agent has five of the six components covered in class (repo context, prompt shape, tools and permissions, context reduction, memory, delegation), but it has no agent skills component. When we solved the vacuum-robot Lab, we wrote skills (grid-validation, reward-design, transition-testing) that capture the rules the work must follow. mini-coding-agent cannot use them. It does not know a skills/ folder exists. It cannot tell when a request needs one of these skills, and it has no way to load a skill's instructions into what the model sees. So every prompt has to restate those rules by hand, or they get ignored.

There is also no record of whether a skill was considered or used. So we cannot show, or debug, why the agent did or did not follow a skill.

Proposed outcome <!-- what better looks like -->
The agent finds skill folders such as skills/pr-review/SKILL.md in the workspace.
When a user prompt matches a skill's description closely enough, the agent puts that skill's instructions into the prompt and follows them. Nobody has to name the skill.
If the agent realizes partway through a task that it needs a skill, it can load that skill on its own.
Every decision is logged: the prompt, the similarity check (each skill's score), and which skill ran.
To prove it works, the agent uses our Lab skills to build the vacuum-robot environment and train a Q-learning agent on it.
Affected users and systems
Anyone running mini-coding-agent who wants repeatable, rule-following behavior on a recurring kind of task.
MiniAgent.ask() / prompt() (where the prompt is assembled), build_tools() (a new tool), and .mini-coding-agent/ (where the new log goes).
The default local model (qwen3.5:4b) is small. Whatever we build has to work with a model that has a short context and weak reasoning.
Constraints <!-- non-negotiables -->
Python standard library only. No new pip dependencies, and no embedding model.
The similarity check uses keyword matching, the approach used in class.
"ask" stays the default approval policy. Skills never bypass approval.
Existing behavior and existing tests keep working when there is no skills/ folder.
Skills use the format from class: YAML frontmatter (name, description), then numbered, checkable rules, ending with a check that leaves evidence.
Out of scope
Embedding or LLM-based semantic matching.
Hooks or CI checks that enforce skill rules. Skills stay advisory.
Downloading or sharing skills between repositories.
Open questions <!-- carried into spec.md -->
What exactly counts as "similar enough"? Which words are compared, how is the score computed, and what is the threshold?
Should more than one skill be able to load for the same prompt?
Where in the prompt does the skill text go so it doesn't break prompt-prefix reuse?
When the model loads a skill mid-task, does that skill stay active for the rest of the request?
Do delegated child agents get skills too?
