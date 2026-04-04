# Reverse Engineering: Mini-Coding-Agent

A deep technical analysis of how the Mini-Coding-Agent system works, from architecture to implementation detail.

---

[TOC]

## Part I: High-Level Overview

### The System as a Whole

Mini-Coding-Agent is a single-file (~1000 lines), zero-dependency Python coding agent that runs locally against an Ollama LLM backend. It implements a complete agentic loop: the user submits a request, the agent repeatedly prompts the model, parses its output for tool calls or final answers, executes tools against the local workspace, records everything into a persistent session, and returns a result.

The system is organized around **six components** annotated directly in the source code, mapping to the framework described in Sebastian Raschka's article on coding agent design:

**from: Components of A Coding Agent**
> "I think this is one of the underrated, boring parts of good coding-agent design. A lot of apparent 'model quality' is really context quality."

[`mini_coding_agent.py#L41-L48`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L41-L48)
```python
##############################
#### Six Agent Components ####
##############################
# 1) Live Repo Context -> WorkspaceContext
# 2) Prompt Shape And Cache Reuse -> build_prefix, memory_text, prompt
# 3) Structured Tools, Validation, And Permissions -> build_tools, run_tool, validate_tool, approve, parse, path, tool_*
# 4) Context Reduction And Output Management -> clip, history_text
# 5) Transcripts, Memory, And Resumption -> SessionStore, record, note_tool, ask, reset
# 6) Delegation And Bounded Subagents -> tool_delegate
```

The central class [`MiniAgent`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L229) orchestrates all six components. When a user message arrives, the [`ask()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L460) method assembles a prompt (components 1+2), enters a loop that calls the model and parses its response (component 3), clips and compresses context each turn (component 4), records every event to the session transcript and working memory (component 5), and optionally delegates to a bounded child agent (component 6).

Two model clients are provided: [`OllamaModelClient`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L183) for real inference against Ollama's `/api/generate` endpoint, and [`FakeModelClient`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L171) for deterministic testing.

### Component 1: Live Repo Context ([`WorkspaceContext`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L77))

Before any work begins, the agent snapshots the repository environment: current working directory, git root, branch, default branch, `git status`, recent commits, and key project documents (`AGENTS.md`, `README.md`, `pyproject.toml`, `package.json`).

**from: Components of A Coding Agent**
> "the coding agent collects info ("stable facts" as a workspace summary) upfront before doing any work, so that it's is not starting from zero, without context, on every prompt."

This context is computed once at agent construction and embedded into every prompt, giving the model grounding in the project's current state without needing to discover it through tool calls.

### Component 2: Prompt Shape and Cache Reuse ([`build_prefix`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L337), [`memory_text`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L386), [`prompt`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L430))

The prompt is assembled from three layers: a **stable prefix** (system instructions, tool descriptions, workspace context), a **working memory section** (task, tracked files, notes), and the **transcript** of the current session plus the user's latest message.

**from: Components of A Coding Agent**
> "The "Stable prompt prefix" means that the information contained there doesn't change too much. It usually contains the general instructions, tool descriptions, and the workspace summary."

The prefix is computed once ([`build_prefix()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L337)) and reused across all model calls within a session. Only the memory and transcript portions change between turns.

### Component 3: Structured Tools, Validation, and Permissions ([`build_tools`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L286), [`run_tool`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L511), [`validate_tool`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L551), [`approve`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L617))

The agent exposes a fixed set of named tools (`list_files`, `read_file`, `search`, `run_shell`, `write_file`, `patch_file`, and optionally `delegate`). Each tool has a declared schema, a risk flag, and a runner function. Before execution, every call passes through validation (argument types, path safety, workspace containment) and, for risky tools, an approval gate.

**from: Components of A Coding Agent**
> "the harness usually provides a pre-defined list of allowed and named tools with clear inputs and clear boundaries."

The model's raw text output is parsed for `<tool>...</tool>` or `<final>...</final>` XML tags. Malformed output triggers a retry with an error notice rather than a crash.

### Component 4: Context Reduction and Output Management ([`clip`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L56), [`history_text`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L401))

Every piece of text flowing into the prompt is bounded. Tool outputs are clipped to [`MAX_TOOL_OUTPUT`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L36) (4000 chars). The transcript is compressed by deduplicating older `read_file` results, shortening older entries more aggressively than recent ones, and truncating the entire history to [`MAX_HISTORY`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L37) (12000 chars).

