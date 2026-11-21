import React, { useEffect, useMemo, useState } from "react";
import { useFetch } from "../lib/hooks";
import { get, post } from "../lib/api";
import { PageHeader, Button, Loading, ErrorBanner, EmptyState, StatusBadge, Input, Textarea, Chip } from "../components/ui";
import { dateTimeStr, relativeTime } from "../lib/format";

interface Agent { name: string; role: string; description: string; requires_approval: boolean }
interface Execution { id: string; agent: string; status: string; input: Record<string, any>; output: string; provider: string; model: string; tokens_in: number; tokens_out: number; duration_ms: number; error: string; created_at: string; approval_id?: string | null }
interface Approval { id: string; type: string; payload: Record<string, any>; status: string; reason: string; created_at: string; updated_at: string }

export default function AIAgents() {
  const { data: agentsData } = useFetch<{ items: Agent[] }>("/api/ai/agents");
  const { data: execData, reload: reloadExecs } = useFetch<{ items: Execution[] }>("/api/ai/executions");
  const { data: approvalsData, reload: reloadApprovals } = useFetch<{ items: Approval[] }>("/api/ai/approvals");

  const [question, setQuestion] = useState("");
  const [askResult, setAskResult] = useState<Execution | null>(null);
  const [asking, setAsking] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [tab, setTab] = useState<"ask" | "agents" | "approvals" | "history">("ask");

  const ask = async () => {
    if (!question.trim()) return;
    setErr(null);
    setAsking(true);
    setAskResult(null);
    try {
      const res = await post<Execution>("/api/ai/ask", { question });
      setAskResult(res);
      reloadExecs();
    } catch (e: any) {
      setErr(e?.message || "AI request failed");
    } finally { setAsking(false); }
  };

  const resolve = async (id: string, decision: "approved" | "rejected", reason = "") => {
    setErr(null);
    try {
      await post(`/api/ai/approvals/${id}/resolve`, { decision, reason });
      reloadApprovals();
      reloadExecs();
    } catch (e: any) { setErr(e?.message || "Could not resolve approval"); }
  };

  const runAgent = async (name: string) => {
    setErr(null);
    try {
      await post(`/api/ai/agents/${name}/run`, { input: { question: question || `Produce the ${name} brief` }, question: question || name });
      reloadExecs();
      reloadApprovals();
    } catch (e: any) { setErr(e?.message || "Failed"); }
  };

  return (
    <>
      <PageHeader title="AI Agents" subtitle="Specialized agents coordinate through a shared executor — the executive assistant is the primary interface">
        <Chip>approval-gated</Chip>
      </PageHeader>
      {err ? <ErrorBanner message={err} onDismiss={() => setErr(null)} /> : null}

      <div className="tabs">
        {(["ask", "agents", "approvals", "history"] as const).map((t) => (
          <button key={t} className={`tab-btn ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t === "approvals" ? `Approvals${approvalsData?.items?.filter((a: Approval) => a.status === "pending").length ? ` (${approvalsData.items.filter((a: Approval) => a.status === "pending").length})` : ""}` : t[0].toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {tab === "ask" ? (
        <>
          <div className="card card-pad" style={{ marginBottom: 18 }}>
            <h3 style={{ fontSize: 16, marginBottom: 10 }}>Ask the executive assistant</h3>
            <div className="flex" style={{ gap: 10 }}>
              <Input value={question} onChange={setQuestion} placeholder='e.g. "What should I focus on today?"' onKeyDown={(e) => { if (e.key === "Enter") ask(); }} />
              <Button loading={asking} onClick={ask}>Ask</Button>
            </div>
            <p className="subtle" style={{ marginTop: 10, marginBottom: 0 }}>The assistant retrieves the full business context before answering. Unconfigured AI shows a clear error — it never fabricates.</p>
          </div>

          {asking ? <Loading /> : null}
          {askResult ? (
            <div className="card card-pad">
              <div className="between" style={{ marginBottom: 12 }}>
                <h3 style={{ fontSize: 15 }}>Response</h3>
                <div className="flex" style={{ gap: 8 }}>
                  <StatusBadge status={askResult.status} />
                  <span className="text-xs">{askResult.tokens_in} in · {askResult.tokens_out} out · {Math.round(askResult.duration_ms / 1000)}s</span>
                </div>
              </div>
              {askResult.status === "success" ? (
                <div className="resp-block">{askResult.output}</div>
              ) : (
                <div className="error-banner"><span>⚠</span><span>{askResult.error || "Execution failed"}</span></div>
              )}
            </div>
          ) : null}
        </>
      ) : null}

      {tab === "agents" ? (
        <div className="grid-3">
          {(agentsData?.items || []).map((a) => (
            <div key={a.name} className="card agent-card">
              <h3>{a.role}</h3>
              <div className="desc">{a.description}</div>
              <div className="foot">
                <div className="text-xs">{a.requires_approval ? "requires human approval" : "auto-executes"}</div>
                <Button size="sm" onClick={() => runAgent(a.name)}>Run</Button>
              </div>
            </div>
          ))}
          {!agentsData?.items?.length ? <Loading /> : null}
        </div>
      ) : null}

      {tab === "approvals" ? (
        (approvalsData?.items || []).length === 0 ? (
          <div className="card card-pad"><EmptyState icon="❖" title="No approvals waiting" detail="Consequential AI actions (content drafts, publishes, deletes) appear here for human review." /></div>
        ) : (
          <div className="grid-2">
            {(approvalsData?.items || []).map((a) => (
              <div key={a.id} className="card card-pad">
                <div className="between" style={{ marginBottom: 8 }}>
                  <StatusBadge status={a.status} />
                  <span className="text-xs">{dateTimeStr(a.created_at)}</span>
                </div>
                <h3 style={{ fontSize: 14 }}>{a.payload?.title || a.type}</h3>
                <div className="text-xs" style={{ color: "var(--text-3)", marginBottom: 10 }}>{a.type} · {a.reason ? `reason: ${a.reason}` : "no reason"}</div>
                {a.status === "pending" ? (
                  <div className="flex" style={{ gap: 8 }}>
                    <Button size="sm" onClick={() => resolve(a.id, "approved")}>Approve</Button>
                    <Button size="sm" variant="danger" onClick={() => resolve(a.id, "rejected", "rejected by user")}>Reject</Button>
                  </div>
                ) : <div className="text-xs">Resolved {relativeTime(a.updated_at)}</div>}
              </div>
            ))}
          </div>
        )
      ) : null}

      {tab === "history" ? (
        (execData?.items || []).length === 0 ? (
          <div className="card card-pad"><EmptyState icon="❖" title="No executions yet" detail="Run an agent or ask the assistant and executions appear here." /></div>
        ) : (
          <div className="table-wrap">
            <table className="data">
              <thead><tr><th>When</th><th>Agent</th><th>Status</th><th>Tokens</th><th>Duration</th></tr></thead>
              <tbody>
                {(execData?.items || []).map((e) => (
                  <tr key={e.id}>
                    <td className="text-xs">{relativeTime(e.created_at)}</td>
                    <td><span className="text-sm" style={{ fontWeight: 650 }}>{e.agent}</span></td>
                    <td><StatusBadge status={e.status} /></td>
                    <td className="text-xs">{e.tokens_in} in · {e.tokens_out} out</td>
                    <td className="text-xs">{(e.duration_ms / 1000).toFixed(1)}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : null}
    </>
  );
}
