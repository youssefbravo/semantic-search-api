"use client";

import { useState } from "react";
import ModeColumn from "../components/ModeColumn";
import UploadPanel from "../components/UploadPanel";
import { search } from "../lib/api";

const MODES = [
  { key: "keyword", label: "Keyword (BM25)", blurb: "Exact word matching", accent: "text-amber-300" },
  { key: "semantic", label: "Semantic", blurb: "By meaning", accent: "text-sky-300" },
  { key: "hybrid", label: "Hybrid (RRF)", blurb: "Best of both", accent: "text-indigo-300" },
];

const EXAMPLES = [
  "which animal looks like it is smiling in photos",
  "how do I stop one user from spamming my server",
  "what makes containers lighter than virtual machines",
  "why does measuring the angle between vectors ignore length",
];

export default function Home() {
  const [query, setQuery] = useState("");
  const [k, setK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null); // { [mode]: response }
  const [error, setError] = useState(null);

  async function runSearch(q) {
    const text = (q ?? query).trim();
    if (!text) return;
    setQuery(text);
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      // Fire all three modes in parallel against the same query.
      const entries = await Promise.all(
        MODES.map(async (m) => [m.key, await search(text, m.key, k)])
      );
      setResults(Object.fromEntries(entries));
    } catch (e) {
      setError(e.message || "Search failed. Is the API running on :8000?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      {/* Header */}
      <header className="mb-8">
        <h1 className="bg-gradient-to-r from-indigo-300 via-sky-300 to-emerald-300 bg-clip-text text-3xl font-bold text-transparent">
          Document Semantic Search
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-400">
          Upload documents, then ask a question in plain English. The same query runs
          through <span className="text-amber-300">keyword</span>,{" "}
          <span className="text-sky-300">semantic</span>, and{" "}
          <span className="text-indigo-300">hybrid</span> retrieval at once — so you can
          see exactly how they differ.
        </p>
      </header>

      {/* Upload */}
      <section className="mb-8">
        <UploadPanel />
      </section>

      {/* Search bar */}
      <section className="mb-6">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            runSearch();
          }}
          className="flex flex-col gap-3 sm:flex-row"
        >
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask anything about your documents…"
            className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-indigo-500"
          />
          <select
            value={k}
            onChange={(e) => setK(Number(e.target.value))}
            className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-3 text-sm text-slate-200 outline-none focus:border-indigo-500"
            title="Number of results per mode"
          >
            {[3, 5, 10].map((n) => (
              <option key={n} value={n}>
                top {n}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={loading}
            className="rounded-xl bg-indigo-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50"
          >
            {loading ? "Searching…" : "Search"}
          </button>
        </form>

        {/* Example chips */}
        <div className="mt-3 flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => runSearch(ex)}
              className="rounded-full border border-slate-700 bg-slate-900/60 px-3 py-1 text-xs text-slate-400 transition hover:border-indigo-500 hover:text-slate-200"
            >
              {ex}
            </button>
          ))}
        </div>

        {error && (
          <p className="mt-3 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
            {error}
          </p>
        )}
      </section>

      {/* Comparison grid */}
      <section className="grid gap-4 md:grid-cols-3">
        {MODES.map((m) => (
          <ModeColumn
            key={m.key}
            mode={m}
            accent={m.accent}
            loading={loading}
            data={results?.[m.key]}
          />
        ))}
      </section>

      {!results && !loading && (
        <p className="mt-10 text-center text-sm text-slate-600">
          Try an example above, or upload your own document and search it.
        </p>
      )}

      <footer className="mt-12 border-t border-slate-800 pt-4 text-center text-xs text-slate-600">
        FastAPI · PostgreSQL (pgvector + BM25) · Redis · Celery · sentence-transformers
      </footer>
    </main>
  );
}
