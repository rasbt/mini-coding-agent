use clap::builder::Str;
use serde::Deserialize;
use std::fmt::format;
use std::fs;
use std::process::Command;

#[derive(Deserialize, Debug)]
#[serde(tag = "name", content = "args", rename_all = "snake_case")]
pub enum ToolCall {
    ListFiles {
        path: Option<String>,
    },
    ReadFile {
        path: String,
        start: Option<usize>,
        end: Option<usize>,
    },
    WriteFile {
        path: String,
        content: String,
    },
    PatchFile {
        path: String,
        old_text: String,
        new_text: String,
    },
    Search {
        pattern: String,
        path: Option<String>,
    },
    RunShell {
        command: String,
        timeout: Option<u64>,
    },
}

impl ToolCall {
    pub fn run(&self) -> String {
        match self {
            ToolCall::ListFiles { path } => {
                let target_path = path.as_deref().unwrap_or(".");
                match fs::read_dir(target_path) {
                    Ok(entries) => {
                        let names: Vec<_> = entries
                            .filter_map(|e| e.ok())
                            .map(|e| e.file_name().to_string_lossy().to_string())
                            .collect();
                        names.join("\n")
                    }
                    Err(e) => format!("Error: {}", e),
                }
            }
            // Logic for ReadFile
            ToolCall::ReadFile { path, start, end } => match std::fs::read_to_string(path) {
                Ok(content) => {
                    let lines: Vec<&str> = content.lines().collect();
                    let start_idx = start.unwrap_or(1).saturating_sub(1);
                    let end_idx = end.unwrap_or(200).min(lines.len());
                    if start_idx >= lines.len() || start_idx >= end_idx {
                        return "Error: Invalid line range.".to_string();
                    }

                    let selected_lines = &lines[start_idx..end_idx];
                    let mut result = Vec::new();

                    for (i, line) in selected_lines.iter().enumerate() {
                        result.push(format!("{:>4}: {}", start_idx + i + 1, line));
                    }
                    format!("# {}\n{}", path, result.join("\n"))
                }
                Err(e) => format!("Error reading file: {}", e),
            },

            ToolCall::WriteFile { path, content } => match fs::write(path, content) {
                Ok(_) => format!("Successfully wrote to {}", path),
                Err(e) => format!("Error writing file: {}", e),
            },
            ToolCall::PatchFile {
                path,
                old_text,
                new_text,
            } => match std::fs::read_to_string(path) {
                Ok(content) => {
                    let matches = content.matches(old_text).count();
                    if matches == 1 {
                        let updated = content.replacen(old_text, new_text, 1);
                        match std::fs::write(path, updated) {
                            Ok(_) => format!("Successfully patched {}", path),
                            Err(e) => format!("Error writing patched file: {}", e),
                        }
                    } else {
                        format!(
                            "Error: old_text must occur exactly once, found {} occurrences.",
                            matches
                        )
                    }
                }
                Err(e) => format!("Error reading file: {}", e),
            },
            ToolCall::Search { pattern, path } => {
                let target_path = path.as_deref().unwrap_or(".");
                match std::process::Command::new("rg").args(["-n", "--smart-case", "--max-count", "200", pattern, target_path]).output() {
                    Ok(output) => {
                        let stdout = String::from_utf8_lossy(&output.stdout);
                        let stderr = String::from_utf8_lossy(&output.stderr);
                        if stdout.trim().is_empty() {
                            if stderr.trim().is_empty() {
                                "(no matches)".to_string()
                            } else {
                                stderr.to_string()
                            }
                        } else {
                            stdout.to_string()
                        }
                    }
                    Err(_) => "Error: ripgrep ('rg) is not installed or failed to run. Please install ripgrep.".to_string(),
                }
            }
            ToolCall::RunShell { command, timeout } => {
                let timeout_secs = timeout.unwrap_or(20);

                println!(
                    "[System] Executing: {} (timeout: {}s)",
                    command, timeout_secs
                );

                let mut child = if cfg!(target_os = "windows") {
                    std::process::Command::new("cmd")
                        .args(["/c", &command])
                        .stdout(std::process::Stdio::piped())
                        .stderr(std::process::Stdio::piped())
                        .spawn()
                } else {
                    std::process::Command::new("sh")
                        .args(["-c", &command])
                        .stdout(std::process::Stdio::piped())
                        .stderr(std::process::Stdio::piped())
                        .spawn()
                };
                match child {
                    Ok(mut process) => match process.wait_with_output() {
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
                        Err(e) => format!("Failed to read command output: {}", e),
                    },
                    Err(e) => format!("Failed to execute command: {}", e),
                }
            }
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum ApprovalPolicy {
    Ask,
    Auto,
    Never,
}
