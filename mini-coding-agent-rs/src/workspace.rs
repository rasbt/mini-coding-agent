use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Debug)]
pub struct WorkspaceContext {
    pub cwd: String,
    pub repo_root: String,
    pub branch: String,
    pub default_branch: String,
    pub status: String,
    pub recent_commits: Vec<String>,
    pub project_docs: HashMap<String, String>,
}

impl WorkspaceContext {
    fn git_command(cwd: &Path, args: &[&str], fallback: &str) -> String {
        match Command::new("git").args(args).current_dir(cwd).output() {
            Ok(output) if output.status.success() => {
                let stdout = String::from_utf8_lossy(&output.stdout);
                let trimmed = stdout.trim();
                if trimmed.is_empty() {
                    fallback.to_string()
                } else {
                    trimmed.to_string()
                }
            }
            _ => fallback.to_string(),
        }
    }

    // Trucate Text
    fn clip(text: &str, limit: usize) -> String {
        if text.len() <= limit {
            text.to_string()
        } else {
            format!(
                "{}\n...[truncated {} chars]",
                &text[..limit],
                text.len() - limit
            )
        }
    }

    pub fn build(cwd_path: &str) -> Self {
        let cwd = PathBuf::from(cwd_path)
            .canonicalize()
            .unwrap_or_else(|_| PathBuf::from("."));

        let repo_root = Self::git_command(
            &cwd,
            &["rev-parse", "--show-toplevel"],
            cwd.to_str().unwrap(),
        );
        let branch = Self::git_command(&cwd, &["branch", "--show-current"], "-");
        let default_branch_raw = Self::git_command(
            &cwd,
            &["symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
            "origin/main",
        );
        let default_branch = default_branch_raw
            .strip_prefix("origin/")
            .unwrap_or(&default_branch_raw)
            .to_string();

        let status_raw = Self::git_command(&cwd, &["log", "--oneline", "-5"], "");
        let status = Self::clip(&status_raw, 1500);

        let commits_raw = Self::git_command(&cwd, &["log", "--oneline", "-5"], "");
        let recent_commits: Vec<String> = commits_raw
            .lines()
            .filter(|l| !l.is_empty())
            .map(|l| l.to_string())
            .collect();

        // Read specific project documentation if it exists
        let mut project_docs = HashMap::new();
        let doc_names = ["AGENTS.md", "README.md", "Cargo.toml", "package.json"];

        let root_path = PathBuf::from(&repo_root);
        for base in &[root_path.clone(), cwd.clone()] {
            for name in doc_names {
                let path = base.join(name);
                if path.exists() {
                    if let Ok(path_diff) = path.strip_prefix(&root_path) {
                        let key = path_diff.to_string_lossy().to_string();
                        if !project_docs.contains_key(&key) {
                            if let Ok(content) = fs::read_to_string(&path) {
                                project_docs.insert(key, Self::clip(&content, 1200));
                            }
                        }
                    }
                }
            }
        }

        Self {
            cwd: cwd.to_string_lossy().to_string(),
            repo_root,
            branch,
            default_branch,
            status,
            recent_commits,
            project_docs,
        }
    }
    pub fn text(&self) -> String {
        let commits = if self.recent_commits.is_empty() {
            "- none".to_string()
        } else {
            self.recent_commits
                .iter()
                .map(|c| format!("- {}", c))
                .collect::<Vec<_>>()
                .join("\n")
        };

        let docs = if self.project_docs.is_empty() {
            "- none".to_string()
        } else {
            self.project_docs
                .iter()
                .map(|(path, snippet)| format!("- {}\n{}", path, snippet))
                .collect::<Vec<_>>()
                .join("\n")
        };

        format!(
        "Workspace:\n- cwd: {}\n- repo_root: {}\n- branch: {}\n- default_branch: {}\n-status:\n{}\n- recent_commits:\n{}\n- project_docs:\n{}",
            self.cwd, self.repo_root, self.branch, self.default_branch, self.status, commits, docs
    )
    }
}
