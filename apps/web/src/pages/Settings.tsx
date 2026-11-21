import React from "react";
import { useAuth } from "../lib/auth";
import { useFetch } from "../lib/hooks";
import { PageHeader, Loading, ErrorBanner, EmptyState, StatCard, Textarea } from "../components/ui";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui";

interface Structure { folders: Array<{ name: string; count: number }>; notes_total: number }

export default function Settings() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { data, loading } = useFetch<Structure>("/api/knowledge/structure");

  return (
    <>
      <PageHeader title="Settings" subtitle="Account, knowledge vault, AI provider" />
      <div className="grid-2">
        <section className="card card-pad">
          <h3 style={{ fontSize: 15, marginBottom: 12 }}>Account</h3>
          <div className="form-grid">
            <div><div className="subtle">Name</div><div style={{ fontWeight: 650, marginTop: 4 }}>{user?.name || "—"}</div></div>
            <div><div className="subtle">Email</div><div style={{ fontWeight: 650, marginTop: 4 }}>{user?.email}</div></div>
            <div><div className="subtle">Role</div><div style={{ fontWeight: 650, marginTop: 4 }}>{user?.role}</div></div>
          </div>
          <div className="divider" />
          <Button variant="danger" onClick={() => { logout(); navigate("/login"); }}>Sign out</Button>
        </section>

        <section className="card card-pad">
          <h3 style={{ fontSize: 15, marginBottom: 12 }}>Knowledge vault</h3>
          {loading ? <Loading /> : null}
          {data ? (
            <div className="form-grid">
              <div><div className="subtle">Total notes</div><div style={{ fontWeight: 650, marginTop: 4 }}>{data.notes_total}</div></div>
              <div><div className="subtle">Folders</div><div style={{ fontWeight: 650, marginTop: 4 }}>{data.folders.length}</div></div>
              <div>
                <div className="subtle" style={{ marginBottom: 6 }}>By folder</div>
                <ul className="nowrap-list" style={{ gap: 6 }}>
                  {data.folders.slice(0, 8).map((f) => (
                    <li key={f.name} className="between">
                      <span className="text-sm">{f.name}</span>
                      <span className="text-xs">{f.count}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : <p className="subtle">Vault not loaded.</p>}
          <div className="divider" />
          <p className="subtle" style={{ margin: 0 }}>Vault path is configured via the <code className="mono">KNOWLEDGE_DIR</code> environment variable. Default: <code className="mono">knowledge/</code>.</p>
        </section>

        <section className="card card-pad">
          <h3 style={{ fontSize: 15, marginBottom: 12 }}>AI provider</h3>
          <p className="subtle" style={{ margin: 0 }}>Configure AI via <code className="mono">AI_BASE_URL</code>, <code className="mono">AI_API_KEY</code>, <code className="mono">AI_MODEL</code> in <code className="mono">.env</code>. The app ships with a clear "not configured" state — it never fabricates AI output.</p>
          <div className="divider" />
          <p className="subtle" style={{ margin: 0 }}>Environment variables are never read into the frontend bundle. The settings file (<code className="mono">.env</code>) is read server-side only.</p>
        </section>

        <section className="card card-pad">
          <h3 style={{ fontSize: 15, marginBottom: 12 }}>Architecture</h3>
          <ul style={{ paddingLeft: 18, margin: 0, color: "var(--text-2)", fontSize: 13 }}>
            <li>FastAPI + SQLite (Postgres-ready) backend</li>
            <li>React + TypeScript frontend</li>
            <li>Obsidian-compatible Markdown knowledge vault</li>
            <li>Config-driven OpenAI-compatible AI providers</li>
            <li>n8n-ready automation layer</li>
          </ul>
        </section>
      </div>
    </>
  );
}
