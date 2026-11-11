# Tasks App: Axum + Next.js

A simple task manager: a REST API in Rust (Axum) and a website in Next.js.

```
tasks-app/
├── backend/    # Axum API (Rust), listens on :8080
└── frontend/   # Next.js site, listens on :3000, proxies /api/* to the backend
```

## Run

Requires Rust (stable) and Node.js 20+.

```bash
# Terminal 1: API
cd backend
cargo run                 # http://localhost:8080  (PORT to change)

# Terminal 2: website
cd frontend
npm install
npm run dev               # http://localhost:3000
```

The site calls `/api/...` on its own origin, and Next.js forwards it to the
backend. Set `API_URL` to point elsewhere (default `http://localhost:8080`).

## API

| Method | Path              | Body                              | Response      |
| ------ | ----------------- | --------------------------------- | ------------- |
| GET    | `/api/health`     |                                   | `{"status":"ok"}` |
| GET    | `/api/tasks`      |                                   | `Task[]`      |
| POST   | `/api/tasks`      | `{"title": "..."}`                | `201 Task`    |
| PATCH  | `/api/tasks/{id}` | `{"title"?: "...", "done"?: bool}` | `Task`        |
| DELETE | `/api/tasks/{id}` |                                   | `204`         |

`Task = { id: uuid, title: string, done: bool }`. Errors return
`{"error": "..."}` with 400 (empty or >200-char title) or 404 (unknown id).

Data is kept in memory, so it resets when the backend restarts.
