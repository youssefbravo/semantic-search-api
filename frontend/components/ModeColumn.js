"use client";

export default function ModeColumn({ mode, data, loading, accent }) {
  return (
    <div className="flex min-h-[16rem] flex-col rounded-2xl border border-slate-800 bg-slate-900/40">
      <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
        <div>
          <div className={`text-sm font-semibold ${accent}`}>{mode.label}</div>
          <div className="text-xs text-slate-500">{mode.blurb}</div>
        </div>
        {data && (
          <div className="text-right text-[11px] text-slate-400">
            <div>{data.latency_ms} ms</div>
            <div>{data.cached ? "cached" : `${data.count} hits`}</div>
          </div>
        )}
      </div>

      <div className="scroll-thin flex-1 space-y-3 overflow-y-auto p-3">
        {loading && (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-20 animate-pulse rounded-xl bg-slate-800/60" />
            ))}
          </div>
        )}

        {!loading && data?.results?.length === 0 && (
          <div className="px-1 py-6 text-center text-sm text-slate-500">No matches.</div>
        )}

        {!loading &&
          data?.results?.map((hit) => (
            <div
              key={hit.chunk_id}
              className="animate-fade-in rounded-xl border border-slate-800 bg-slate-950/60 p-3"
            >
              <div className="mb-1.5 flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-md bg-slate-800 text-[11px] font-bold text-slate-300">
                  {hit.rank}
                </span>
                <span className="text-[11px] text-slate-500">
                  score {hit.score.toFixed(3)}
                </span>
              </div>
              <p className="line-clamp-4 text-[13px] leading-relaxed text-slate-300">
                {hit.content}
              </p>
            </div>
          ))}
      </div>
    </div>
  );
}
