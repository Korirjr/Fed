"use client";

import { FormEvent, useEffect, useState } from "react";

type Task = { id: string; title: string; done: boolean };

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error ?? `HTTP ${res.status}`);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export default function Home() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Task[]>("/tasks")
      .then(setTasks)
      .catch(() => setError("ما قدرت أتصل بالـ API. تأكد إن الـ backend شغّال."))
      .finally(() => setLoading(false));
  }, []);

  async function run(action: () => Promise<void>) {
    setError(null);
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  const addTask = (e: FormEvent) => {
    e.preventDefault();
    run(async () => {
      const task = await api<Task>("/tasks", {
        method: "POST",
        body: JSON.stringify({ title }),
      });
      setTasks((t) => [...t, task]);
      setTitle("");
    });
  };

  const toggle = (task: Task) =>
    run(async () => {
      const updated = await api<Task>(`/tasks/${task.id}`, {
        method: "PATCH",
        body: JSON.stringify({ done: !task.done }),
      });
      setTasks((t) => t.map((x) => (x.id === updated.id ? updated : x)));
    });

  const remove = (task: Task) =>
    run(async () => {
      await api(`/tasks/${task.id}`, { method: "DELETE" });
      setTasks((t) => t.filter((x) => x.id !== task.id));
    });

  const doneCount = tasks.filter((t) => t.done).length;

  return (
    <main>
      <h1>مهامي</h1>
      <p className="sub">Next.js في الواجهة، وAxum (Rust) في الـ backend</p>

      <div className="card">
        <form onSubmit={addTask}>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="وش تبي تسوي؟"
            maxLength={200}
          />
          <button type="submit" disabled={!title.trim()}>
            أضف
          </button>
        </form>

        {error && <p className="error">{error}</p>}

        {loading ? (
          <p className="empty">جاري التحميل…</p>
        ) : tasks.length === 0 ? (
          <p className="empty">ما فيه مهام. أضف أول مهمة 👆</p>
        ) : (
          <>
            <ul>
              {tasks.map((task) => (
                <li key={task.id} className={task.done ? "done" : ""}>
                  <label>
                    <input type="checkbox" checked={task.done} onChange={() => toggle(task)} />
                    <span>{task.title}</span>
                  </label>
                  <button className="ghost" onClick={() => remove(task)} aria-label="حذف">
                    حذف
                  </button>
                </li>
              ))}
            </ul>
            <p className="stats">
              خلّصت {doneCount} من {tasks.length}
            </p>
          </>
        )}
      </div>
    </main>
  );
}
