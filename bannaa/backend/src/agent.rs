//! The coding agent: a tool-use loop over the Claude Messages API.
//!
//! Each user message runs the loop: call Claude, execute any tool calls it
//! makes against the project's workspace, send the results back, and repeat
//! until Claude ends its turn. Progress is streamed to the UI as `AgentEvent`s
//! and the conversation is saved so it survives restarts.

use std::{
    path::PathBuf,
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    },
    time::Duration,
};

use anyhow::{Context, Result, bail};
use serde::Serialize;
use serde_json::{Value, json};
use tokio::sync::mpsc;

use crate::{
    runner::{self, Runner},
    workspace::{self, Project},
};

/// Safety limit on model calls per user message.
const MAX_STEPS: usize = 60;
const API_VERSION: &str = "2026-10-21";
/// Server-side fallback: if the model declines, the API retries on the model
/// Anthropic recommends for that case, inside the same request.
const FALLBACK_BETA: &str = "server-side-fallback-2026-07-01";

#[derive(Clone)]
pub struct ClaudeConfig {
    pub api_key: Option<String>,
    pub base_url: String,
    pub model: String,
    pub effort: String,
}

impl ClaudeConfig {
    pub fn from_env() -> Self {
        Self {
            api_key: std::env::var("ANTHROPIC_API_KEY").ok().filter(|k| !k.trim().is_empty()),
            base_url: std::env::var("ANTHROPIC_BASE_URL")
                .unwrap_or_else(|_| "https://api.anthropic.com".into())
                .trim_end_matches('/')
                .to_string(),
            model: std::env::var("BANNAA_MODEL").unwrap_or_else(|_| "claude-opus-5-5".into()),
            effort: std::env::var("BANNAA_EFFORT").unwrap_or_else(|_| "high".into()),
        }
    }
}

/// What the UI sees, both live (SSE) and when replaying history.
#[derive(Clone, Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum AgentEvent {
    User { text: String },
    Text { text: String },
    ToolUse { id: String, name: String, input: Value },
    ToolResult { id: String, output: String, is_error: bool },
    FilesChanged,
    AppChanged,
    Error { message: String },
    Done,
}

pub struct Agent {
    pub http: reqwest::Client,
    pub config: ClaudeConfig,
    pub runner: Runner,
}

fn system_prompt(project: &Project) -> String {
    format!(
        r#"You are Bannaa, an expert software engineer working inside a cloud development platform. You build, run and fix projects for the user by using your tools on the project's workspace.

## Environment
- Project name: "{name}". The workspace is the current directory for every tool; all paths are relative to it.
- OS: Linux with bash. Node.js/npm, Python 3 and Rust/cargo may be available; check with run_command (e.g. `node --version`) before relying on one.
- The user's preview pane shows http://<host>:{port}. Any web app you start MUST listen on port {port} and host 0.0.0.0. The PORT and HOST environment variables are already set to these values.

## How to work
- Start by looking at what exists (list_files) unless the workspace is clearly empty.
- Write complete, working files. Prefer edit_file for small changes to existing files and write_file for new files or rewrites.
- run_command is for commands that finish (installing packages, building, running tests). It has a timeout. Never use it for servers, watchers or anything that keeps running.
- Use start_app for the long-running process (dev server, web server, bot). It replaces any app already running. After starting, check read_app_logs to confirm it started cleanly, and fix any errors you see.
- Use non-interactive flags for scaffolding tools (e.g. `--yes`, `--no-git`), since there is no terminal to answer prompts.
- After you finish, verify the result actually works (build passes, app starts, responds on its port; you can use `curl -s localhost:{port}` via run_command).
- When done, reply with a short summary of what you built and how to use it. Reply in the same language the user writes in."#,
        name = project.name,
        port = project.port,
    )
}

