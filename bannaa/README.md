# Bannaa (بنّاء): AI development platform

A browser IDE with a real AI coding agent. You describe a project in the chat,
and the agent writes the files, installs packages, runs commands, starts the
app and checks that it works. You watch it live in the editor, console and
preview.

```
bannaa/
├── backend/    Axum (Rust): projects, files, process runner, agent loop  → :8080
└── frontend/   Next.js: home page + IDE (chat, editor, preview, console)  → :3000
```

## Features

- **Projects**: create, open and delete; each has its own workspace folder and a reserved preview port (4100+).
- **AI agent** (Claude, via the Messages API): a tool-use loop with these tools:
  `list_files`, `read_file`, `write_file`, `edit_file`, `delete_file`,
  `run_command` (with timeout), `start_app`, `stop_app`, `read_app_logs`.
  Progress streams to the chat as it happens, the conversation is saved per project,
  and the agent can be stopped mid-run.
- **Editor**: file tree and a CodeMirror editor with syntax highlighting (JS/TS, HTML, CSS, Python, Rust, JSON, Markdown). Ctrl+S saves.
- **Run and preview**: start/stop the project's app; its live output streams to the console, and the preview shows it in an iframe.
- **Console**: run one-off commands (`npm install ...`) in the project.

## Run

Requires Rust (stable), Node.js 20+, and an Anthropic API key for the agent.

```bash
# 1) Backend
cd backend
cp .env.example .env          # then put your key in ANTHROPIC_API_KEY
cargo run --release           # http://localhost:8080

# 2) Frontend (second terminal)
cd frontend
npm install
npm run dev                   # http://localhost:3000
```

Without a key, everything except the agent still works (editor, run, preview, console).

| Variable | Default | Meaning |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | (none) | Required for the agent |
| `BANNAA_MODEL` | `claude-opus-5-5` | Model the agent uses |
| `BANNAA_EFFORT` | `high` | `low` / `medium` / `high` / `xhigh` / `max` |
| `BANNAA_DATA_DIR` | `data` | Where projects and chats are stored |
| `PORT` | `8080` | Backend port |
| `API_URL` (frontend) | `http://localhost:8080` | Where Next.js forwards `/api/*` |

The agent calls the API with adaptive thinking, prompt caching, and server-side
fallback (`fallbacks: "default"`): if the model declines a request, the API
retries it on the recommended fallback model.

## How it works

1. The chat sends `POST /api/projects/{id}/agent`; the backend replies with a Server-Sent Events stream.
2. The agent loop (`backend/src/agent.rs`) calls Claude with the project's tools, runs each tool call
   against the workspace, sends the results back, and repeats until Claude finishes (max 60 steps).
3. Each step is streamed to the UI (`text`, `tool_use`, `tool_result`, `files_changed`, `app_changed`, `done`).
4. Apps get `PORT` and `HOST=0.0.0.0` in their environment, and the preview loads `http://<host>:<port>`.

## Security: read this before exposing it

The agent and the console **run real shell commands on the server** with the
backend's permissions. File paths are restricted to the project folder, but
commands are not sandboxed. Run it on your own machine or inside a disposable
container/VM, and do not expose it to the internet without adding
authentication and per-project isolation (e.g. one Docker container per project).

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Status, whether the agent has a key, model |
| GET / POST | `/api/projects` | List / create (`{"name"}`) |
| GET / DELETE | `/api/projects/{id}` | Get / delete |
| GET | `/api/projects/{id}/files` | File tree |
| GET / PUT / DELETE | `/api/projects/{id}/file?path=` | Read / write (`{"content"}`) / delete |
| POST | `/api/projects/{id}/exec` | Run a command (`{"command"}`), wait for output |
| GET | `/api/projects/{id}/run` | App status |
| POST | `/api/projects/{id}/run/start` · `/run/stop` | Start (`{"command"}`) / stop the app |
| GET | `/api/projects/{id}/run/logs` | App output (SSE) |
| POST | `/api/projects/{id}/agent` | Send a message to the agent (SSE stream) |
| POST | `/api/projects/{id}/agent/stop` | Stop the running agent |
| GET / DELETE | `/api/projects/{id}/agent/history` | Chat history / clear |