**from: Components of A Coding Agent**
> "A minimal harness uses at least two compaction strategies to manage that problem. The first is clipping, which shortens long document snippets, large tool outputs, memory notes, and transcript entries."

### Component 5: Transcripts, Memory, and Resumption ([`SessionStore`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L150), [`record`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L448), [`note_tool`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L452), [`ask`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L460))

The system maintains two layers of memory. The **full transcript** is an append-only list of every user message, tool call, and assistant response. The **working memory** is a small distilled structure (`task`, `files`, `notes`) that is actively maintained as tools execute, acting as a compact summary of what matters right now.

**from: Components of A Coding Agent**
> "a coding agent separates state into (at least) two layers: working memory: the small, distilled state the agent keeps explicitly [and] a full transcript: this covers all the user requests, tool outputs, and LLM responses"

Sessions are persisted to disk as JSON files via [`SessionStore`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L150), enabling resumption across process restarts.

### Component 6: Delegation and Bounded Subagents ([`tool_delegate`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L850))

The `delegate` tool spawns a child [`MiniAgent`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L229) that inherits the model client and workspace but operates under strict constraints: read-only access, no approval for risky tools (`approval_policy="never"`), limited step budget, and incremented depth. The child receives a summarized snapshot of the parent's history as initial notes.

**from: Components of A Coding Agent**
> "the subagent inherits enough context to be useful, but also has it constrained (for example, read-only and restricted in recursion depth)"

Delegation is only available when `depth < max_depth`, preventing unbounded recursion.

---

## Part II: Low-Level Detail

### Component 1: Live Repo Context — [`WorkspaceContext`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L77) in Detail

