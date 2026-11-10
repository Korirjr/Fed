"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { use, useCallback, useEffect, useRef, useState } from "react";
import AgentChat from "@/components/AgentChat";
import Console from "@/components/Console";
import FileTree from "@/components/FileTree";
import Preview from "@/components/Preview";
import { api, enc, FileEntry, Health, Project, RunStatus } from "@/lib/api";

const CodeEditor = dynamic(() => import("@/components/CodeEditor"), { ssr: false });

type OpenFile = { path: string; content: string; saved: string };

export default function IDE({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [project, setProject] = useState<Project | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [open, setOpen] = useState<OpenFile | null>(null);
  const [tab, setTab] = useState<"editor" | "preview">("editor");
  const [status, setStatus] = useState<RunStatus | null>(null);
  const [runCmd, setRunCmd] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [notFound, setNotFound] = useState(false);
  const openRef = useRef(open);
  openRef.current = open;

  const refreshFiles = useCallback(async () => {
    const list = await api<FileEntry[]>(`/projects/${id}/files`).catch(() => null);
    if (list) setFiles(list);
    // Reload the open file if it changed on disk and has no unsaved edits.
    const cur = openRef.current;
    if (cur && cur.content === cur.saved) {
      const f = await api<{ content: string }>(`/projects/${id}/file?path=${enc(cur.path)}`).catch(() => null);
      if (f && f.content !== cur.saved) setOpen({ path: cur.path, content: f.content, saved: f.content });
    }
  }, [id]);

  const refreshStatus = useCallback(async () => {
    const s = await api<RunStatus>(`/projects/${id}/run`).catch(() => null);
    if (!s) return;
    setStatus((prev) => {
      if (s.running && !prev?.running) {
        setTab("preview");
        setReloadKey((k) => k + 1);
      }
      return s;
    });
    if (s.command) setRunCmd((c) => c || s.command!);
  }, [id]);

  useEffect(() => {
    api<Project>(`/projects/${id}`).then(setProject).catch(() => setNotFound(true));
    api<Health>("/health").then(setHealth).catch(() => {});
    refreshFiles();
    refreshStatus();
    const t = setInterval(refreshStatus, 3000);
    return () => clearInterval(t);
  }, [id, refreshFiles, refreshStatus]);

  // Guess a run command from the files when none was set yet.
  useEffect(() => {
    if (runCmd) return;
    const has = (p: string) => files.some((f) => f.path === p);
    if (has("package.json")) setRunCmd("npm install && npm run dev");
    else if (has("Cargo.toml")) setRunCmd("cargo run");
    else if (has("main.py")) setRunCmd("python3 main.py");
    else if (has("app.py")) setRunCmd("python3 app.py");
    else if (has("index.html")) setRunCmd("python3 -m http.server $PORT");
  }, [files, runCmd]);

  async function openFile(path: string) {
    if (open && open.content !== open.saved && !confirm("فيه تعديلات ما انحفظت. تتجاهلها؟")) return;
    try {
      const f = await api<{ content: string }>(`/projects/${id}/file?path=${enc(path)}`);
      setOpen({ path, content: f.content, saved: f.content });
      setTab("editor");
    } catch (e) {
      alert((e as Error).message);
    }
  }

  const save = useCallback(async () => {
    const cur = openRef.current;
    if (!cur || cur.content === cur.saved) return;
    await api(`/projects/${id}/file?path=${enc(cur.path)}`, { method: "PUT", body: JSON.stringify({ content: cur.content }) });
    setOpen((o) => (o && o.path === cur.path ? { ...o, saved: cur.content } : o));
    setReloadKey((k) => k + 1);
  }, [id]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "s") {
        e.preventDefault();
        save();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [save]);

  async function deleteFile(path: string) {
    if (!confirm(`حذف ${path}؟`)) return;
    await api(`/projects/${id}/file?path=${enc(path)}`, { method: "DELETE" }).catch((e) => alert(e.message));
    if (open?.path === path || open?.path.startsWith(path + "/")) setOpen(null);
    refreshFiles();
  }

  async function newFile() {
    const path = prompt("اسم الملف (مثلاً src/index.js):");
    if (!path) return;
    await api(`/projects/${id}/file?path=${enc(path)}`, { method: "PUT", body: JSON.stringify({ content: "" }) }).catch((e) => alert(e.message));
    await refreshFiles();
    openFile(path);
  }

  async function start() {
    if (!runCmd.trim()) return;
    const s = await api<RunStatus>(`/projects/${id}/run/start`, { method: "POST", body: JSON.stringify({ command: runCmd }) }).catch((e) => {
      alert(e.message);
      return null;
    });
    if (s) {
      setStatus(s);
      setTab("preview");
      // Give the server a moment to bind its port before loading the preview.
      setTimeout(() => setReloadKey((k) => k + 1), 2500);
    }
  }

  async function stop() {
    const s = await api<RunStatus>(`/projects/${id}/run/stop`, { method: "POST" }).catch(() => null);
    if (s) setStatus(s);
  }

  if (notFound) {
    return (
      <main className="home">
        <h2>المشروع غير موجود</h2>
        <Link href="/">← رجوع للمشاريع</Link>
      </main>
    );
  }

  const dirty = open && open.content !== open.saved;

  return (
    <div className="ide">
      <header className="topbar">
        <Link href="/" className="brand">
          بنّاء
        </Link>
        <span className="muted">/</span>
        <span className="name">{project?.name ?? "…"}</span>
        <span className="spacer" />
        <span className={`dot ${status?.running ? "on" : ""}`} title={status?.running ? "شغّال" : "متوقف"} />
        <input className="run-cmd mono" value={runCmd} onChange={(e) => setRunCmd(e.target.value)} placeholder="أمر التشغيل" />
        {status?.running ? (
          <>
            <button className="secondary" onClick={start}>
              ⟳ إعادة
            </button>
            <button className="danger" onClick={stop}>
              ⏹ إيقاف
            </button>
          </>
        ) : (
          <button onClick={start} disabled={!runCmd.trim()}>
            ▶ تشغيل
          </button>
        )}
      </header>

      <div className="workspace">
        <AgentChat
          projectId={id}
          agentReady={!!health?.agent_ready}
          onFilesChanged={refreshFiles}
          onAppChanged={() => {
            refreshStatus();
            setReloadKey((k) => k + 1);
          }}
        />

        <section className="center">
          <div className="tabs">
            <button className={tab === "editor" ? "active" : ""} onClick={() => setTab("editor")}>
              {open ? <span className="file-tab">{open.path.split("/").pop()}{dirty ? " ●" : ""}</span> : "المحرر"}
            </button>
            <button className={tab === "preview" ? "active" : ""} onClick={() => setTab("preview")}>
              المعاينة {status?.running ? "🟢" : ""}
            </button>
            <span style={{ flex: 1 }} />
            {tab === "editor" && open && (
              <span className={`save-hint ${dirty ? "dirty" : ""}`} style={{ alignSelf: "center", paddingInline: 8 }}>
                {dirty ? "غير محفوظ · Ctrl+S" : "محفوظ"}
              </span>
            )}
          </div>
          <div className="main-view">
            {tab === "editor" ? (
              open ? (
                <div className="editor-wrap">
                  <CodeEditor path={open.path} value={open.content} onChange={(v) => setOpen((o) => (o ? { ...o, content: v } : o))} />
                </div>
              ) : (
                <div className="empty-state">
                  <div className="big">📝</div>
                  <div>اختر ملف من القائمة عشان تعدّله.</div>
                </div>
              )
            ) : (
              <Preview status={status} reloadKey={reloadKey} />
            )}
          </div>
          <Console projectId={id} onCommandDone={refreshFiles} />
        </section>

        <aside className="panel">
          <div className="panel-head">
            الملفات <span className="spacer" />
            <button className="icon" onClick={newFile} title="ملف جديد">
              ＋
            </button>
            <button className="icon" onClick={refreshFiles} title="تحديث">
              ⟳
            </button>
          </div>
          <FileTree files={files} active={open?.path ?? null} onOpen={openFile} onDelete={deleteFile} />
        </aside>
      </div>
    </div>
  );
}
