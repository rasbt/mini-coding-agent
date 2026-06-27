use crate::ollama::OllamaClient;
use crate::session::{Session, SessionStore};
use crate::tools::ApprovalPolicy;
use crate::workspace::WorkspaceContext;

use regex::Regex;
use serde_json::Value;

pub struct MiniAgent {
    pub model_client: OllamaClient,
    pub workspace: WorkspaceContext,
    pub session_store: SessionStore,
    pub session: Session,
    pub approval_policy: ApprovalPolicy,
    pub max_step: usize,
    pub max_new_tokens: usize,
}

impl MiniAgent {
    pub fn new(
        model_client: OllamaClient,
        workspace: WorkspaceContext,
        session_store: SessionStore,
        session: Session,
        approval_policy: ApprovalPolicy,
        max_step: usize,
        max_new_tokens: usize,
    ) -> Self {
        Self {
            model_client,
            workspace,
            session_store,
            session,
            approval_policy,
            max_step,
            max_new_tokens,
        }
    }

    pub fn clip(text: &str, limit: usize) -> String {
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

    pub fn memory_text(&self) -> String {
        let task = if self.session.memory.task.is_empty() {
            "-"
        } else {
            &self.session.memory.task
        };
        let files = if self.session.memory.files.is_empty() {
            "-".to_string()
        } else {
            self.session.memory.files.join(", ")
        };
        let notes = if self.session.memory.notes.is_empty() {
            "- none".to_string()
        } else {
            self.session
                .memory
                .notes
                .iter()
                .map(|n| format!("- {}", n))
                .collect::<Vec<_>>()
                .join("\n")
        };
        format!(
            "Memory:\n- task: {}\n- files: {}\n- notes:\n{}",
            task, files, notes
        )
    }

    pub fn history_text(&self) -> String {
        if self.session.history.is_empty() {
            return "- empty".to_string();
        }

        let mut lines = Vec::new();
        let total_items = self.session.history.len();
        let recent_start = if total_items > 6 { total_items - 6 } else { 0 };

        for (index, item) in self.session.history.iter().enumerate() {
            let recent = index >= recent_start;
            let limit = if recent { 900 } else { 220 };

            if item.role == "tool" {
                let name = item.name.as_deref().unwrap_or("unknown");
                let args_str = item
                    .args
                    .as_ref()
                    .map(|a| a.to_string())
                    .unwrap_or_default();
                lines.push(format!("[tool:{}] {}", name, args_str));
                lines.push(Self::clip(&item.content, limit));
            } else {
                lines.push(format!(
                    "[{}] {}",
                    item.role,
                    Self::clip(&item.content, limit)
                ));
            }
        }
        // limit the total history block to 12,000 characters
        Self::clip(&lines.join("\n"), 12000)
    }

    pub fn build_prefix(&self) -> String {
        let rules = "- Use tools instead of guessing about the workspace. 
- Return exactly one <tool>...</tool> or one <final>...</final>.
- Tool calls must look like:
  <tool>{\"name\":\"tool_name\",\"args\":{...}}</tool>
- For write_file and patch_file with multi-line text, prefer XML style:
  <tool name=\"write_file\" path=\"file.py\"><content>...</content></tool>
- Final answers must look like:
  <final>your answer</final>
- Never invent tool results.";
        let examples = "<tool>{\"name\":\"list_files\",\"args\":{\"path\":\".\"}}</tool>\n<final>Done.</final>";

        format!("You are Mini-Coding-Agent, a small local coding agent running through Ollama.\nRules:\n{}\n\nValid response examples:\n{}\n\n{}", rules, examples, self.workspace.text())
    }

    pub fn prompt(&self, user_message: &str) -> String {
        format!(
            "{}\n\n{}\n\nTranscript:\n{}\n\nCurrent user request:\n{}",
            self.build_prefix(),
            self.memory_text(),
            self.history_text(),
            user_message
        )
    }

    pub fn extract<'a>(text: &'a str, tag: &str) -> Option<&'a str> {
        let start_tag = format!("<{}>", tag);
        let end_tag = format!("</{}>", tag);
        let start = text.find(&start_tag)?;
        let start_idx = start + start_tag.len();
        let end = text[start_idx..].find(&end_tag)?;
        Some(&text[start_idx..start_idx + end].trim())
    }

