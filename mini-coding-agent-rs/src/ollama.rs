use crate::Message;
use reqwest::Client;
use serde::{Deserialize, Serialize};

#[derive(Serialize)]
pub struct GenerateOptions {
    pub num_predict: usize,
    pub temperature: f32,
    pub top_p: f32,
}

#[derive(Serialize)]
pub struct GenerateRequest {
    pub model: String,
    pub prompt: String,
    pub stream: bool,
    pub raw: bool,
    pub options: GenerateOptions,
}
#[derive(Deserialize)]
pub struct GenerateResponse {
    pub response: String,
    pub error: Option<String>,
}

pub struct OllamaClient {
    model: String,
    host: String,
    http_client: Client,
    temperature: f32,
    top_p: f32,
}

impl OllamaClient {
    pub fn new(model: String, host: String, temperature: f32, top_p: f32) -> Self {
        Self {
            model,
            host,
            http_client: Client::new(),
            temperature,
            top_p,
        }
    }

    pub async fn complete(
        &self,
        prompt: &str,
        max_new_tokens: usize,
    ) -> Result<String, Box<dyn std::error::Error>> {
        let url = format!("{}/api/generate", self.host);

        let request = GenerateRequest {
            model: self.model.clone(),
            prompt: prompt.to_string(),
            stream: false,
            raw: false,
            options: GenerateOptions {
                num_predict: max_new_tokens,
                temperature: self.temperature,
                top_p: self.top_p,
            },
        };

        let res = self
            .http_client
            .post(&url)
            .json(&request)
            .send()
            .await?
            .json::<GenerateResponse>()
            .await?;

        if let Some(err) = res.error {
            return Err(format!("Ollama error: {}", err).into());
        }
        Ok(res.response)
    }
}
