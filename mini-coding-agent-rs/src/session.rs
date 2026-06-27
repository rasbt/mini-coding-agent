use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use uuid::Uuid;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct SessionMemory {
    pub task: String,
    pub files: Vec<String>,
    pub notes: Vec<String>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct SessionItem {
    pub role: String,
    pub content: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub args: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub created_at: Option<String>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Session {
    pub id: String,
    pub created_at: String,
    pub workspace_root: String,
    pub history: Vec<SessionItem>,
    pub memory: SessionMemory,
}

impl Session {
    pub fn new(workspace_root: String) -> Self {
        let id = format!(
            "{}-{}",
            Utc::now().format("%Y%m%d-%H%M%S"),
            &Uuid::new_v4().to_string()[..6]
        );
        Self {
            id,
            created_at: Utc::now().to_rfc3339(),
            workspace_root,
            history: Vec::new(),
            memory: SessionMemory {
                task: String::new(),
                files: Vec::new(),
                notes: Vec::new(),
            },
        }
    }
}

pub struct SessionStore {
    root: PathBuf,
}

impl SessionStore {
    pub fn new<P: AsRef<Path>>(workspace_root: P) -> Self {
        let root = workspace_root
            .as_ref()
            .join(".mini-coding-agent")
            .join("sessions");
        fs::create_dir_all(&root).unwrap_or_default();
        Self { root }
    }

    fn path(&self, session_id: &str) -> PathBuf {
        self.root.join(format!("{}.json", session_id))
    }

    pub fn save(&self, session: &Session) -> Result<PathBuf, std::io::Error> {
        let path = self.path(&session.id);
        let json = serde_json::to_string_pretty(session)?;
        fs::write(&path, json)?;
        Ok(path)
    }

    pub fn load(&self, session_id: &str) -> Result<Session, std::io::Error> {
        let json = fs::read_to_string(self.path(session_id))?;
        let session = serde_json::from_str(&json)?;
        Ok(session)
    }

    pub fn latest(&self) -> Option<String> {
        let mut entries: Vec<_> = fs::read_dir(&self.root)
            .ok()?
            .filter_map(Result::ok)
            .filter(|e| e.path().extension().and_then(|s| s.to_str()) == Some("json"))
            .collect();
        entries.sort_by_key(|e| e.metadata().and_then(|m| m.modified()).ok());

        entries
            .last()
            .map(|e| e.path().file_stem().unwrap().to_string_lossy().into_owned())
    }
}
