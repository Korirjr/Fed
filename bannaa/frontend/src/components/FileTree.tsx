"use client";

import { useMemo, useState } from "react";
import { FileEntry } from "@/lib/api";

type Props = {
  files: FileEntry[];
  active: string | null;
  onOpen: (path: string) => void;
  onDelete: (path: string) => void;
};

function icon(path: string) {
  const ext = path.split(".").pop()?.toLowerCase();
  if (["ts", "tsx", "js", "jsx", "mjs"].includes(ext ?? "")) return "🟨";
  if (["rs"].includes(ext ?? "")) return "🦀";
  if (["py"].includes(ext ?? "")) return "🐍";
  if (["html"].includes(ext ?? "")) return "🌐";
  if (["css", "scss"].includes(ext ?? "")) return "🎨";
  if (["json", "toml", "yaml", "yml"].includes(ext ?? "")) return "⚙️";
  if (["md"].includes(ext ?? "")) return "📝";
  if (["png", "jpg", "jpeg", "svg", "gif", "ico", "webp"].includes(ext ?? "")) return "🖼️";
  return "📄";
}

export default function FileTree({ files, active, onOpen, onDelete }: Props) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());

  const visible = useMemo(
    () =>
      files.filter((f) => {
        const parts = f.path.split("/");
        for (let i = 1; i < parts.length; i++) {
          if (collapsed.has(parts.slice(0, i).join("/"))) return false;
        }
        return true;
      }),
    [files, collapsed],
  );

  if (files.length === 0) {
    return <div className="tree-empty">المشروع فاضي. اطلب من الـ Agent يبني لك شي ✨</div>;
  }

  return (
    <div className="tree">
      {visible.map((f) => {
        const depth = f.path.split("/").length - 1;
        const name = f.path.split("/").pop();
        const isCollapsed = collapsed.has(f.path);
        return (
          <div
            key={f.path}
            className={`tree-item ${active === f.path ? "active" : ""}`}
            style={{ paddingLeft: 10 + depth * 14 }}
            onClick={() => {
              if (f.is_dir) {
                setCollapsed((s) => {
                  const n = new Set(s);
                  if (n.has(f.path)) n.delete(f.path);
                  else n.add(f.path);
                  return n;
                });
              } else onOpen(f.path);
            }}
            title={f.path}
          >
            <span>{f.is_dir ? (isCollapsed ? "📁" : "📂") : icon(f.path)}</span>
            <span>{name}</span>
            <span
              className="del"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(f.path);
              }}
            >
              ✕
            </span>
          </div>
        );
      })}
    </div>
  );
}