The [`WorkspaceContext`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L77) class is responsible for gathering all environmental facts. It is a plain data class built via the [`build()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L88) classmethod:

[`mini_coding_agent.py#L77-L85`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L77-L85)
```python
class WorkspaceContext:
    def __init__(self, cwd, repo_root, branch, default_branch, status, recent_commits, project_docs):
        self.cwd = cwd
        self.repo_root = repo_root
        self.branch = branch
        self.default_branch = default_branch
        self.status = status
        self.recent_commits = recent_commits
        self.project_docs = project_docs
```

The [`build()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L88) method wraps all git commands in a safe helper that returns a fallback string on any failure:

[`mini_coding_agent.py#L91-L103`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L91-L103)
```python
def git(args, fallback=""):
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip() or fallback
    except Exception:
        return fallback
```

This makes the context-gathering robust — if the workspace is not a git repo, everything gracefully degrades to fallback values rather than crashing.

Project documents are discovered by scanning both the repo root and the current working directory for well-known filenames:

[`mini_coding_agent.py#L16`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L16)
```python
DOC_NAMES = ("AGENTS.md", "README.md", "pyproject.toml", "package.json")
```

[`mini_coding_agent.py#L106-L115`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L106-L115)
```python
docs = {}
for base in (repo_root, cwd):
    for name in DOC_NAMES:
        path = base / name
        if not path.exists():
            continue
        key = str(path.relative_to(repo_root))
        if key in docs:
            continue
        docs[key] = clip(path.read_text(encoding="utf-8", errors="replace"), 1200)
```

Documents are clipped to 1200 characters to prevent large files from bloating the context. The deduplication via `key in docs` ensures a file is only included once even if `repo_root == cwd`.

The [`text()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L127) method serializes the context into a plain-text block embedded directly in the prompt:

[`mini_coding_agent.py#L127-L144`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L127-L144)
```python
def text(self):
    commits = "\n".join(f"- {line}" for line in self.recent_commits) or "- none"
    docs = "\n".join(f"- {path}\n{snippet}" for path, snippet in self.project_docs.items()) or "- none"
    return textwrap.dedent(
        f"""\
        Workspace:
        - cwd: {self.cwd}
        - repo_root: {self.repo_root}
        - branch: {self.branch}
        - default_branch: {self.default_branch}
        - status:
        {self.status}
        - recent_commits:
        {commits}
        - project_docs:
        {docs}
        """
    ).strip()
```

### Component 2: Prompt Shape and Cache Reuse — Prompt Assembly in Detail

The prompt is assembled in three methods that layer on top of each other.

[**`build_prefix()`**](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L337) constructs the stable portion at agent init time. It includes the system persona, behavioral rules, tool catalog with schemas and risk labels, example tool-call formats, and the workspace context:

[`mini_coding_agent.py#L337-L384`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L337-L384)
```python
def build_prefix(self):
    tool_lines = []
    for name, tool in self.tools.items():
        fields = ", ".join(f"{key}: {value}" for key, value in tool["schema"].items())
        risk = "approval required" if tool["risky"] else "safe"
        tool_lines.append(f"- {name}({fields}) [{risk}] {tool['description']}")
    tool_text = "\n".join(tool_lines)
    examples = "\n".join(
        [
            '<tool>{"name":"list_files","args":{"path":"."}}</tool>',
            '<tool>{"name":"read_file","args":{"path":"README.md","start":1,"end":80}}</tool>',
            '<tool name="write_file" path="binary_search.py"><content>def binary_search(nums, target):\n    return -1\n</content></tool>',
            # ... more examples
            "<final>Done.</final>",
        ]
    )
    return textwrap.dedent(
        f"""\
        You are Mini-Coding-Agent, a small local coding agent running through Ollama.

        Rules:
        - Use tools instead of guessing about the workspace.
        - Return exactly one <tool>...</tool> or one <final>...</final>.
        ...
        Tools:
        {tool_text}

        Valid response examples:
        {examples}

        {self.workspace.text()}
        """
    ).strip()
```

The prefix never changes during a session, making it a candidate for KV-cache reuse on backends that support prompt prefix caching.

[**`memory_text()`**](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L386) serializes the working memory:

[`mini_coding_agent.py#L386-L396`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L386-L396)
```python
def memory_text(self):
    memory = self.session["memory"]
    return textwrap.dedent(
        f"""\
        Memory:
        - task: {memory['task'] or "-"}
        - files: {", ".join(memory["files"]) or "-"}
        - notes:
          {chr(10).join(f"- {note}" for note in memory["notes"]) or "- none"}
        """
    ).strip()
```

[**`prompt()`**](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L430) combines all three layers — prefix, memory, compressed transcript, and the current user message:

[`mini_coding_agent.py#L430-L443`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L430-L443)
```python
def prompt(self, user_message):
    return textwrap.dedent(
        f"""\
        {self.prefix}

        {self.memory_text()}

        Transcript:
        {self.history_text()}

        Current user request:
        {user_message}
        """
    ).strip()
```

This layered structure means the model sees stable instructions first, then a compact summary of what it should remember, then the recent conversation, and finally the user's request.

### Component 3: Structured Tools, Validation, and Permissions — The Full Pipeline

#### Tool Registration

Tools are registered in [`build_tools()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L286) as a dictionary mapping tool names to their schema, risk level, description, and runner:

[`mini_coding_agent.py#L286-L332`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L286-L332)
```python
def build_tools(self):
    tools = {
        "list_files": {
            "schema": {"path": "str='.'"},
            "risky": False,
            "description": "List files in the workspace.",
            "run": self.tool_list_files,
        },
        # ...
        "run_shell": {
            "schema": {"command": "str", "timeout": "int=20"},
            "risky": True,
            "description": "Run a shell command in the repo root.",
            "run": self.tool_run_shell,
        },
        # ...
    }
    if self.depth < self.max_depth:
        tools["delegate"] = {
            "schema": {"task": "str", "max_steps": "int=3"},
            "risky": False,
            "description": "Ask a bounded read-only child agent to investigate.",
            "run": self.tool_delegate,
        }
    return tools
```

The `delegate` tool is conditionally registered only when recursion depth allows. This makes it impossible for the model to even attempt delegation beyond the configured depth.

#### Parsing Model Output

The [`parse()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L631) static method handles two output formats — JSON-style `<tool>{"name":...}</tool>` and XML-style `<tool name="write_file" path="..."><content>...</content></tool>`. It returns a `(kind, payload)` tuple where `kind` is one of `"tool"`, `"final"`, or `"retry"`:

[`mini_coding_agent.py#L631-L662`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L631-L662)
```python
@staticmethod
def parse(raw):
    raw = str(raw)
    if "<tool>" in raw and ("<final>" not in raw or raw.find("<tool>") < raw.find("<final>")):
        body = MiniAgent.extract(raw, "tool")
        try:
            payload = json.loads(body)
        except Exception:
            return "retry", MiniAgent.retry_notice("model returned malformed tool JSON")
        # ... validate payload structure
        return "tool", payload
    if "<tool" in raw and ("<final>" not in raw or raw.find("<tool") < raw.find("<final>")):
        payload = MiniAgent.parse_xml_tool(raw)
        if payload is not None:
            return "tool", payload
        return "retry", MiniAgent.retry_notice()
    if "<final>" in raw:
        final = MiniAgent.extract(raw, "final").strip()
        if final:
            return "final", final
        return "retry", MiniAgent.retry_notice("model returned an empty <final> answer")
    raw = raw.strip()
    if raw:
        return "final", raw
    return "retry", MiniAgent.retry_notice("model returned an empty response")
```

The priority order is: `<tool>` JSON > `<tool` XML > `<final>` > raw text as implicit final > retry. If the model produces anything unparseable, it gets a retry notice rather than an error — the agent will re-prompt with the notice in the transcript.

The XML parser handles multi-line file content that would be awkward to encode in JSON:

[`mini_coding_agent.py#L676-L697`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L676-L697)
```python
@staticmethod
def parse_xml_tool(raw):
    match = re.search(r"<tool(?P<attrs>[^>]*)>(?P<body>.*?)</tool>", raw, re.S)
    if not match:
        return None
    attrs = MiniAgent.parse_attrs(match.group("attrs"))
    name = str(attrs.pop("name", "")).strip()
    if not name:
        return None

    body = match.group("body")
    args = dict(attrs)
    for key in ("content", "old_text", "new_text", "command", "task", "pattern", "path"):
        if f"<{key}>" in body:
            args[key] = MiniAgent.extract_raw(body, key)

    body_text = body.strip("\n")
    if name == "write_file" and "content" not in args and body_text:
        args["content"] = body_text
    # ...
    return {"name": name, "args": args}
```

#### Validation

Every tool call passes through [`validate_tool()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L551) before execution. Each tool has custom validation logic:

[`mini_coding_agent.py#L551-L616`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L551-L616)
```python
def validate_tool(self, name, args):
    # ...
    if name == "patch_file":
        path = self.path(args["path"])
        if not path.is_file():
            raise ValueError("path is not a file")
        old_text = str(args.get("old_text", ""))
        if not old_text:
            raise ValueError("old_text must not be empty")
        if "new_text" not in args:
            raise ValueError("missing new_text")
        text = path.read_text(encoding="utf-8")
        count = text.count(old_text)
        if count != 1:
            raise ValueError(f"old_text must occur exactly once, found {count}")
        return
    # ...
```

Validation failures produce error messages with examples to guide the model toward correct usage:

[`mini_coding_agent.py#L515-L522`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L515-L522)
```python
try:
    self.validate_tool(name, args)
except Exception as exc:
    example = self.tool_example(name)
    message = f"error: invalid arguments for {name}: {exc}"
    if example:
        message += f"\nexample: {example}"
    return message
```

#### Path Sandboxing

All file paths are resolved through the [`path()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L737) method, which enforces workspace containment:

[`mini_coding_agent.py#L737-L743`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L737-L743)
```python
def path(self, raw_path):
    path = Path(raw_path)
    path = path if path.is_absolute() else self.root / path
    resolved = path.resolve()
    if os.path.commonpath([str(self.root), str(resolved)]) != str(self.root):
        raise ValueError(f"path escapes workspace: {raw_path}")
    return resolved
```

This prevents the model from reading or writing files outside the repository root, even through symlinks or `..` traversal.

#### Approval Gate

Risky tools (`run_shell`, `write_file`, `patch_file`) must pass the approval gate before execution:

[`mini_coding_agent.py#L617-L628`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L617-L628)
```python
def approve(self, name, args):
    if self.read_only:
        return False
    if self.approval_policy == "auto":
        return True
    if self.approval_policy == "never":
        return False
    try:
        answer = input(f"approve {name} {json.dumps(args, ensure_ascii=True)}? [y/N] ")
    except EOFError:
        return False
    return answer.strip().lower() in {"y", "yes"}
```

Three policies are supported: `"ask"` (interactive human confirmation), `"auto"` (always approve), and `"never"` (always deny). Child agents created by delegation always use `"never"`, ensuring subagents cannot mutate the workspace.

#### Repeated Call Detection

The agent prevents infinite loops by detecting when the same tool is called with the same arguments twice consecutively:

[`mini_coding_agent.py#L532-L537`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L532-L537)
```python
def repeated_tool_call(self, name, args):
    tool_events = [item for item in self.session["history"] if item["role"] == "tool"]
    if len(tool_events) < 2:
        return False
    recent = tool_events[-2:]
    return all(item["name"] == name and item["args"] == args for item in recent)
```

#### The [`run_tool`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L511) Orchestration

All these checks are orchestrated in [`run_tool()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L511):

[`mini_coding_agent.py#L511-L530`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L511-L530)
```python
def run_tool(self, name, args):
    tool = self.tools.get(name)
    if tool is None:
        return f"error: unknown tool '{name}'"
    try:
        self.validate_tool(name, args)
    except Exception as exc:
        example = self.tool_example(name)
        message = f"error: invalid arguments for {name}: {exc}"
        if example:
            message += f"\nexample: {example}"
        return message
    if self.repeated_tool_call(name, args):
        return f"error: repeated identical tool call for {name}; choose a different tool or return a final answer"
    if tool["risky"] and not self.approve(name, args):
        return f"error: approval denied for {name}"
    try:
        return clip(tool["run"](args))
    except Exception as exc:
        return f"error: tool {name} failed: {exc}"
```

The pipeline is: lookup -> validate -> dedup check -> approval -> execute -> clip output. Errors at any stage are returned as strings (not exceptions), so the model sees them and can adjust.

### Component 4: Context Reduction and Output Management — Clipping and History Compression

#### Output Clipping

The [`clip()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L56) function truncates any string that exceeds a limit, appending a notice of how much was removed:

[`mini_coding_agent.py#L36`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L36) · [`mini_coding_agent.py#L56-L60`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L56-L60)
```python
MAX_TOOL_OUTPUT = 4000

def clip(text, limit=MAX_TOOL_OUTPUT):
    text = str(text)
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated {len(text) - limit} chars]"
```

This is applied everywhere: tool outputs, project documents (at 1200 chars), memory notes (at 220 chars), and the history itself.

#### History Compression

The [`history_text()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L401) method implements a recency-weighted compression strategy:

[`mini_coding_agent.py#L37`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L37) · [`mini_coding_agent.py#L401-L425`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L401-L425)
```python
MAX_HISTORY = 12000

def history_text(self):
    history = self.session["history"]
    if not history:
        return "- empty"

    lines = []
    seen_reads = set()
    recent_start = max(0, len(history) - 6)
    for index, item in enumerate(history):
        recent = index >= recent_start
        if item["role"] == "tool" and item["name"] == "read_file" and not recent:
            path = str(item["args"].get("path", ""))
            if path in seen_reads:
                continue
            seen_reads.add(path)

        if item["role"] == "tool":
            limit = 900 if recent else 180
            lines.append(f"[tool:{item['name']}] {json.dumps(item['args'], sort_keys=True)}")
            lines.append(clip(item["content"], limit))
        else:
            limit = 900 if recent else 220
            lines.append(f"[{item['role']}] {clip(item['content'], limit)}")

    return clip("\n".join(lines), MAX_HISTORY)
```

Three strategies are at work:

1. **Recency bias**: The last 6 entries get 900-char limits; older entries get 180-220 chars. This preserves high fidelity for the immediate working context while aggressively compressing ancient history.
2. **Deduplication**: Older `read_file` calls for the same path are dropped entirely — only the first read survives in the compressed transcript.
3. **Global cap**: The entire assembled history is clipped to 12000 chars as a final safety net.

### Component 5: Transcripts, Memory, and Resumption — Dual-Layer State

#### Session Structure

Each session is a JSON document with four fields:

[`mini_coding_agent.py#L253-L259`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L253-L259)
```python
self.session = session or {
    "id": datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6],
    "created_at": now(),
    "workspace_root": workspace.repo_root,
    "history": [],
    "memory": {"task": "", "files": [], "notes": []},
}
```

- `history` is the full transcript — every user message, tool result, and assistant response.
- `memory` is the working memory — a compact, actively curated summary.

#### Recording Events

Every event (user message, tool result, assistant response) is appended to the transcript and immediately persisted:

[`mini_coding_agent.py#L448-L450`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L448-L450)
```python
def record(self, item):
    self.session["history"].append(item)
    self.session_path = self.session_store.save(self.session)
```

The [`save()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L158) call writes the entire session to a JSON file on every event, ensuring no work is lost even on a crash.

#### Working Memory Updates

After each tool execution, [`note_tool()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L452) updates the working memory:

[`mini_coding_agent.py#L452-L458`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L452-L458)
```python
def note_tool(self, name, args, result):
    memory = self.session["memory"]
    path = args.get("path")
    if name in {"read_file", "write_file", "patch_file"} and path:
        self.remember(memory["files"], str(path), 8)
    note = f"{name}: {clip(str(result).replace(chr(10), ' '), 220)}"
    self.remember(memory["notes"], note, 5)
```

The [`remember()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L275) helper implements a bounded, most-recently-used list:

[`mini_coding_agent.py#L275-L281`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L275-L281)
```python
@staticmethod
def remember(bucket, item, limit):
    if not item:
        return
    if item in bucket:
        bucket.remove(item)
    bucket.append(item)
    del bucket[:-limit]
```

Files touched by file operations are tracked (up to 8), and a condensed note for each tool call is kept (up to 5). This ensures the memory stays small and relevant.

#### The [`ask()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L460) Loop — The Heart of the Agent

The [`ask()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L460) method is the agentic loop. It records the user message, sets the task in working memory if empty, then enters a loop:

[`mini_coding_agent.py#L460-L506`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L460-L506)
```python
def ask(self, user_message):
    memory = self.session["memory"]
    if not memory["task"]:
        memory["task"] = clip(user_message.strip(), 300)
    self.record({"role": "user", "content": user_message, "created_at": now()})

    tool_steps = 0
    attempts = 0
    max_attempts = max(self.max_steps * 3, self.max_steps + 4)

    while tool_steps < self.max_steps and attempts < max_attempts:
        attempts += 1
        raw = self.model_client.complete(self.prompt(user_message), self.max_new_tokens)
        kind, payload = self.parse(raw)

        if kind == "tool":
            tool_steps += 1
            name = payload.get("name", "")
            args = payload.get("args", {})
            result = self.run_tool(name, args)
            self.record(
                {"role": "tool", "name": name, "args": args, "content": result, "created_at": now()}
            )
            self.note_tool(name, args, result)
            continue

        if kind == "retry":
            self.record({"role": "assistant", "content": payload, "created_at": now()})
            continue

        final = (payload or raw).strip()
        self.record({"role": "assistant", "content": final, "created_at": now()})
        self.remember(memory["notes"], clip(final, 220), 5)
        return final

    # ...budget exhausted...
```

Two counters govern termination:
- `tool_steps` counts successful tool executions (bounded by `max_steps`, default 6).
- `attempts` counts all loop iterations including retries (bounded by `max_attempts = max(max_steps * 3, max_steps + 4)`).

This dual-counter design ensures that retries (from malformed model output) don't consume the tool budget, while still preventing infinite retry loops.

#### Session Persistence and Resumption

[`SessionStore`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L150) manages file-based persistence:

[`mini_coding_agent.py#L150-L168`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L150-L168)
```python
class SessionStore:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, session_id):
        return self.root / f"{session_id}.json"

    def save(self, session):
        path = self.path(session["id"])
        path.write_text(json.dumps(session, indent=2), encoding="utf-8")
        return path

    def load(self, session_id):
        return json.loads(self.path(session_id).read_text(encoding="utf-8"))

    def latest(self):
        files = sorted(self.root.glob("*.json"), key=lambda path: path.stat().st_mtime)
        return files[-1].stem if files else None
```

Sessions are stored under `.mini-coding-agent/sessions/` in the workspace root. The [`latest()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L166) method supports the `--resume latest` CLI flag by returning the most recently modified session.

Resumption reconstructs the agent with the saved session intact:

[`mini_coding_agent.py#L264-L272`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L264-L272)
```python
@classmethod
def from_session(cls, model_client, workspace, session_store, session_id, **kwargs):
    return cls(
        model_client=model_client,
        workspace=workspace,
        session_store=session_store,
        session=session_store.load(session_id),
        **kwargs,
    )
```

### Component 6: Delegation and Bounded Subagents — Child Agent Spawning

The [`tool_delegate()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L850) method creates a fully isolated child agent:

[`mini_coding_agent.py#L850-L869`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L850-L869)
```python
def tool_delegate(self, args):
    if self.depth >= self.max_depth:
        raise ValueError("delegate depth exceeded")
    task = str(args.get("task", "")).strip()
    if not task:
        raise ValueError("task must not be empty")
    child = MiniAgent(
        model_client=self.model_client,
        workspace=self.workspace,
        session_store=self.session_store,
        approval_policy="never",
        max_steps=int(args.get("max_steps", 3)),
        max_new_tokens=self.max_new_tokens,
        depth=self.depth + 1,
        max_depth=self.max_depth,
        read_only=True,
    )
    child.session["memory"]["task"] = task
    child.session["memory"]["notes"] = [clip(self.history_text(), 300)]
    return "delegate_result:\n" + child.ask(task)
```

Key constraints on the child agent:
- **`approval_policy="never"`**: The child cannot execute risky tools.
- **`read_only=True`**: An additional safety check — [`approve()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L617) returns `False` when `read_only` is set.
- **`depth=self.depth + 1`**: Incremented depth prevents recursive delegation beyond `max_depth` (default 1).
- **`max_steps` is configurable but defaults to 3**: Smaller budget than the parent's default of 6.
- **Context seeding**: The child receives the parent's compressed history (clipped to 300 chars) as an initial memory note, plus the delegated task as its task field.

The child runs its own independent [`ask()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L460) loop with its own session, transcript, and memory. Its final answer is returned to the parent as a tool result string prefixed with `"delegate_result:\n"`.

### How Components Work Together — The Full Request Lifecycle

When a user types a message:

1. **Context (Component 1)** was already captured at startup and baked into the prefix.
2. **Prompt assembly (Component 2)** combines the stable prefix + working memory + compressed transcript + user message into a single string.
3. **Model call**: The prompt is sent to Ollama via [`model_client.complete()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L191).
4. **Parsing (Component 3)**: The raw response is parsed for `<tool>` or `<final>` tags.
5. **Tool execution (Component 3)**: If a tool call is found, it passes through validation -> dedup -> approval -> execution. The output is clipped (Component 4).
6. **Recording (Component 5)**: The tool result is appended to the transcript and working memory is updated.
7. **History compression (Component 4)**: On the next iteration, [`history_text()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L401) compresses older entries to fit the budget.
8. **Loop**: Steps 2-7 repeat until the model emits a `<final>` answer or the step budget is exhausted.
9. **Delegation (Component 6)**: If the model calls `delegate`, a constrained child agent runs steps 1-8 independently, and its result feeds back into step 6 of the parent.

### The Model Backend

The [`OllamaModelClient`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L183) wraps Ollama's HTTP API:

[`mini_coding_agent.py#L191-L226`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L191-L226)
```python
class OllamaModelClient:
    def complete(self, prompt, max_new_tokens):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "raw": False,
            "think": False,
            "options": {
                "num_predict": max_new_tokens,
                "temperature": self.temperature,
                "top_p": self.top_p,
            },
        }
        request = urllib.request.Request(
            self.host + "/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # ...
```

It uses only the standard library (`urllib.request`), maintaining the zero-dependency design. `stream: False` means the entire response is buffered before returning, and `think: False` disables chain-of-thought from models that support it.

The [`FakeModelClient`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L171) enables deterministic testing by returning pre-scripted outputs:

[`mini_coding_agent.py#L171-L180`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L171-L180)
```python
class FakeModelClient:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.prompts = []

    def complete(self, prompt, max_new_tokens):
        self.prompts.append(prompt)
        if not self.outputs:
            raise RuntimeError("fake model ran out of outputs")
        return self.outputs.pop(0)
```

This is used extensively in the test suite, where each test pre-loads a sequence of model responses and verifies the agent's behavior end-to-end.

### The CLI and REPL

The [`main()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L967) function ties everything together via [`build_arg_parser()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L948) and [`build_agent()`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L915):

[`mini_coding_agent.py#L967-L1017`](https://github.com/mguinada/mini-coding-agent/blob/main/mini_coding_agent.py#L967-L1017)
```python
def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    agent = build_agent(args)

    print(build_welcome(agent, model=args.model, host=args.host))

    if args.prompt:
        prompt = " ".join(args.prompt).strip()
        if prompt:
            print()
            try:
                print(agent.ask(prompt))
            except RuntimeError as exc:
                print(str(exc), file=sys.stderr)
                return 1
        return 0

    while True:
        try:
            user_input = input("\nmini-coding-agent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("")
            return 0
        # ... slash commands ...
        print()
        try:
            print(agent.ask(user_input))
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
```

It supports two modes: **one-shot** (pass a prompt as positional arguments) and **interactive REPL** (no prompt arguments). The REPL handles slash commands (`/help`, `/memory`, `/session`, `/reset`, `/exit`) locally without sending them to the model.
