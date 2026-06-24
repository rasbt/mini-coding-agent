mod ollama;
mod session;
mod tools;

use ollama::OllamaClient;
use tools::ToolCall;

use clap::Parser;
use serde::{Deserialize, Serialize};
use std::io::{self, Write};

mod workspace;
use workspace::WorkspaceContext;

#[derive(Parser, Debug)]
#[command[author, version, about, long_about = None]]
struct Args {
    #[arg(short, long, default_value = "minimax-m3:cloud")]
    model: String,

    #[arg(short, long, default_value = "http://127.0.0.1:11434")]
    server: String,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Message {
    role: String,
    content: String,
}

// #[derive(Debug)]
// struct WorkspaceContext {
//     repo_root: String,
//     branch: String,
// }
//
// impl WorkspaceContext {
//     fn new() -> Self {
//         let root = Command::new("git")
//             .args(["rev-parse", "--show-toplevel"])
//             .output()
//             .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
//             .unwrap_or_else(|_| "main".to_string());
//
//         let branch = Command::new("git")
//             .args(["branch", "--show-current"])
//             .output()
//             .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
//             .unwrap_or_else(|_| "main".to_string());
//
//         Self {
//             repo_root: root,
//             branch,
//         }
//     }
// }

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();
    // let client = OllamaClient::new(args.model, args.server);

    let mut history = vec![Message {
        role: "system".to_string(),
        content: "You are a coding assistant.
            Available tools:
            - list_files(path: string)
            - read_file(path: string)
            - write_file(path: string, content: string)
            - run_shell(command: string)

            To use a tool, return ONLY:
            <tool>{\"name\":\"tool_name\", \"args\":{...}}</tool>"
            .to_string(),
    }];

    println!("Welcome to Mini-Coding-Agent!");
    println!("Type 'exit' to quit.");

    let workspace = WorkspaceContext::build(".");
    println!("{}", workspace.text());
    Ok(())
}
