&nbsp;
# Mini-Coding-Agent

This folder contains a small standalone coding agent:

- code: `mini_coding_agent.py`
- CLI: `mini-coding-agent`

It is a minimal local agent loop with:

- workspace snapshot collection
- stable prompt plus turn state
- structured tools
- approval handling for risky tools
- transcript and memory persistence
- bounded delegation

The model backend is currently based on Ollama.

<a href="https://magazine.sebastianraschka.com/p/components-of-a-coding-agent">
  <img src="https://substack-post-media.s3.amazonaws.com/public/images/49b97718-57f4-4977-99c8-8ad5c4d32af3_1548x862.png" width="500px">
</a>

<br>

**[The detailed tutorial: Components of a Coding Agent](https://magazine.sebastianraschka.com/p/components-of-a-coding-agent)**


&nbsp;
## Seven Components

<a href="https://magazine.sebastianraschka.com/p/components-of-a-coding-agent">
  <img alt="Six core components of a coding agent" src="https://sebastianraschka.com/images/github/mini-coding-agent/six-components.webp" width="500px">
</a>

This coding harness is organized around seven components:

1. **Live repo context**  
   The agent collects stable workspace facts upfront, such as repo layout, instructions, and git state.
2. **Prompt shape and cache reuse**  
   A stable prompt prefix, which is separate from the changing request, transcript, and memory so repeated model calls can reuse the static parts efficiently.
3. **Structured tools, validation, and permissions**  
   The model works through named tools with checked inputs, workspace path validation, and approval gates instead of free-form arbitrary actions.
4. **Context reduction and output management**  
   Long outputs are clipped, repeated reads are deduplicated, and older transcript entries are compressed to keep prompt size under control.
5. **Transcripts, memory, and resumption**  
   The runtime keeps both a full durable transcript and a smaller working memory so sessions can be resumed while preserving important state via working memory.
6. **Delegation and bounded subagents**  
   Scoped subtasks can be delegated to helper agents that inherit enough context to help (but operate within limits).
7. **Agent skills** discover skill folders, select an applicable skill, add its instructions to the model prompt, and log the decision.

## CS440 Project 2

| Path | Purpose |
| --- | --- |
| `mini_coding_agent.py` | Agent loop, skill discovery and matching, `use_skill` tool, and logs |
| `.claude/skills/` | Original Lab 5 skills |
| `intent/` | SDLC intent, specification, and implementation plan |
| `q-learning-9b/` | Vacuum robot demo, notebook, tests, and saved results |
| `tests/` | Agent and skill regression tests |

The agent searches the target repository root for one-level skill folders under
`skills/`, `skill/`, and `.claude/skills/`. Each folder contains `SKILL.md`
or `skill.md`. The registry reads the name, description, and optional keywords.
It scores the prompt against each skill's metadata using word-count cosine
similarity and selects the best score at or above 0.25. A `/skill-name` prompt
or a model call to `use_skill` selects by exact name. The skill body is
included in subsequent model prompts for that turn. The model follows it with
the agent's existing tools and approval rules.

### Vacuum robot demonstration

The `q-learning-9b/` folder inside this repository contains a copy of CS440 Lab 5
with its original `check-vacuum` skill and simulator. The demo workspace contains
`learning_todos.py`, `q_learning.ipynb`, and `q_learning_demo.py` alongside
the simulator and tests. From the repository root, install the demo dependencies
and verify the included implementation:

```powershell
python -m pip install -r q-learning-9b/requirements.txt
Push-Location .\q-learning-9b
python q_learning_demo.py verify
Pop-Location
```

To open the included demo workspace in the agent, start Ollama per the
[requirements](#requirements) and run this from the repository root:

```powershell
python mini_coding_agent.py --cwd q-learning-9b --approval ask --max-steps 15 --max-new-tokens 2048
```

To start from TODOs, run `python q_learning_demo.py prepare` inside a fresh
disposable demo checkout that has the notebook and helper but no
`learning_todos.py`. Preparation generates the learner starter, clears
notebook outputs, and removes any existing `results.json` from that checkout.
Launch the agent from the repository root and pass that checkout's path to
`--cwd`. At the agent prompt, enter `/skills` to verify discovery. Then try:

> Check the Lab 5 notebook for the vacuum robot and use focused specialists to review the environment, requirements, and code features. To solve the Lab 4 vacuum robot problem, implement the five Q-learning TODOs in learning_todos.py. Read the environment and tests for the expected interfaces. Use only observations from the simulator. Then run python q_learning_demo.py verify and report the results. Keep the simulator and tests intact.

Review the tool arguments when the agent requests approval. Approve the
checker command, learner-file edits, and verification command if they match the
task. The verification command copies the learner into the notebook,
runs the checker and Q-learning tests, then trains and evaluates if those
checks succeed. A syntax checker pass can still contain unfinished TODOs.
The `verify` command writes fresh `results.json` only after successful training
and evaluation. To trigger the skill explicitly, prefix the prompt with
`/check-vacuum`.

To display the skill log from a run in the included demo workspace, open a
second terminal at the repository root:

```powershell
Get-Content -LiteralPath '.\q-learning-9b\.mini-coding-agent\skills.log' |
  ForEach-Object { $_ | ConvertFrom-Json } |
  Where-Object { $_.depth -eq 0 } |
  ConvertTo-Json -Depth 6
```

Show the `prompt`, `similarity_check`, and `skill_executed` records for the
same session. The execution record means the instructions were activated.
Use the tool calls, the source diff, and the test or training output to show
what the agent completed and what remains.
Logs store prompt text locally. Delegated calls have their own session IDs and
`depth: 1` records.

To run the automated tests from the agent repository:

```powershell
python -m pip install -e . pytest
python -m pytest -q
```

&nbsp;
## Requirements

You need:

- Python 3.10+
- Ollama installed
- an Ollama model pulled locally

Optional:

- `uv` for environment management and the `mini-coding-agent` CLI entry point

This project has no Python runtime dependency beyond the standard library, so you can run it directly with `python mini_coding_agent.py` if you do not want to use `uv`.

&nbsp;
## Install Ollama

Install Ollama on your machine so the `ollama` command is available in your shell.

Official installation link: [ollama.com/download](https://ollama.com/download)

Then verify:

```bash
ollama --help
```

Start the server:

```bash
ollama serve
```

In another terminal, pull a model. Example:

```bash
ollama pull qwen3.5:4b
```

Qwen 3.5 model library:

- [ollama.com/library/qwen3.5](https://ollama.com/library/qwen3.5)

The default in this project is `qwen3.5:4b`. If you have sufficient memory, it is worth trying a larger model such as `qwen3.5:9b` or another larger Qwen 3.5 variant. The agent just sends prompts to Ollama's `/api/generate` endpoint.

&nbsp;
## Project Setup

Clone the repo or your fork and change into it:

```bash
git clone https://github.com/rasbt/mini-coding-agent.git
cd mini-coding-agent
```

If you forked it first, use your fork URL instead:

```bash
git clone https://github.com/<your-github-user>/mini-coding-agent.git
cd mini-coding-agent
```



&nbsp;
## Basic Usage

Start the agent:

```bash
cd mini-coding-agent
uv run mini-coding-agent
```

Without `uv`, run the script directly:

```bash
cd mini-coding-agent
python mini_coding_agent.py
```

By default it uses:

- model: `qwen3.5:4b`
- approval: `ask`

For a concrete usage example, see [EXAMPLE.md](EXAMPLE.md).

&nbsp;
## Approval Modes

Risky tools such as shell commands and file writes are gated by approval.

- `--approval ask`
  prompts before risky actions (default and recommended)
- `--approval auto`
  allows risky actions automatically, including arbitrary command execution and file writes by the model; use only with trusted prompts and trusted repositories
- `--approval never`
  denies risky actions

Example:

```bash
uv run mini-coding-agent --approval auto
```



&nbsp;
## Resume Sessions

The agent saves sessions under the target workspace root in:

```text
.mini-coding-agent/sessions/
```

Resume the latest session:

```bash
uv run mini-coding-agent --resume latest
```


Resume a specific session:

```bash
uv run mini-coding-agent --resume 20260401-144025-2dd0aa
```


&nbsp;
## Interactive Commands

Inside the REPL, slash commands are handled directly by the agent instead of
being sent to the model as a normal task.

- `/help`
  shows the list of available interactive commands
- `/memory`
  prints the distilled session memory, including the current task, tracked files, and notes
- `/session`
  prints the path to the current saved session JSON file
- `/reset`
  clears the current session history and distilled memory but keeps you in the REPL
- `/exit`
  exits the interactive session
- `/quit`
  exits the interactive session; alias for `/exit`

&nbsp;
## Main CLI Flags

```bash
uv run mini-coding-agent --help
```

Without `uv`:

```bash
python mini_coding_agent.py --help
```

CLI flags are passed before the agent starts. Use them to choose the workspace,
model connection, resume behavior, approval mode, and generation limits.

Important flags:

- `--cwd`
  sets the workspace directory the agent should inspect and modify; default: `.`
- `--model`
  selects the Ollama model name, such as `qwen3.5:4b`; default: `qwen3.5:4b`
- `--host`
  points the agent at the Ollama server URL (usually not needed); default: `http://127.0.0.1:11434`
- `--ollama-timeout`
  controls how long the client waits for an Ollama response (usually not needed); default: `300` seconds
- `--resume`
  resumes a saved session by id or uses `latest`; default: start a new session
- `--approval`
  controls how risky tools are handled: `ask`, `auto`, or `never`; default: `ask`
- `--max-steps`
  limits how many model and tool turns are allowed for one user request; default: `6`
- `--max-new-tokens`
  caps the model output length for each step; default: `512`
- `--temperature`
  controls sampling randomness; default: `0.2`
- `--top-p`
  controls nucleus sampling for generation; default: `0.9`

&nbsp;
## Example

See [EXAMPLE.md](EXAMPLE.md)

&nbsp;
## Notes & Tips

- The agent expects the model to emit either `<tool>...</tool>` or `<final>...</final>`.
- Different Ollama models will follow those instructions with different reliability.
- If the model does not follow the format well, use a stronger instruction-following model.
- The agent is intentionally small and optimized for readability, not robustness.
