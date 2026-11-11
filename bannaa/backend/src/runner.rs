//! Running commands inside a project: one-off commands (with a timeout) and a
//! single long-running "app" process per project whose output is kept for the
//! console and whose port backs the preview.

use std::{
    collections::{HashMap, VecDeque},
    path::Path,
    process::Stdio,
    sync::{Arc, Mutex},
    time::Duration,
};

use serde::Serialize;
use tokio::{
    io::{AsyncBufReadExt, AsyncRead, BufReader},
    process::{Child, Command},
    sync::broadcast,
};

const MAX_LOG_LINES: usize = 2000;
/// Upper bound on command output returned to the agent or the UI.
pub const MAX_OUTPUT_CHARS: usize = 20_000;

#[derive(Clone, Serialize)]
pub struct RunStatus {
    pub running: bool,
    pub command: Option<String>,
    pub port: u16,
    pub exit_code: Option<i32>,
}

struct App {
    command: String,
    pid: Option<u32>,
    running: bool,
    exit_code: Option<i32>,
}

struct ProjectRun {
    app: Option<App>,
    logs: VecDeque<String>,
    tx: broadcast::Sender<String>,
}

impl ProjectRun {
    fn new() -> Self {
        Self {
            app: None,
            logs: VecDeque::new(),
            tx: broadcast::channel(512).0,
        }
    }

    fn push_log(&mut self, line: String) {
        if self.logs.len() >= MAX_LOG_LINES {
            self.logs.pop_front();
        }
        self.logs.push_back(line.clone());
        let _ = self.tx.send(line);
    }
}

#[derive(Clone, Default)]
pub struct Runner {
    inner: Arc<Mutex<HashMap<String, ProjectRun>>>,
}

#[derive(Serialize)]
pub struct CommandOutput {
    pub exit_code: Option<i32>,
    pub timed_out: bool,
    pub output: String,
}

fn shell(command: &str, dir: &Path, port: u16) -> Command {
    let mut cmd = Command::new("bash");
    cmd.arg("-lc")
        .arg(command)
        .current_dir(dir)
        .env("PORT", port.to_string())
        .env("HOST", "0.0.0.0")
        .env("CI", "1")
        .env("FORCE_COLOR", "0")
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        // New process group, so stopping kills the whole tree (npm -> node, ...).
        .process_group(0)
        .kill_on_drop(true);
    cmd
}

fn kill_group(pid: u32) {
    // SAFETY: plain syscall; a negative pid targets the process group.
    unsafe {
        libc::kill(-(pid as i32), libc::SIGTERM);
    }
    tokio::spawn(async move {
        tokio::time::sleep(Duration::from_secs(3)).await;
        unsafe {
            libc::kill(-(pid as i32), libc::SIGKILL);
        }
    });
}

pub fn truncate(s: &str, max: usize) -> String {
    if s.chars().count() <= max {
        return s.to_string();
    }
    // Keep the head and the tail: errors usually show up at the end.
    let head: String = s.chars().take(max / 4).collect();
    let tail: String = {
        let chars: Vec<char> = s.chars().collect();
        chars[chars.len() - (max * 3 / 4)..].iter().collect()
    };
    format!("{head}\n\n... [output truncated] ...\n\n{tail}")
}

impl Runner {
    /// Runs a command to completion (or until `timeout`) and returns its output.
    pub async fn exec(&self, dir: &Path, port: u16, command: &str, timeout: Duration) -> CommandOutput {
        let mut child = match shell(command, dir, port).spawn() {
            Ok(c) => c,
            Err(e) => {
                return CommandOutput {
                    exit_code: None,
                    timed_out: false,
                    output: format!("failed to start command: {e}"),
                };
            }
        };
        let pid = child.id();
        let stdout = child.stdout.take();
        let stderr = child.stderr.take();
        let collect = async move {
            let (out, err) = tokio::join!(read_all(stdout), read_all(stderr));
            (out, err)
        };
        let result = tokio::time::timeout(timeout, async {
            let (out, err) = collect.await;
            let status = child.wait().await;
            (out, err, status)
        })
        .await;

        match result {
            Ok((out, err, status)) => {
                let mut output = out;
                if !err.is_empty() {
                    if !output.is_empty() && !output.ends_with('\n') {
                        output.push('\n');
                    }
                    output.push_str(&err);
                }
                CommandOutput {
                    exit_code: status.ok().and_then(|s| s.code()),
                    timed_out: false,
                    output: truncate(&output, MAX_OUTPUT_CHARS),
                }
            }
            Err(_) => {
                if let Some(pid) = pid {
                    kill_group(pid);
                }
                CommandOutput {
                    exit_code: None,
                    timed_out: true,
                    output: format!(
                        "command timed out after {}s and was stopped. \
                         For servers or watchers, use start_app instead.",
                        timeout.as_secs()
                    ),
                }
            }
        }
    }

