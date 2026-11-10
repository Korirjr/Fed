"use client";

import CodeMirror from "@uiw/react-codemirror";
import { vscodeDark } from "@uiw/codemirror-theme-vscode";
import { javascript } from "@codemirror/lang-javascript";
import { html } from "@codemirror/lang-html";
import { css } from "@codemirror/lang-css";
import { python } from "@codemirror/lang-python";
import { rust } from "@codemirror/lang-rust";
import { json } from "@codemirror/lang-json";
import { markdown } from "@codemirror/lang-markdown";
import { useMemo } from "react";

function languageFor(path: string) {
  const ext = path.split(".").pop()?.toLowerCase() ?? "";
  switch (ext) {
    case "js":
    case "mjs":
    case "cjs":
    case "jsx":
      return [javascript({ jsx: true })];
    case "ts":
    case "tsx":
      return [javascript({ jsx: true, typescript: true })];
    case "html":
    case "htm":
      return [html()];
    case "css":
    case "scss":
      return [css()];
    case "py":
      return [python()];
    case "rs":
      return [rust()];
    case "json":
      return [json()];
    case "md":
      return [markdown()];
    default:
      return [];
  }
}

export default function CodeEditor({ path, value, onChange }: { path: string; value: string; onChange: (v: string) => void }) {
  const extensions = useMemo(() => languageFor(path), [path]);
  return (
    <CodeMirror
      value={value}
      height="100%"
      theme={vscodeDark}
      extensions={extensions}
      onChange={onChange}
      basicSetup={{ tabSize: 2 }}
    />
  );
}
