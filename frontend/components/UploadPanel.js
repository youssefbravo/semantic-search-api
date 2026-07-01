"use client";

import { useRef, useState } from "react";
import { getDocument, uploadDocument } from "../lib/api";

const STATE_STYLES = {
  uploading: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  pending: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  processing: "bg-sky-500/15 text-sky-300 border-sky-500/30",
  done: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  failed: "bg-rose-500/15 text-rose-300 border-rose-500/30",
  error: "bg-rose-500/15 text-rose-300 border-rose-500/30",
};

export default function UploadPanel() {
  const [doc, setDoc] = useState(null); // {filename, state, chunks}
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef(null);

  async function handleFile(file) {
    if (!file) return;
    setDoc({ filename: file.name, state: "uploading", chunks: 0 });
    try {
      const created = await uploadDocument(file);
      setDoc({ filename: file.name, state: created.status, chunks: 0 });
      // Poll ingestion status until the worker finishes.
      for (let i = 0; i < 60; i++) {
        const d = await getDocument(created.id);
        setDoc({ filename: file.name, state: d.status, chunks: d.num_chunks });
        if (d.status === "done" || d.status === "failed") break;
        await new Promise((r) => setTimeout(r, 1000));
      }
    } catch (e) {
      setDoc({ filename: file.name, state: "error", chunks: 0 });
    }
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        handleFile(e.dataTransfer.files?.[0]);
      }}
      onClick={() => inputRef.current?.click()}
      className={`cursor-pointer rounded-2xl border-2 border-dashed p-6 text-center transition ${
        dragOver
          ? "border-indigo-400 bg-indigo-500/10"
          : "border-slate-700 bg-slate-900/50 hover:border-slate-600"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt,.md,text/plain,application/pdf"
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      <div className="text-sm text-slate-300">
        <span className="font-medium text-indigo-300">Drop a PDF or text file</span>{" "}
        here, or click to choose
      </div>
      <div className="mt-1 text-xs text-slate-500">
        It’s chunked, embedded, and indexed in the background.
      </div>

      {doc && (
        <div className="mt-4 flex items-center justify-center gap-3 text-sm">
          <span className="truncate max-w-[14rem] text-slate-300">{doc.filename}</span>
          <span
            className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${
              STATE_STYLES[doc.state] || "border-slate-600 text-slate-300"
            }`}
          >
            {doc.state}
            {doc.state === "done" ? ` · ${doc.chunks} chunks` : ""}
          </span>
        </div>
      )}
    </div>
  );
}
