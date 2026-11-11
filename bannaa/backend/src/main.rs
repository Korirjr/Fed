mod agent;
mod runner;
mod workspace;

use std::{
    collections::HashMap,
    convert::Infallible,
    net::SocketAddr,
    path::PathBuf,
    sync::{Arc, Mutex, atomic::{AtomicBool, Ordering}},
    time::Duration,
};

use axum::{
    Json, Router,
    extract::{Path, Query, State},
    http::StatusCode,
    response::{
        IntoResponse, Response,
        sse::{Event, KeepAlive, Sse},
    },
    routing::{get, post},
};
use futures_util::{Stream, StreamExt, stream};
use serde::Deserialize;
use serde_json::json;
use tokio_stream::wrappers::{BroadcastStream, ReceiverStream};
use tower_http::{cors::CorsLayer, trace::TraceLayer};

use agent::{Agent, AgentEvent, ClaudeConfig};
use runner::Runner;
use workspace::{Project, Workspaces};

#[derive(Clone)]
struct AppState {
    workspaces: Arc<Workspaces>,
    runner: Runner,
    agent: Arc<Agent>,
    /// Projects with an agent run in progress (one at a time per project),
    /// each with a flag that asks the run to stop.
    busy: Arc<Mutex<HashMap<String, Arc<AtomicBool>>>>,
}

struct ApiError(StatusCode, String);

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        (self.0, Json(json!({ "error": self.1 }))).into_response()
    }
}

impl From<anyhow::Error> for ApiError {
    fn from(e: anyhow::Error) -> Self {
        ApiError(StatusCode::BAD_REQUEST, format!("{e:#}"))
    }
}

type ApiResult<T> = Result<T, ApiError>;

fn project(state: &AppState, id: &str) -> ApiResult<Project> {
    state
        .workspaces
        .get(id)?
        .ok_or_else(|| ApiError(StatusCode::NOT_FOUND, "project not found".into()))
}

// ---------- projects ----------

async fn health(State(state): State<AppState>) -> Json<serde_json::Value> {
    Json(json!({
        "status": "ok",
        "agent_ready": state.agent.config.api_key.is_some(),
        "model": state.agent.config.model,
    }))
}

async fn list_projects(State(state): State<AppState>) -> ApiResult<Json<Vec<Project>>> {
    Ok(Json(state.workspaces.list()?))
}

#[derive(Deserialize)]
struct CreateProject {
    name: String,
}

async fn create_project(State(state): State<AppState>, Json(input): Json<CreateProject>) -> ApiResult<(StatusCode, Json<Project>)> {
    let name = input.name.trim();
    if name.is_empty() || name.chars().count() > 80 {
        return Err(ApiError(StatusCode::BAD_REQUEST, "name must be 1-80 characters".into()));
    }
    Ok((StatusCode::CREATED, Json(state.workspaces.create(name)?)))
}

async fn get_project(State(state): State<AppState>, Path(id): Path<String>) -> ApiResult<Json<Project>> {
    Ok(Json(project(&state, &id)?))
}

async fn delete_project(State(state): State<AppState>, Path(id): Path<String>) -> ApiResult<StatusCode> {
    project(&state, &id)?;
    state.runner.stop(&id).await;
    state.workspaces.delete(&id)?;
    Ok(StatusCode::NO_CONTENT)
}

// ---------- files ----------

async fn list_files(State(state): State<AppState>, Path(id): Path<String>) -> ApiResult<Json<Vec<workspace::FileEntry>>> {
    project(&state, &id)?;
    Ok(Json(workspace::list_files(&state.workspaces.dir(&id), "", 5000)?))
}

#[derive(Deserialize)]
struct PathQuery {
    path: String,
}

async fn read_file(State(state): State<AppState>, Path(id): Path<String>, Query(q): Query<PathQuery>) -> ApiResult<Json<serde_json::Value>> {
    project(&state, &id)?;
    let content = workspace::read_file(&state.workspaces.dir(&id), &q.path)?;
    Ok(Json(json!({ "path": q.path, "content": content })))
}

#[derive(Deserialize)]
struct WriteFile {
    content: String,
}

