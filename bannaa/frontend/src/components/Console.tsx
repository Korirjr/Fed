"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { api, CommandOutput } from "@/lib/api";

export default function Console({ projectId, onCommandDone }: { projectId: string; onCommandDone: () => void }) {
  const [lines, setLines] = useState<string[]>([]);
  const [cmd, setCmd] = useState("");
  const [busy, setBusy] = useState(false);
  const box = useRef<HTMLPreElement>(null);

  // Live app output over SSE (backlog first, then new lines).
  useEffect(() => {
    setLines([]);
    const es = new EventSource(`/api/projects/${projectId}/run/logs`);
    es.onmessage = (e) => setLines((l) => [...l.slice(-1500), e.data]);
    return () => es.close();
  }, [projectId]);

  useEffect(() => {
    const el = box.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines]);

  async function run(e: FormEvent) {
    e.preventDefault();
    const command = cmd.trim();
    if (!command) return;
    setBusy(true);
    setCmd("");
    setLines((l) => [...l, `$ ${command}`]);
    try {
      const out = await api<CommandOutput>(`/projects/${projectId}/exec`, { method: "POST", body: JSON.stringify({ command }) });
      const tail = out.timed_out ? "[timed out]" : `[exit ${out.exit_code ?? "?"}]`;
      setLines((l) => [...l, ...out.output.replace(/\n$/, "").split("\n"), tail]);
    } catch (err) {
      setLines((l) => [...l, `error: ${(err as Error).message}`]);
    } finally {
      setBusy(false);
      onCommandDone();
    }
  }

  return (
    <div className="console">
      <div className="panel-head">
        Console <span className="spacer" />
        <button className="icon" onClick={() => setLines([])}>
          مسح
        </button>
      </div>
      <pre className="logs" ref={box}>
        {lines.join("\n") || "مخرجات التطبيق والأوامر تظهر هنا."}
      </pre>
      <form onSubmit={run}>
        <input value={cmd} onChange={(e) => setCmd(e.target.value)} placeholder="$ npm install express" disabled={busy} />
        <button type="submit" className="secondary" disabled={busy || !cmd.trim()}>
          {busy ? "…" : "Run"}
        </button>
      </form>
    </div>
  );
}
