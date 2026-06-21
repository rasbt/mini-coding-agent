use crate::Message;
use reqwest::Client;
use serde::{Deserialize, Serialize};

#[derive(Serialize)]
pub struct ChatRequest {
    model: String,
    messages: Vec<Message>,
    stream: bool,
}

#[derive(Deserialize)]
pub struct ChatResponse {
    message: Message,
}

pub struct OllamaClient {
    model: String,
    host: String,
    http_client: Client,
}

impl OllamaClient {
    pub fn new(model: String, host: String) -> Self {
        Self {
            model,
            host,
            http_client: Client::new(),
        }
    }

    pub async fn chat(
        &self,
        messages: Vec<Message>,
    ) -> Result<Message, Box<dyn std::error::Error>> {
        let url = format!("{}/api/chat", self.host);

        let request = ChatRequest {
            model: self.model.clone(),
            messages,
            stream: false,
        };

        let res = self
            .http_client
            .post(url)
            .json(&request)
            .send()
            .await?
            .json::<ChatResponse>()
            .await?;

        Ok(res.message)
    }
}