async fn write_file(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Query(q): Query<PathQuery>,
    Json(input): Json<WriteFile>,
) -> ApiResult<StatusCode> {
    project(&state, &id)?;
    workspace::write_file(&state.workspaces.dir(&id), &q.path, &input.content)?;
    Ok(StatusCode::NO_CONTENT)
}

async fn delete_file(State(state): State<AppState>, Path(id): Path<String>, Query(q): Query<PathQuery>) -> ApiResult<StatusCode> {
    project(&state, &id)?;
    workspace::delete_path(&state.workspaces.dir(&id), &q.path)?;
    Ok(StatusCode::NO_CONTENT)
}

// ---------- commands & app ----------

#[derive(Deserialize)]
struct CommandInput {
    command: String,
}

async fn exec(State(state): State<AppState>, Path(id): Path<String>, Json(input): Json<CommandInput>) -> ApiResult<Json<runner::CommandOutput>> {
    let p = project(&state, &id)?;
    let out = state
        .runner
        .exec(&state.workspaces.dir(&id), p.port, &input.command, Duration::from_secs(300))
        .await;
    Ok(Json(out))
}

async fn run_status(State(state): State<AppState>, Path(id): Path<String>) -> ApiResult<Json<runner::RunStatus>> {
    let p = project(&state, &id)?;
    Ok(Json(state.runner.status(&id, p.port)))
}

async fn run_start(State(state): State<AppState>, Path(id): Path<String>, Json(input): Json<CommandInput>) -> ApiResult<Json<runner::RunStatus>> {
    let p = project(&state, &id)?;
    if input.command.trim().is_empty() {
        return Err(ApiError(StatusCode::BAD_REQUEST, "command is empty".into()));
    }
    state.runner.start(&id, &state.workspaces.dir(&id), p.port, &input.command).await?;
    Ok(Json(state.runner.status(&id, p.port)))
}

async fn run_stop(State(state): State<AppState>, Path(id): Path<String>) -> ApiResult<Json<runner::RunStatus>> {
    let p = project(&state, &id)?;
    state.runner.stop(&id).await;
    Ok(Json(state.runner.status(&id, p.port)))
}

/// Streams the app's output: recent backlog first, then live lines.
async fn run_logs(State(state): State<AppState>, Path(id): Path<String>) -> ApiResult<Sse<impl Stream<Item = Result<Event, Infallible>>>> {
    project(&state, &id)?;
    let live = state.runner.subscribe(&id);
    let backlog = state.runner.logs(&id, 500);
    let backlog = stream::iter(backlog.into_iter().map(|l| Ok(Event::default().data(l))));
    let live = BroadcastStream::new(live).filter_map(|r| async move { r.ok().map(|l| Ok(Event::default().data(l))) });
    Ok(Sse::new(backlog.chain(live)).keep_alive(KeepAlive::default()))
}

// ---------- agent ----------

#[derive(Deserialize)]
struct AgentInput {
    message: String,
}

/// Clears the busy flag when the agent task ends, even if it panics.
struct BusyGuard(Arc<Mutex<HashMap<String, Arc<AtomicBool>>>>, String);

impl Drop for BusyGuard {
    fn drop(&mut self) {
        self.0.lock().unwrap().remove(&self.1);
    }
}

async fn agent_run(
    State(state): State<AppState>,
    Path(id): Path<String>,
    Json(input): Json<AgentInput>,
) -> ApiResult<Sse<impl Stream<Item = Result<Event, Infallible>>>> {
    let p = project(&state, &id)?;
    let message = input.message.trim().to_string();
    if message.is_empty() {
        return Err(ApiError(StatusCode::BAD_REQUEST, "message is empty".into()));
    }
    let cancel = Arc::new(AtomicBool::new(false));
    {
        let mut busy = state.busy.lock().unwrap();
        if busy.contains_key(&id) {
            return Err(ApiError(StatusCode::CONFLICT, "the agent is already working on this project".into()));
        }
        busy.insert(id.clone(), cancel.clone());
    }
    let guard = BusyGuard(state.busy.clone(), id.clone());

    let (tx, rx) = tokio::sync::mpsc::channel::<AgentEvent>(256);
    let agent = state.agent.clone();
    let dir = state.workspaces.dir(&id);
    let history = state.workspaces.history_path(&id);
    // The run continues even if the browser disconnects; the result is saved.
    tokio::spawn(async move {
        let _guard = guard;
        agent.run(p, dir, history, message, cancel, tx).await;
    });

    let events = ReceiverStream::new(rx).map(|ev| Ok(Event::default().json_data(ev).unwrap_or_default()));
    Ok(Sse::new(events).keep_alive(KeepAlive::default()))
}