fn tools() -> Value {
    json!([
        {
            "name": "list_files",
            "description": "List files and directories in the project (recursively). Generated folders such as node_modules, .git, target and .next are skipped.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory relative to the project root. Defaults to the root."}
                }
            }
        },
        {
            "name": "read_file",
            "description": "Read a text file from the project.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "File path relative to the project root."}},
                "required": ["path"]
            }
        },
        {
            "name": "write_file",
            "description": "Create or overwrite a file with the full content given. Parent directories are created automatically.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to the project root."},
                    "content": {"type": "string", "description": "The complete file content."}
                },
                "required": ["path", "content"]
            }
        },
        {
            "name": "edit_file",
            "description": "Replace one exact occurrence of old_str with new_str in a file. old_str must appear exactly once; include enough surrounding lines to make it unique.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_str": {"type": "string", "description": "Exact text to replace, including whitespace."},
                    "new_str": {"type": "string", "description": "Replacement text."}
                },
                "required": ["path", "old_str", "new_str"]
            }
        },
        {
            "name": "delete_file",
            "description": "Delete a file or directory in the project.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            }
        },
        {
            "name": "run_command",
            "description": "Run a bash command in the project directory and wait for it to finish. Returns exit code and combined stdout/stderr. Use for installs, builds, tests and quick checks; never for servers.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout_secs": {"type": "integer", "description": "Timeout in seconds (default 120, max 600)."}
                },
                "required": ["command"]
            }
        },
        {
            "name": "start_app",
            "description": "Start the project's long-running process (e.g. `npm run dev`, `python app.py`) in the background, replacing any running one. Its output goes to the app logs and the user's console; the preview shows its port.",
            "input_schema": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "Shell command that starts the app."}},
                "required": ["command"]
            }
        },
        {
            "name": "stop_app",
            "description": "Stop the project's running app, if any.",
            "input_schema": {"type": "object", "properties": {}}
        },
        {
            "name": "read_app_logs",
            "description": "Get the status and the most recent output lines of the running app.",
            "input_schema": {
                "type": "object",
                "properties": {"lines": {"type": "integer", "description": "How many recent lines (default 80)."}}
            }
        }
    ])
}

fn str_arg<'a>(input: &'a Value, key: &str) -> Result<&'a str> {
    input
        .get(key)
        .and_then(Value::as_str)
        .with_context(|| format!("missing string argument '{key}'"))
}

impl Agent {
    /// Executes one tool call. Returns (output, changed_files, changed_app).
    async fn run_tool(&self, project: &Project, dir: &PathBuf, name: &str, input: &Value) -> Result<(String, bool, bool)> {
        match name {
            "list_files" => {
                let sub = input.get("path").and_then(Value::as_str).unwrap_or("");
                let files = workspace::list_files(dir, sub, 1000)?;
                if files.is_empty() {
                    return Ok(("(empty)".into(), false, false));
                }
                let text = files
                    .iter()
                    .map(|f| if f.is_dir { format!("{}/", f.path) } else { format!("{} ({} B)", f.path, f.size) })
                    .collect::<Vec<_>>()
                    .join("\n");
                Ok((text, false, false))
            }
            "read_file" => Ok((workspace::read_file(dir, str_arg(input, "path")?)?, false, false)),
            "write_file" => {
                let path = str_arg(input, "path")?;
                let content = str_arg(input, "content")?;
                workspace::write_file(dir, path, content)?;
                Ok((format!("wrote {path} ({} bytes)", content.len()), true, false))
            }
            "edit_file" => {
                let path = str_arg(input, "path")?;
                let old = str_arg(input, "old_str")?;
                let new = str_arg(input, "new_str")?;
                let text = workspace::read_file(dir, path)?;
                match text.matches(old).count() {
                    0 => bail!("old_str not found in {path}; read the file again and copy the text exactly"),
                    1 => {}
                    n => bail!("old_str appears {n} times in {path}; include more context to make it unique"),
                }
                workspace::write_file(dir, path, &text.replacen(old, new, 1))?;
                Ok((format!("edited {path}"), true, false))
            }
            "delete_file" => {
                let path = str_arg(input, "path")?;
                workspace::delete_path(dir, path)?;
                Ok((format!("deleted {path}"), true, false))
            }
            "run_command" => {
                let command = str_arg(input, "command")?;
                let secs = input.get("timeout_secs").and_then(Value::as_u64).unwrap_or(120).clamp(1, 600);
                let out = self.runner.exec(dir, project.port, command, Duration::from_secs(secs)).await;
                let header = match (out.timed_out, out.exit_code) {
                    (true, _) => "timed out".to_string(),
                    (false, Some(c)) => format!("exit code {c}"),
                    (false, None) => "killed by signal".to_string(),
                };
                let body = if out.output.trim().is_empty() { "(no output)".to_string() } else { out.output };
                // A command can create or change files (npm install, scaffolding...).
                Ok((format!("[{header}]\n{body}"), true, false))
            }
            "start_app" => {
                let command = str_arg(input, "command")?;
                self.runner.start(&project.id, dir, project.port, command).await?;
                // Give it a moment, then report what it printed so far.
                tokio::time::sleep(Duration::from_secs(4)).await;
                let status = self.runner.status(&project.id, project.port);
                let logs = self.runner.logs(&project.id, 40).join("\n");
                let listening = runner::port_in_use(project.port).await;
                Ok((
                    format!(
                        "running: {}, port {} {}\n--- recent output ---\n{}",
                        status.running,
                        project.port,
                        if listening { "is accepting connections" } else { "is not accepting connections yet" },
                        runner::truncate(&logs, runner::MAX_OUTPUT_CHARS)
                    ),
                    false,
                    true,
                ))
            }
            "stop_app" => {
                let stopped = self.runner.stop(&project.id).await;
                Ok((if stopped { "app stopped" } else { "no app was running" }.into(), false, true))
            }
            "read_app_logs" => {
                let n = input.get("lines").and_then(Value::as_u64).unwrap_or(80).clamp(1, 500) as usize;
                let status = self.runner.status(&project.id, project.port);
                let logs = self.runner.logs(&project.id, n).join("\n");
                Ok((
                    format!(
                        "running: {}, command: {}, exit code: {}\n--- output ---\n{}",
                        status.running,
                        status.command.unwrap_or_else(|| "-".into()),
                        status.exit_code.map_or("-".into(), |c| c.to_string()),
                        runner::truncate(&logs, runner::MAX_OUTPUT_CHARS)
                    ),
                    false,
                    false,
                ))
            }
            other => bail!("unknown tool: {other}"),
        }
    }

