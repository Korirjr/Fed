use std::{
    collections::HashMap,
    net::SocketAddr,
    sync::{Arc, RwLock},
};

use axum::{
    Json, Router,
    extract::{Path, State},
    http::StatusCode,
    routing::get,
};
use serde::{Deserialize, Serialize};
use tower_http::{cors::CorsLayer, trace::TraceLayer};
use uuid::Uuid;

#[derive(Clone, Serialize)]
struct Task {
    id: Uuid,
    title: String,
    done: bool,
}

#[derive(Deserialize)]
struct CreateTask {
    title: String,
}

#[derive(Deserialize)]
struct UpdateTask {
    title: Option<String>,
    done: Option<bool>,
}

/// In-memory store. Insertion order is kept in `order` so the list is stable.
#[derive(Default)]
struct Store {
    tasks: HashMap<Uuid, Task>,
    order: Vec<Uuid>,
}

type AppState = Arc<RwLock<Store>>;

type ApiError = (StatusCode, Json<serde_json::Value>);

fn error(status: StatusCode, msg: &str) -> ApiError {
    (status, Json(serde_json::json!({ "error": msg })))
}

fn validate_title(title: &str) -> Result<String, ApiError> {
    let title = title.trim();
    if title.is_empty() {
        return Err(error(StatusCode::BAD_REQUEST, "title must not be empty"));
    }
    if title.chars().count() > 200 {
        return Err(error(StatusCode::BAD_REQUEST, "title is too long (max 200)"));
    }
    Ok(title.to_string())
}

async fn health() -> Json<serde_json::Value> {
    Json(serde_json::json!({ "status": "ok" }))
}

async fn list_tasks(State(state): State<AppState>) -> Json<Vec<Task>> {
    let store = state.read().unwrap();
    Json(store.order.iter().map(|id| store.tasks[id].clone()).collect())
}

async fn create_task(
    State(state): State<AppState>,
    Json(input): Json<CreateTask>,
) -> Result<(StatusCode, Json<Task>), ApiError> {
    let task = Task {
        id: Uuid::new_v4(),
        title: validate_title(&input.title)?,
        done: false,
    };
    let mut store = state.write().unwrap();
    store.order.push(task.id);
    store.tasks.insert(task.id, task.clone());
    Ok((StatusCode::CREATED, Json(task)))
}

async fn update_task(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
    Json(input): Json<UpdateTask>,
) -> Result<Json<Task>, ApiError> {
    let title = input.title.as_deref().map(validate_title).transpose()?;
    let mut store = state.write().unwrap();
    let task = store
        .tasks
        .get_mut(&id)
        .ok_or_else(|| error(StatusCode::NOT_FOUND, "task not found"))?;
    if let Some(title) = title {
        task.title = title;
    }
    if let Some(done) = input.done {
        task.done = done;
    }
    Ok(Json(task.clone()))
}

async fn delete_task(
    State(state): State<AppState>,
    Path(id): Path<Uuid>,
) -> Result<StatusCode, ApiError> {
    let mut store = state.write().unwrap();
    if store.tasks.remove(&id).is_none() {
        return Err(error(StatusCode::NOT_FOUND, "task not found"));
    }
    store.order.retain(|t| *t != id);
    Ok(StatusCode::NO_CONTENT)
}

fn app(state: AppState) -> Router {
    Router::new()
        .route("/api/health", get(health))
        .route("/api/tasks", get(list_tasks).post(create_task))
        .route("/api/tasks/{id}", axum::routing::patch(update_task).delete(delete_task))
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "tasks_api=info,tower_http=info".into()),
        )
        .init();

    let port: u16 = std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8080);
    let addr = SocketAddr::from(([0, 0, 0, 0], port));

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    tracing::info!("API listening on http://{addr}");
    axum::serve(listener, app(AppState::default())).await.unwrap();
}
