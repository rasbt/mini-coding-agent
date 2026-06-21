mod ollama;
mod tools;

use ollama::OllamaClient;
use tools::ToolCall;

use clap::Parser;
use serde::{Deserialize, Serialize};
use std::io::{self, Write};

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
    let client = OllamaClient::new(args.model, args.server);

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

    loop {
        print!("\n> ");
        io::stdout().flush()?;
        let mut user_input = String::new();
        io::stdin().read_line(&mut user_input)?;
        let user_input = user_input.trim();
        if user_input == "exit" {
            break;
        }

        history.push(Message {
            role: "user".to_string(),
            content: user_input.to_string(),
        });

        for _ in 0..5 {
            let response = client.chat(history.clone()).await?;
            history.push(response.clone());

            let content = response.content.trim();

            if content.contains("<tool>") && content.contains("</tool>") {
                let start = content.find("<tool>").unwrap() + 6;
                let end = content.find("</tool>").unwrap();
                let json_str = &content[start..end];

                match serde_json::from_str::<ToolCall>(json_str) {
                    Ok(tool_call) => {
                        let result = tool_call.run();
                        println!("[Tool Result] \n{}", result);
                        history.push(Message {
                            role: "user".to_string(),
                            content: format!("Tool result: {}", result),
                        });
                    }
                    Err(e) => {
                        println!("[ERORR] Could not pars tool: {}", e);
                        break;
                    }
                }
            } else {
                println!("\nAgent: {}", content);
            }
        }
    }
    Ok(())
}