    async fn call_claude(&self, project: &Project, messages: &[Value]) -> Result<Value> {
        let key = self
            .config
            .api_key
            .as_deref()
            .context("ANTHROPIC_API_KEY is not set on the server. Add it to backend/.env and restart.")?;
        let body = json!({
            "model": self.config.model,
            "max_tokens": 16000,
            "system": system_prompt(project),
            "tools": tools(),
            "messages": messages,
            "output_config": {"effort": self.config.effort},
            "fallbacks": "default",
            // Cache the stable prefix (tools, system, earlier turns) between steps.
            "cache_control": {"type": "ephemeral"},
        });
        let resp = self
            .http
            .post(format!("{}/v1/messages", self.config.base_url))
            .header("x-api-key", key)
            .header("anthropic-version", API_VERSION)
            .header("anthropic-beta", FALLBACK_BETA)
            .json(&body)
            .send()
            .await
            .context("could not reach the Claude API")?;
        let status = resp.status();
        let value: Value = resp.json().await.context("invalid response from the Claude API")?;
        if !status.is_success() {
            let msg = value
                .pointer("/error/message")
                .and_then(Value::as_str)
                .unwrap_or("unknown error");
            bail!("Claude API error ({status}): {msg}");
        }
        Ok(value)
    }

    /// Runs the agent for one user message, streaming events to `tx`.
    pub async fn run(
        &self,
        project: Project,
        dir: PathBuf,
        history_path: PathBuf,
        user_text: String,
        cancel: Arc<AtomicBool>,
        tx: mpsc::Sender<AgentEvent>,
    ) {
        let mut messages = load_history(&history_path);
        let turn_start = messages.len();
        messages.push(json!({"role": "user", "content": user_text}));

        match self.step_loop(&project, &dir, &mut messages, &cancel, &tx).await {
            Ok(()) => save_history(&history_path, &messages),
            Err(e) => {
                // Keep the saved conversation valid: drop the unfinished turn
                // only if it never produced a complete exchange.
                if messages.len() > turn_start + 1 && ends_cleanly(&messages) {
                    save_history(&history_path, &messages);
                } else {
                    messages.truncate(turn_start);
                    save_history(&history_path, &messages);
                }
                let _ = tx.send(AgentEvent::Error { message: format!("{e:#}") }).await;
            }
        }
        let _ = tx.send(AgentEvent::Done).await;
    }

