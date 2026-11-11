"use client";

import { useEffect, useRef, useState } from "react";
import { RunStatus } from "@/lib/api";

export default function Preview({ status, reloadKey }: { status: RunStatus | null; reloadKey: number }) {
  const [url, setUrl] = useState("");
  const [nonce, setNonce] = useState(0);
  const frame = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (!status) return;
    // The app listens on its own port on the same host as the platform.
    setUrl(`${window.location.protocol}//${window.location.hostname}:${status.port}/`);
  }, [status?.port]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => setNonce((n) => n + 1), [reloadKey]);

  if (!status?.running) {
    return (
      <div className="empty-state">
        <div className="big">🖥️</div>
        <div>ما فيه تطبيق شغّال.</div>
        <div>اضغط «تشغيل» فوق، أو اطلب من الـ Agent يشغّل المشروع.</div>
      </div>
    );
  }

  return (
    <div className="preview">
      <div className="preview-bar">
        <button className="secondary" onClick={() => setNonce((n) => n + 1)} title="تحديث">
          ⟳
        </button>
        <input className="mono" value={url} onChange={(e) => setUrl(e.target.value)} onKeyDown={(e) => e.key === "Enter" && setNonce((n) => n + 1)} />
        <button className="secondary" onClick={() => window.open(url, "_blank")}>
          فتح ↗
        </button>
      </div>
      {url && <iframe key={nonce} ref={frame} src={url} title="preview" />}
    </div>
  );
}