    /// Starts (or restarts) the project's long-running app.
    pub async fn start(&self, project_id: &str, dir: &Path, port: u16, command: &str) -> anyhow::Result<()> {
        self.stop(project_id).await;
        // Wait briefly for the previous process group to release the port.
        for _ in 0..20 {
            if !port_in_use(port).await {
                break;
            }
            tokio::time::sleep(Duration::from_millis(250)).await;
        }

        let mut child: Child = shell(command, dir, port).spawn()?;
        let pid = child.id();
        {
            let mut map = self.inner.lock().unwrap();
            let run = map.entry(project_id.to_string()).or_insert_with(ProjectRun::new);
            run.logs.clear();
            run.push_log(format!("$ {command}   (PORT={port})"));
            run.app = Some(App {
                command: command.to_string(),
                pid,
                running: true,
                exit_code: None,
            });
        }

        if let Some(out) = child.stdout.take() {
            self.pump(project_id, out);
        }
        if let Some(err) = child.stderr.take() {
            self.pump(project_id, err);
        }

        let inner = self.inner.clone();
        let id = project_id.to_string();
        tokio::spawn(async move {
            let status = child.wait().await;
            let code = status.ok().and_then(|s| s.code());
            let mut map = inner.lock().unwrap();
            if let Some(run) = map.get_mut(&id) {
                // Only record the exit if this is still the current process.
                let current = run.app.as_ref().map(|a| a.pid) == Some(pid);
                if current {
                    if let Some(app) = run.app.as_mut() {
                        app.running = false;
                        app.exit_code = code;
                    }
                    run.push_log(format!("[process exited with code {}]", code.map_or("?".into(), |c| c.to_string())));
                }
            }
        });
        Ok(())
    }

    fn pump<R: AsyncRead + Unpin + Send + 'static>(&self, project_id: &str, reader: R) {
        let inner = self.inner.clone();
        let id = project_id.to_string();
        tokio::spawn(async move {
            let mut lines = BufReader::new(reader).lines();
            while let Ok(Some(line)) = lines.next_line().await {
                if let Some(run) = inner.lock().unwrap().get_mut(&id) {
                    run.push_log(line);
                }
            }
        });
    }

    pub async fn stop(&self, project_id: &str) -> bool {
        let pid = {
            let mut map = self.inner.lock().unwrap();
            let Some(run) = map.get_mut(project_id) else { return false };
            let Some(app) = run.app.as_mut() else { return false };
            if !app.running {
                return false;
            }
            app.running = false;
            let pid = app.pid;
            run.push_log("[stopped]".into());
            pid
        };
        if let Some(pid) = pid {
            kill_group(pid);
        }
        true
    }

    pub fn status(&self, project_id: &str, port: u16) -> RunStatus {
        let map = self.inner.lock().unwrap();
        let app = map.get(project_id).and_then(|r| r.app.as_ref());
        RunStatus {
            running: app.is_some_and(|a| a.running),
            command: app.map(|a| a.command.clone()),
            port,
            exit_code: app.and_then(|a| a.exit_code),
        }
    }

    pub fn logs(&self, project_id: &str, last: usize) -> Vec<String> {
        let map = self.inner.lock().unwrap();
        map.get(project_id)
            .map(|r| r.logs.iter().rev().take(last).rev().cloned().collect())
            .unwrap_or_default()
    }

    pub fn subscribe(&self, project_id: &str) -> broadcast::Receiver<String> {
        let mut map = self.inner.lock().unwrap();
        map.entry(project_id.to_string())
            .or_insert_with(ProjectRun::new)
            .tx
            .subscribe()
    }

    pub async fn stop_all(&self) {
        let ids: Vec<String> = self.inner.lock().unwrap().keys().cloned().collect();
        for id in ids {
            self.stop(&id).await;
        }
    }
}

async fn read_all<R: AsyncRead + Unpin>(reader: Option<R>) -> String {
    let Some(reader) = reader else { return String::new() };
    let mut lines = BufReader::new(reader).lines();
    let mut out = String::new();
    while let Ok(Some(line)) = lines.next_line().await {
        // Keep memory bounded on very chatty commands.
        if out.len() < MAX_OUTPUT_CHARS * 8 {
            out.push_str(&line);
            out.push('\n');
        }
    }
    out
}

pub async fn port_in_use(port: u16) -> bool {
    tokio::net::TcpStream::connect(("127.0.0.1", port)).await.is_ok()
}