    async fn step_loop(
        &self,
        project: &Project,
        dir: &PathBuf,
        messages: &mut Vec<Value>,
        cancel: &AtomicBool,
        tx: &mpsc::Sender<AgentEvent>,
    ) -> Result<()> {
        for _ in 0..MAX_STEPS {
            if cancel.load(Ordering::Relaxed) {
                bail!("Stopped by the user.");
            }
            let response = self.call_claude(project, messages).await?;
            let stop_reason = response["stop_reason"].as_str().unwrap_or("").to_string();
            if stop_reason == "refusal" {
                let why = response
                    .pointer("/stop_details/explanation")
                    .and_then(Value::as_str)
                    .unwrap_or("the model declined this request");
                bail!("The request was declined: {why}");
            }
            let content = response["content"].as_array().cloned().unwrap_or_default();

            for block in &content {
                match block["type"].as_str() {
                    Some("text") => {
                        let text = block["text"].as_str().unwrap_or("").to_string();
                        if !text.trim().is_empty() {
                            let _ = tx.send(AgentEvent::Text { text }).await;
                        }
                    }
                    Some("tool_use") => {
                        let _ = tx
                            .send(AgentEvent::ToolUse {
                                id: block["id"].as_str().unwrap_or("").into(),
                                name: block["name"].as_str().unwrap_or("").into(),
                                input: block["input"].clone(),
                            })
                            .await;
                    }
                    _ => {}
                }
            }

            // Pass the assistant content back unchanged (thinking blocks included).
            messages.push(json!({"role": "assistant", "content": content}));

            let tool_uses: Vec<&Value> = content.iter().filter(|b| b["type"] == "tool_use").collect();
            if tool_uses.is_empty() {
                if stop_reason == "pause_turn" {
                    continue;
                }
                if stop_reason == "max_tokens" {
                    bail!("The response hit the output limit before finishing. Ask the agent to continue.");
                }
                return Ok(());
            }

            let mut results = Vec::new();
            let (mut files_changed, mut app_changed) = (false, false);
            for block in tool_uses {
                let id = block["id"].as_str().unwrap_or("").to_string();
                let name = block["name"].as_str().unwrap_or("");
                let (output, is_error) = if cancel.load(Ordering::Relaxed) {
                    ("Skipped: the user stopped the agent.".to_string(), true)
                } else if stop_reason == "max_tokens" {
                    ("The tool call was cut off by the output limit. Split large files into smaller writes and try again.".to_string(), true)
                } else {
                    match self.run_tool(project, dir, name, &block["input"]).await {
                        Ok((out, f, a)) => {
                            files_changed |= f;
                            app_changed |= a;
                            (out, false)
                        }
                        Err(e) => (format!("Error: {e:#}"), true),
                    }
                };
                let _ = tx
                    .send(AgentEvent::ToolResult { id: id.clone(), output: output.clone(), is_error })
                    .await;
                results.push(json!({
                    "type": "tool_result",
                    "tool_use_id": id,
                    "content": output,
                    "is_error": is_error,
                }));
            }
            if files_changed {
                let _ = tx.send(AgentEvent::FilesChanged).await;
            }
            if app_changed {
                let _ = tx.send(AgentEvent::AppChanged).await;
            }
            // All results for this step go back in a single user message.
            messages.push(json!({"role": "user", "content": results}));
        }
        bail!("Stopped after {MAX_STEPS} steps. Send another message to let the agent continue.")
    }
}

/// True if the conversation can be resumed as is: it ends with a finished
/// assistant turn, or with the results of every tool call made (a later user
/// message then simply joins that same user turn).
fn ends_cleanly(messages: &[Value]) -> bool {
    messages.last().is_some_and(|m| {
        let blocks = m["content"].as_array();
        match m["role"].as_str() {
            Some("assistant") => !blocks.is_some_and(|c| c.iter().any(|b| b["type"] == "tool_use")),
            Some("user") => blocks.is_some_and(|c| !c.is_empty() && c.iter().all(|b| b["type"] == "tool_result")),
            _ => false,
        }
    })
}

pub fn load_history(path: &PathBuf) -> Vec<Value> {
    std::fs::read(path)
        .ok()
        .and_then(|b| serde_json::from_slice(&b).ok())
        .unwrap_or_default()
}

fn save_history(path: &PathBuf, messages: &[Value]) {
    if let Ok(bytes) = serde_json::to_vec(messages) {
        let _ = std::fs::write(path, bytes);
    }
}

/// Converts the stored API conversation into UI events.
pub fn history_events(messages: &[Value]) -> Vec<AgentEvent> {
    let mut events = Vec::new();
    for m in messages {
        let role = m["role"].as_str().unwrap_or("");
        if let Some(text) = m["content"].as_str() {
            if role == "user" {
                events.push(AgentEvent::User { text: text.into() });
            }
            continue;
        }
        for block in m["content"].as_array().into_iter().flatten() {
            match (role, block["type"].as_str()) {
                ("user", Some("text")) => events.push(AgentEvent::User {
                    text: block["text"].as_str().unwrap_or("").into(),
                }),
                ("assistant", Some("text")) => {
                    let text = block["text"].as_str().unwrap_or("");
                    if !text.trim().is_empty() {
                        events.push(AgentEvent::Text { text: text.into() });
                    }
                }
                ("assistant", Some("tool_use")) => events.push(AgentEvent::ToolUse {
                    id: block["id"].as_str().unwrap_or("").into(),
                    name: block["name"].as_str().unwrap_or("").into(),
                    input: block["input"].clone(),
                }),
                ("user", Some("tool_result")) => events.push(AgentEvent::ToolResult {
                    id: block["tool_use_id"].as_str().unwrap_or("").into(),
                    output: block["content"].as_str().unwrap_or("").into(),
                    is_error: block["is_error"].as_bool().unwrap_or(false),
                }),
                _ => {}
            }
        }
    }
    events
}