    pub fn parse(raw: &str) -> (String, String) {
        let raw = raw.trim();
        if let Some(tool_body) = Self::extract(raw, "tool") {
            if serde_json::from_str::<Value>(tool_body).is_ok() {
                return ("tool".to_string(), tool_body.to_string());
            } else {
                return ("retry".to_string(), "Runtime notice: model returned malformed tool JSON. Reply with a valid <tool> call.".to_string());
            }
        }

        let xml_re = Regex::new(r#"<tool\s+name=["']([^"']+)["'][^>]*>(.*?)<\/tool>"#).unwrap();
        if let Some(caps) = xml_re.captures(raw) {
            let name = caps.get(1).unwrap().as_str();
            let body = caps.get(2).unwrap().as_str();
            if name == "write_file" || name == "patch_file" {
                if let Some(content) = Self::extract(body, "content") {
                    let json = serde_json::json!({
                        "name": name,
                        "args": {
                        "path": Self::extract(body, "path").unwrap_or(""),
                        "content": content

                    }
                    });
                    return ("tool".to_string(), json.to_string());
                }
            }
        }

        if let Some(final_text) = Self::extract(raw, "final") {
            if !final_text.is_empty() {
                return ("final".to_string(), final_text.to_string());
            }
        }

        if !raw.is_empty() && !raw.contains("<tool") {
            return ("final".to_string(), raw.to_string());
        }

        ("retry".to_string(), "Runtime notice: model returned an empty response or malformed tags. Use <tool> or <final>.".to_string())
    }

    pub async fn ask(&mut self, user_message: &str) -> String {
        use crate::session::SessionItem;

        if self.session.memory.task.is_empty() {
            self.session.memory.task = Self::clip(user_message, 300);
        }

        self.session.history.push(SessionItem {
            role: "user".to_string(),
            content: user_message.to_string(),
            name: None,
            args: None,
            created_at: Some(chrono::Utc::now().to_rfc3339()),
        });

        let mut tool_steps = 0;
        let mut attempts = 0;
        let max_attempts = (self.max_step * 3).max(self.max_step + 4);

        while tool_steps < self.max_step && attempts < max_attempts {
            attempts += 1;
            let prompt_text = self.prompt(user_message);

            match self
                .model_client
                .complete(&prompt_text, self.max_new_tokens)
                .await
            {
                Ok(raw_response) => {
                    let (kind, payload) = Self::parse(&raw_response);
                    if kind == "tool" {
                        tool_steps += 1;
                        match serde_json::from_str::<crate::tools::ToolCall>(&payload) {
                            Ok(tool_call) => {
                                let result = tool_call.run();

                                self.session.history.push(SessionItem {
                                    role: "tool".to_string(),
                                    name: Some("executed".to_string()),
                                    args: Some(serde_json::from_str(&payload).unwrap()),
                                    content: result.clone(),
                                    created_at: Some(chrono::Utc::now().to_rfc3339()),
                                });

                                let _ = self.session_store.save(&self.session);
                                continue;
                            }
                            Err(e) => {
                                self.session.history.push(SessionItem {
                                    role: "assistant".to_string(),
                                    content: format!(
                                        "Runtime notice: Failed to parse tool call internally: {}",
                                        e
                                    ),
                                    name: None,
                                    args: None,
                                    created_at: None,
                                });
                                continue;
                            }
                        }
                    }

                    if kind == "retry" {
                        self.session.history.push(SessionItem {
                            role: "assistant".to_string(),
                            content: payload,
                            name: None,
                            args: None,
                            created_at: None,
                        });
                        continue;
                    }

                    // It's final answer!
                    self.session.history.push(SessionItem {
                        role: "assistant".to_string(),
                        content: payload.clone(),
                        name: None,
                        args: None,
                        created_at: Some(chrono::Utc::now().to_rfc3339()),
                    });

                    let _ = self.session_store.save(&self.session);
                    return payload;
                }
                Err(e) => return format!("Error reaching Ollama: {}", e),
            }
        }
        "Stopped afer reaching step limits whithout a final answer.".to_string()
    }
}
