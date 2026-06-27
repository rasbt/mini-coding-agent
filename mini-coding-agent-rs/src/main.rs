mod agent;
mod ollama;
mod session;
mod tools;
mod workspace;

use agent::MiniAgent;
use ollama::OllamaClient;
use session::{Session, SessionStore};
use tools::ApprovalPolicy;
use workspace::WorkspaceContext;

use clap::Parser;
use std::io::{self, Write};

#[derive(Parser, Debug)]
#[command[author, version, about, long_about = None]]
struct Args {
    #[arg(short, long, default_value = "minimax-m3:cloud")]
    model: String,

    #[arg(long, default_value = "http://127.0.0.1:11434")]
    host: String,

    #[arg(long, default_value = ".")]
    cwd: String,

    #[arg(long)]
    resume: Option<String>,

    #[arg(long, default_value = "ask")]
    approval: String,

    #[arg(long, default_value_t = 6)]
    max_steps: usize,

    #[arg(long, default_value_t = 512)]
    max_new_tokens: usize,

    #[arg(long, default_value_t = 0.2)]
    temperature: f32,

    #[arg(long, default_value_t = 0.9)]
    top_p: f32,
}

fn build_welcome(agent: &MiniAgent, model: &str, host: &str) -> String {
    let art = [
        r#"/\     /\"#,
        r#"{  `---'  }"#,
        r#"{  O   O  }"#,
        r#"~~>  V  <~~"#,
        r#"\\  \|/  /"#,
        r#"`-----'__"#,
    ];

    let mut output = String::new();
    output.push_str(&format!("+{}+\n", "=".repeat(76)));
    for line in &art {
        output.push_str(&format!("| {:^74} |\n", line));
    }
    output.push_str(&format!("| {:^74} |\n", "MINI CODING AGENT RUST"));
    output.push_str(&format!("+{}+\n", "-".repeat(76)));

    let cwd_display = if agent.workspace.cwd.len() > 60 {
        format!(
            "...{}",
            &agent.workspace.cwd[agent.workspace.cwd.len() - 57..]
        )
    } else {
        agent.workspace.cwd.clone()
    };

    output.push_str(&format!("| WORKSPACE  {:<63} |\n", cwd_display));
    output.push_str(&format!(
        "| MODEL      {:<20} BRANCH  {:<33} |\n",
        model, agent.workspace.branch
    ));
    output.push_str(&format!(
        "| HOST       {:<20} SESSION {:<33} |\n",
        host, agent.session.id
    ));
    output.push_str(&format!("+{}+\n", "=".repeat(76)));
    output
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();

    let approval_policy = match args.approval.to_lowercase().as_str() {
        "auto" => ApprovalPolicy::Auto,
        "never" => ApprovalPolicy::Never,
        _ => ApprovalPolicy::Ask,
    };

    let workspace = WorkspaceContext::build(&args.cwd);
    let store = SessionStore::new(&workspace.repo_root);

    let session_id = if let Some(r) = args.resume {
        if r == "latest" {
            store
                .latest()
                .unwrap_or_else(|| Session::new(workspace.repo_root.clone()).id)
        } else {
            r
        }
    } else {
        Session::new(workspace.repo_root.clone()).id
    };

    let session = store
        .load(&session_id)
        .unwrap_or_else(|_| Session::new(workspace.repo_root.clone()));

    let client = OllamaClient::new(
        args.model.clone(),
        args.host.clone(),
        args.temperature,
        args.top_p,
    );

    let mut agent = MiniAgent::new(
        client,
        workspace,
        store,
        session,
        approval_policy,
        args.max_steps,
        args.max_new_tokens,
    );

    println!("{}", build_welcome(&agent, &args.model, &args.host));

    loop {
        print!("\nmini-coding-agent-rs> ");
        io::stdout().flush()?;

        let mut user_input = String::new();
        io::stdin().read_line(&mut user_input)?;
        let user_input = user_input.trim();

        if user_input.is_empty() {
            continue;
        }

        match user_input {
            "/exit" | "/quit" => break,
            "/help" => {
                println!("Commands:");
                println!("/help    Show this help message.");
                println!("/memory  Show the agent's distilled working memory.");
                println!("/session Show the path to the saved session file.");
                println!("/reset   Clear the current session history and memory.");
                println!("/exit    Exit the agent.");
            }
            "/memory" => println!("{}", agent.memory_text()),
            "/session" => {
                let session_path = agent.session_store.save(&agent.session)?;
                println!("{}", session_path.display())
            }
            "/reset" => {
                agent.session.history.clear();
                agent.session.memory.task.clear();
                agent.session.memory.files.clear();
                agent.session.memory.notes.clear();
                println!("session reset");
            }
            _ => {
                println!();
                let response = agent.ask(user_input).await;
                println!("\n{}", response);
            }
        }
    }
    Ok(())
}
