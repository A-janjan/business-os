import React, { useState } from "react";
import { useFetch } from "../lib/hooks";
import { get, post } from "../lib/api";
import { PageHeader, Button, Loading, ErrorBanner, EmptyState, StatusBadge } from "../components/ui";
import { dateTimeStr } from "../lib/format";

interface Report { id: string; type: string; title: string; body: string; source: Record<string, any>; agent: string; created_at: string }

export default function Reports() {
  const { data, loading, error, reload } = useFetch<{ items: Report[] }>("/api/reports/");
  const [err, setErr] = useState<string | null>(null);
  const [generating, setGenerating] = useState<"weekly" | "brief" | null>(null);
  const [viewing, setViewing] = useState<Report | null>(null);

  const generateWeekly = async () => {
    setErr(null);
    setGenerating("weekly");
    try { await post("/api/reports/weekly-review"); } catch (e: any) { setErr(e?.message || "Failed"); }
    setGenerating(null);
    reload();
  };

  const generateBrief = async () => {
    setErr(null);
    setGenerating("brief");
    try { await post("/api/reports/daily-brief"); reload(); } catch (e: any) {
      setErr(e?.message || "Daily brief unavailable — configure AI provider");
    }
    setGenerating(null);
  };

  const items = data?.items || [];

  return (
    <>
      <PageHeader title="Reports" subtitle="Generated reviews and briefs — weekly review runs deterministically; daily brief uses the AI provider">
        <Button variant="secondary" loading={generating === "weekly"} onClick={generateWeekly}>Generate weekly review</Button>
        <Button loading={generating === "brief"} onClick={generateBrief}>Daily brief (AI)</Button>
      </PageHeader>
      {err ? <ErrorBanner message={err} onDismiss={() => setErr(null)} /> : null}

      {loading ? <Loading /> : (
        <>
          {items.length === 0 ? (
            <div className="card card-pad"><EmptyState icon="◈" title="No reports yet" detail="Generate a weekly review (deterministic, no AI needed) or a daily business brief (AI-backed)." /></div>
          ) : (
            <div className="grid-2">
              {items.map((r) => (
                <div key={r.id} className="card card-pad" style={{ cursor: "pointer" }} onClick={() => setViewing(r)}>
                  <div className="between" style={{ marginBottom: 8 }}>
                    <h3 style={{ fontSize: 15 }}>{r.title}</h3>
                    <StatusBadge status={r.type} />
                  </div>
                  <p className="subtle" style={{ margin: "0 0 10px", whiteSpace: "pre-wrap" }}>{(r.body || "").slice(0, 280)}{(r.body || "").length > 280 ? "…" : ""}</p>
                  <div className="between">
                    <span className="text-xs">{dateTimeStr(r.created_at)}</span>
                    <span className="text-xs">by {r.agent || "system"}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {viewing ? (
        <div className="modal-backdrop" onClick={() => setViewing(null)} role="dialog" aria-modal="true">
          <div className="modal" style={{ maxWidth: 820 }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div><div className="modal-title">{viewing.title}</div><div className="modal-sub">{viewing.type} · {dateTimeStr(viewing.created_at)}</div></div>
              <button className="btn btn-ghost btn-sm" onClick={() => setViewing(null)}>✕</button>
            </div>
            <div className="modal-body">
              <pre style={{ whiteSpace: "pre-wrap", fontFamily: "var(--font-mono)", fontSize: 12.5, lineHeight: 1.6, background: "var(--surface-2)", padding: 16, borderRadius: 10, border: "1px solid var(--border)", maxHeight: "60vh", overflow: "auto", margin: 0 }}>{viewing.body}</pre>
            </div>
            <div className="modal-footer"><Button variant="secondary" onClick={() => setViewing(null)}>Close</Button></div>
          </div>
        </div>
      ) : null}
    </>
  );
}
