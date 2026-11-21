import React, { useState } from "react";
import { useFetch } from "../lib/hooks";
import { post } from "../lib/api";
import { PageHeader, Button, Loading, ErrorBanner, EmptyState, StatusBadge } from "../components/ui";
import { dateTimeStr } from "../lib/format";

interface Workflow { id: string; name: string; description: string; schedule: string; status: string }
interface Execution { id: string; workflow_id: string; status: string; payload: Record<string, any>; error: string; created_at: string; started_at: string | null; finished_at: string | null }

export default function Automations() {
  const { data: wfData, loading, error, reload } = useFetch<{ items: Workflow[] }>("/api/automation/workflows");
  const { data: execData, reload: reloadExecs } = useFetch<{ items: Execution[] }>("/api/automation/executions");
  const [err, setErr] = useState<string | null>(null);
  const [triggering, setTriggering] = useState<string | null>(null);

  const trigger = async (name: string) => {
    setErr(null);
    setTriggering(name);
    try {
      await post(`/api/automation/workflows/${name}/trigger`, { payload: {} });
      reloadExecs();
    } catch (e: any) { setErr(e?.message || "Trigger failed"); }
    finally { setTriggering(null); }
  };

  return (
    <>
      <PageHeader title="Automations" subtitle="n8n workflows — triggers and execution history. Scheduled runs happen in n8n, not in this app." />
      {err ? <ErrorBanner message={err} onDismiss={() => setErr(null)} /> : null}

      <div className="info-banner" style={{ marginBottom: 18 }}>
        n8n is the external automation engine. Set <code className="mono">N8N_ENABLED=true</code>, <code className="mono">N8N_WEBHOOK_BASE_URL</code> and <code className="mono">N8N_API_KEY</code> in <code className="mono">.env</code> to enable live triggers. Without it, triggers are recorded and marked failed — never faked as successful. See <code className="mono">workflows/n8n/</code> for templates.
      </div>

      <div className="section-title">Workflow templates</div>
      {loading ? <Loading /> : (
        <>
          {(wfData?.items || []).map((w) => (
            <div key={w.id || w.name} className="card card-pad" style={{ marginBottom: 12 }}>
              <div className="between">
                <div>
                  <div className="flex" style={{ gap: 10, alignItems: "center" }}>
                    <h3 style={{ fontSize: 15 }}>{w.name}</h3>
                    <StatusBadge status={w.status} />
                  </div>
                  <p className="subtle" style={{ margin: "6px 0 0" }}>{w.description}</p>
                  <div className="text-xs" style={{ marginTop: 6 }}>schedule: <code className="mono">{w.schedule || "—"}</code></div>
                </div>
                <Button size="sm" loading={triggering === w.name} onClick={() => trigger(w.name)}>Trigger</Button>
              </div>
            </div>
          ))}
        </>
      )}

      <div className="section-title">Execution history</div>
      {(execData?.items || []).length === 0 ? (
        <div className="card card-pad"><EmptyState icon="⚙" title="No executions yet" detail="Trigger a workflow to see its execution recorded." /></div>
      ) : (
        <div className="table-wrap">
          <table className="data">
            <thead><tr><th>When</th><th>Workflow</th><th>Status</th><th>Error</th></tr></thead>
            <tbody>
              {(execData?.items || []).map((e) => (
                <tr key={e.id}>
                  <td className="text-xs">{dateTimeStr(e.created_at)}</td>
                  <td><span className="text-sm">{e.workflow_id?.slice(0, 8)}…</span></td>
                  <td><StatusBadge status={e.status} /></td>
                  <td className="text-xs" style={{ maxWidth: 340, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{e.error || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