async fn agent_history(State(state): State<AppState>, Path(id): Path<String>) -> ApiResult<Json<serde_json::Value>> {
    project(&state, &id)?;
    let messages = agent::load_history(&state.workspaces.history_path(&id));
    let busy = state.busy.lock().unwrap().contains_key(&id);
    Ok(Json(json!({ "busy": busy, "events": agent::history_events(&messages) })))
}

async fn agent_clear(State(state): State<AppState>, Path(id): Path<String>) -> ApiResult<StatusCode> {
    project(&state, &id)?;
    if state.busy.lock().unwrap().contains_key(&id) {
        return Err(ApiError(StatusCode::CONFLICT, "the agent is still working".into()));
    }
    let _ = std::fs::remove_file(state.workspaces.history_path(&id));
    Ok(StatusCode::NO_CONTENT)
}

/// Asks a running agent to stop after its current step.
async fn agent_stop(State(state): State<AppState>, Path(id): Path<String>) -> ApiResult<StatusCode> {
    project(&state, &id)?;
    if let Some(flag) = state.busy.lock().unwrap().get(&id) {
        flag.store(true, Ordering::Relaxed);
    }
    Ok(StatusCode::NO_CONTENT)
}

fn app(state: AppState) -> Router {
    Router::new()
        .route("/api/health", get(health))
        .route("/api/projects", get(list_projects).post(create_project))
        .route("/api/projects/{id}", get(get_project).delete(delete_project))
        .route("/api/projects/{id}/files", get(list_files))
        .route("/api/projects/{id}/file", get(read_file).put(write_file).delete(delete_file))
        .route("/api/projects/{id}/exec", post(exec))
        .route("/api/projects/{id}/run", get(run_status))
        .route("/api/projects/{id}/run/start", post(run_start))
        .route("/api/projects/{id}/run/stop", post(run_stop))
        .route("/api/projects/{id}/run/logs", get(run_logs))
        .route("/api/projects/{id}/agent", post(agent_run))
        .route("/api/projects/{id}/agent/history", get(agent_history).delete(agent_clear))
        .route("/api/projects/{id}/agent/stop", post(agent_stop))
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let _ = dotenvy::dotenv();
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env().unwrap_or_else(|_| "bannaa_server=info,tower_http=warn".into()),
        )
        .init();

    let data_dir = PathBuf::from(std::env::var("BANNAA_DATA_DIR").unwrap_or_else(|_| "data".into()));
    let config = ClaudeConfig::from_env();
    if config.api_key.is_none() {
        tracing::warn!("ANTHROPIC_API_KEY is not set: the editor works, but the agent cannot run until you add it");
    }
    let runner = Runner::default();
    let state = AppState {
        workspaces: Arc::new(Workspaces::new(data_dir)?),
        runner: runner.clone(),
        agent: Arc::new(Agent {
            http: reqwest::Client::builder().timeout(Duration::from_secs(600)).build()?,
            config,
            runner: runner.clone(),
        }),
        busy: Arc::default(),
    };

    let port: u16 = std::env::var("PORT").ok().and_then(|p| p.parse().ok()).unwrap_or(8080);
    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    let listener = tokio::net::TcpListener::bind(addr).await?;
    tracing::info!("Bannaa API listening on http://{addr}");
    axum::serve(listener, app(state))
        .with_graceful_shutdown(async move {
            let _ = tokio::signal::ctrl_c().await;
            runner.stop_all().await;
        })
        .await?;
    Ok(())
}
