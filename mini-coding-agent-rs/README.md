# Mini Coding Agent (Rust Edition)

A blazingly fast, context-aware local coding assistant written in Rust. It communicates with local models via Ollama and seamlessly reads your workspace, interacts with your files, and executes shell commands safely on your behalf.

## Features

- **Context-Aware**: Automatically pulls your current branch, recent commits, Git status, and project documentation into its context before you even say hello.
- **Token Efficient**: Employs aggressive "context reduction" strategies to truncate verbose command outputs and gracefully prune older chat history to save tokens.
- **Sandboxed Execution**: Features an approval policy (`ask`, `auto`, `never`) for risky operations like editing files or running shell commands.
- **Robust Parsing**: Supports a dual JSON/XML parsing strategy and automatically asks the model to try again if it hallucinates malformed tool payloads.
- **Persistence**: Remembers your previous sessions and summaries via the `.mini-coding-agent/sessions` directory so you can pick up exactly where you left off.

## Requirements

- [Rust & Cargo](https://rustup.rs/) (edition 2021+)
- [Ollama](https://ollama.com/) running locally or accessible via URL.
- [Ripgrep (`rg`)](https://github.com/BurntSushi/ripgrep) installed on your system (optional, used for the `search` tool).

## Installation

To install the agent globally on your system, clone the repository, navigate to the `mini-coding-agent-rs` directory, and run:

```bash
cargo install --path .
```

This will compile the optimized binary and place it in your `~/.cargo/bin` folder, making it accessible from anywhere in your terminal!

## Usage

Navigate to any coding project where you want assistance and run:

```bash
mini-coding-agent-rs
```

### Command Line Arguments

You can customize the agent's behavior at startup using CLI flags:

- `--model <MODEL>`: The Ollama model to use (default: `qwen3.5:4b`)
- `--host <URL>`: The Ollama API endpoint (default: `http://127.0.0.1:11434`)
- `--cwd <PATH>`: The workspace directory (default: `.`)
- `--approval <POLICY>`: Tool approval policy: `ask`, `auto`, or `never` (default: `ask`)
- `--resume <ID>`: Resume a specific session ID, or `latest` to pick up your last conversation.
- `--max-steps <N>`: Maximum tool execution loops per turn (default: 6)
- `--max-new-tokens <N>`: Maximum output tokens per step (default: 512)
- `--temperature <TEMP>`: Model temperature (default: 0.2)
- `--top-p <TOP_P>`: Model top-p sampling (default: 0.9)

**Example:**
```bash
mini-coding-agent-rs --model qwen2.5-coder:7b --approval auto --resume latest
```

### In-App Commands

While running the REPL loop, you can use the following commands:

- `/help`    Show the help message.
- `/memory`  Show the agent's distilled working memory summary.
- `/session` Show the path to the saved session file.
- `/reset`   Clear the current session history and memory.
- `/exit`    Exit the agent (or `/quit`).

## Tools

The agent is equipped with the following internal tools:
- `list_files(path)`
- `read_file(path, start, end)`
- `search(pattern, path)`
- `write_file(path, content)`
- `patch_file(path, old_text, new_text)`
- `run_shell(command)`

## Contributing

Pull requests and feature improvements are welcome! Ensure you run `cargo fmt` and `cargo check` before submitting.
