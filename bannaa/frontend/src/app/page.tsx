"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api, Health, Project } from "@/lib/api";

export default function Home() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Project[]>("/projects").then(setProjects).catch((e) => setError(e.message));
    api<Health>("/health").then(setHealth).catch(() => {});
  }, []);

  async function create(e: FormEvent) {
    e.preventDefault();
    try {
      const p = await api<Project>("/projects", { method: "POST", body: JSON.stringify({ name }) });
      window.location.href = `/p/${p.id}`;
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function remove(p: Project) {
    if (!confirm(`حذف المشروع "${p.name}" وكل ملفاته؟`)) return;
    await api(`/projects/${p.id}`, { method: "DELETE" });
    setProjects((ps) => ps?.filter((x) => x.id !== p.id) ?? null);
  }

  return (
    <main className="home">
      <div className="hero">
        <h1>
          بنّاء <span>AI</span>
        </h1>
        <p>اوصف المشروع اللي تبيه، والـ Agent يكتب الكود ويثبّت المكتبات ويشغّله قدامك.</p>
      </div>

      {health && !health.agent_ready && (
        <div className="banner">
          ⚠️ الـ Agent مو جاهز: لازم تحط مفتاح Claude API في <code>backend/.env</code> بهذا الشكل{" "}
          <code>ANTHROPIC_API_KEY=...</code> وبعدها تعيد تشغيل الـ backend. المحرر والتشغيل يشتغلون بدونه.
        </div>
      )}
      {error && <div className="banner">{error === "HTTP 500" ? "ما قدرت أتصل بالـ backend. تأكد إنه شغّال." : error}</div>}

      <form className="create" onSubmit={create}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="اسم المشروع الجديد، مثلاً: متجر ورد" maxLength={80} />
        <button type="submit" disabled={!name.trim()}>
          + مشروع جديد
        </button>
      </form>

      {projects === null ? (
        <p className="muted">جاري التحميل…</p>
      ) : projects.length === 0 ? (
        <p className="muted">ما عندك مشاريع للحين. أنشئ أول مشروع 👆</p>
      ) : (
        <div className="projects">
          {projects.map((p) => (
            <Link key={p.id} href={`/p/${p.id}`} className="project-card">
              <h3>{p.name}</h3>
              <div className="muted">{new Date(p.created_at * 1000).toLocaleDateString("ar")}</div>
              <div className="row">
                <span className="muted mono">:{p.port}</span>
                <button
                  className="danger"
                  onClick={(e) => {
                    e.preventDefault();
                    remove(p);
                  }}
                >
                  حذف
                </button>
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
