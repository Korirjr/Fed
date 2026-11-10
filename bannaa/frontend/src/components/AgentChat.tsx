"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { AgentEvent, api, streamAgent } from "@/lib/api";

type Item =
  | { kind: "user"; text: string }
  | { kind: "text"; text: string }
  | { kind: "tool"; id: string; name: string; input: Record<string, unknown>; result?: { output: string; is_error: boolean } }
  | { kind: "error"; text: string };

const TOOL_LABELS: Record<string, string> = {
  list_files: "📂 استعراض الملفات",
  read_file: "📖 قراءة",
  write_file: "✍️ كتابة",
  edit_file: "✏️ تعديل",
  delete_file: "🗑️ حذف",
  run_command: "⚡ أمر",
  start_app: "🚀 تشغيل التطبيق",
  stop_app: "⏹️ إيقاف التطبيق",
  read_app_logs: "📜 قراءة السجل",
};

const SUGGESTIONS = [
  "سوّ لي موقع شخصي بسيط بـ HTML و CSS وشغّله",
  "ابنِ API بـ Express فيه CRUD للمنتجات وشغّله",
  "سوّ لعبة XO في المتصفح",
  "سوّ تطبيق Next.js لقائمة مهام",
];

function mainArg(name: string, input: Record<string, unknown>) {
  const v = input.command ?? input.path ?? "";
  return typeof v === "string" ? v : JSON.stringify(v);
}

function apply(items: Item[], e: AgentEvent): Item[] {
  switch (e.type) {
    case "user":
      return [...items, { kind: "user", text: e.text }];
    case "text":
      return [...items, { kind: "text", text: e.text }];
    case "tool_use":
      return [...items, { kind: "tool", id: e.id, name: e.name, input: e.input }];
    case "tool_result":
      return items.map((it) => (it.kind === "tool" && it.id === e.id ? { ...it, result: { output: e.output, is_error: e.is_error } } : it));
    case "error":
      return [...items, { kind: "error", text: e.message }];
    default:
      return items;
  }
}

type Props = {
  projectId: string;
  agentReady: boolean;
  onFilesChanged: () => void;
  onAppChanged: () => void;
};

export default function AgentChat({ projectId, agentReady, onFilesChanged, onAppChanged }: Props) {
  const [items, setItems] = useState<Item[]>([]);
  const [input, setInput] = useState("");
  const [working, setWorking] = useState(false);
  const [busyElsewhere, setBusyElsewhere] = useState(false);
  const [stopping, setStopping] = useState(false);
  const abort = useRef<AbortController | null>(null);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api<{ busy: boolean; events: AgentEvent[] }>(`/projects/${projectId}/agent/history`)
      .then((h) => {
        setItems(h.events.reduce(apply, [] as Item[]));
        setBusyElsewhere(h.busy);
      })
      .catch(() => {});
  }, [projectId]);

  useEffect(() => {
    const el = box.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [items, working]);

  async function send(text: string) {
    const message = text.trim();
    if (!message || working) return;
    setInput("");
    setWorking(true);
    setItems((it) => [...it, { kind: "user", text: message }]);
    abort.current = new AbortController();
    try {
      await streamAgent(
        projectId,
        message,
        (e) => {
          if (e.type === "files_changed") onFilesChanged();
          else if (e.type === "app_changed") onAppChanged();
          else setItems((it) => apply(it, e));
        },
        abort.current.signal,
      );
    } catch (err) {
      if ((err as Error).name !== "AbortError") setItems((it) => [...it, { kind: "error", text: (err as Error).message }]);
    } finally {
      setWorking(false);
      setStopping(false);
      onFilesChanged();
      onAppChanged();
    }
  }

  // Asks the server to stop; the stream then ends on its own after the current step.
  async function stop() {
    setStopping(true);
    await api(`/projects/${projectId}/agent/stop`, { method: "POST" }).catch(() => abort.current?.abort());
  }

  async function clear() {
    if (!confirm("مسح المحادثة؟ الملفات ما راح تنحذف.")) return;
    await api(`/projects/${projectId}/agent/history`, { method: "DELETE" }).catch(() => {});
    setItems([]);
  }

  return (
    <div className="panel">
      <div className="panel-head">
        🤖 AI Agent <span className="spacer" />
        <button className="icon" onClick={clear} disabled={working || items.length === 0}>
          محادثة جديدة
        </button>
      </div>

      <div className="chat" ref={box}>
        {items.length === 0 && !working && (
          <div className="chat-empty">
            <div className="big">🏗️</div>
            وش تبي نبني اليوم؟
            <br />
            اوصف المشروع، وأنا أكتب الكود وأشغّله.
          </div>
        )}
        {items.map((it, i) => {
          if (it.kind === "user") return <div key={i} className="msg user" dir="auto">{it.text}</div>;
          if (it.kind === "error") return <div key={i} className="msg error" dir="auto">⚠️ {it.text}</div>;
          if (it.kind === "text")
            return (
              <div key={i} className="msg assistant" dir="auto">
                <ReactMarkdown>{it.text}</ReactMarkdown>
              </div>
            );
          const details = it.name === "write_file" ? String(it.input.content ?? "") : it.result?.output;
          return (
            <details key={i} className="tool">
              <summary>
                <span className="label">{TOOL_LABELS[it.name] ?? it.name}</span>
                <span className="arg">{mainArg(it.name, it.input)}</span>
                {!it.result ? <span className="spinner" /> : <span className={`status ${it.result.is_error ? "err" : "ok"}`}>{it.result.is_error ? "✗" : "✓"}</span>}
              </summary>
              {details ? <pre>{details}</pre> : null}
              {it.name === "write_file" && it.result ? <pre>{it.result.output}</pre> : null}
            </details>
          );
        })}
        {working && (
          <div className="thinking">
            <span className="spinner" /> يشتغل…
          </div>
        )}
        {busyElsewhere && !working && <div className="muted">الـ Agent يشتغل على هالمشروع في نافذة ثانية. حدّث الصفحة بعد شوي.</div>}
      </div>

      <div className="composer">
        {items.length === 0 && (
          <div className="suggestions">
            {SUGGESTIONS.map((s) => (
              <button key={s} className="secondary" onClick={() => send(s)} disabled={!agentReady || working}>
                {s}
              </button>
            ))}
          </div>
        )}
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(input);
            }
          }}
          placeholder={agentReady ? "اكتب طلبك… (Enter للإرسال، Shift+Enter لسطر جديد)" : "الـ Agent يحتاج ANTHROPIC_API_KEY في backend/.env"}
          disabled={!agentReady}
        />
        <div className="row">
          <span className="muted" style={{ fontSize: 12 }}>
            الـ Agent يقدر يكتب ملفات ويشغّل أوامر داخل المشروع.
          </span>
          <span className="spacer" />
          {working ? (
            <button className="danger" onClick={stop} disabled={stopping}>
              {stopping ? "يوقف…" : "⏹ إيقاف"}
            </button>
          ) : (
            <button onClick={() => send(input)} disabled={!agentReady || !input.trim()}>
              إرسال
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
