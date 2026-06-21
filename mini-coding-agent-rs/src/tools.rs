use serde::Deserialize;
use std::fs;
use std::process::Command;

#[derive(Deserialize, Debug)]
#[serde(tag = "name", content = "args", rename_all = "snake_case")]
pub enum ToolCall {
    ListFiles { path: String },
    ReadFile { path: String },
    WriteFile { path: String, content: String },
    RunShell { command: String },
}

impl ToolCall {
    pub fn run(&self) -> String {
        match self {
            ToolCall::ListFiles { path } => match fs::read_dir(path) {
                Ok(entries) => {
                    let names: Vec<_> = entries
                        .filter_map(|e| e.ok())
                        .map(|e| e.file_name().to_string_lossy().to_string())
                        .collect();
                    names.join("\n")
                }
                Err(e) => format!("Error: {}", e),
            },
            // Logic for ReadFile
            ToolCall::ReadFile { path } => match fs::read_to_string(path) {
                Ok(content) => content,
                Err(e) => format!("Error reading file: {}", e),
            },
            ToolCall::WriteFile { path, content } => match fs::write(path, content) {
                Ok(_) => format!("Successfully wrote to {}", path),
                Err(e) => format!("Error writing file: {}", e),
            },
            ToolCall::RunShell { command } => {
                println!("[System] Executing: {}", command);

                let output = if cfg!(target_os = "windows") {
                    Command::new("cmd").args(["/c", command]).output()
                } else {
                    Command::new("sh").args(["-c", command]).output()
                };

                match output {
                    Ok(o) => {
                        let stdout = String::from_utf8_lossy(&o.stdout);
                        let stderr = String::from_utf8_lossy(&o.stderr);
                        format!(
                            "Exit Code: {}\nSTDOUT: {}\nSTDERR: {}",
                            o.status.code().unwrap_or(-1),
                            stdout,
                            stderr
                        )
                    }
                    Err(e) => format!("Failed to execute command: {}", e),
                }
            }
        }
    }
}
