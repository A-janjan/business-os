import React, { useState } from "react";
import { useFetch } from "../lib/hooks";
import { get, post, put, patch, del } from "../lib/api";
import { PageHeader, Button, Modal, Field, Input, Select, Textarea, Loading, ErrorBanner, StatusBadge, EmptyState, Progress } from "../components/ui";
import { dateStr } from "../lib/format";

interface Milestone { id: string; title: string; due_date: string | null; status: string }
interface Project { id: string; name: string; description: string; client_id: string | null; client_name: string | null; status: string; priority: string; start_date: string | null; deadline: string | null; progress: number; notes: string; milestones: Milestone[] }
interface Client { id: string; name: string }

const EMPTY = { name: "", description: "", client_id: "", status: "active", priority: "medium", start_date: "", deadline: "", progress: 0, notes: "" };

export default function Projects() {
  const { data, loading, error, reload } = useFetch<{ items: Project[] }>("/api/projects/");
  const { data: clients } = useFetch<{ items: Client[] }>("/api/clients/");
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);
  const [form, setForm] = useState(EMPTY as any);
  const [err, setErr] = useState<string | null>(null);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Project | null>(null);
  const [milestoneText, setMilestoneText] = useState("");

  const items = data?.items || [];
  const clientOptions = (clients?.items || []).map((c) => ({ value: c.id, label: c.name }));

  const openCreate = () => { setForm(EMPTY as any); setEditing(null); setErr(null); setModal(true); };
  const openEdit = (p: Project) => {
    setForm({ name: p.name, description: p.description, client_id: p.client_id || "", status: p.status, priority: p.priority, start_date: p.start_date || "", deadline: p.deadline || "", progress: p.progress, notes: p.notes });
    setEditing(p); setErr(null); setModal(true);
  };

  const save = async () => {
    setErr(null);
    const payload = { ...form, client_id: form.client_id || null, start_date: form.start_date || null, deadline: form.deadline || null };
    try {
      if (editing) await put(`/api/projects/${editing.id}`, payload);
      else await post("/api/projects/", payload);
      setModal(false);
      reload();
    } catch (e: any) { setErr(e?.message || "Could not save project"); }
  };

  const openDetail = async (id: string) => {
    const p = await get<Project>(`/api/projects/${id}`);
    setDetail(p);
    setDetailId(id);
  };

  const addMilestone = async () => {
    if (!detail || !milestoneText.trim()) return;
    try {
      await post(`/api/projects/${detail.id}/milestones`, { title: milestoneText.trim(), status: "todo" });
      setMilestoneText("");
      const p = await get<Project>(`/api/projects/${detail.id}`);
      setDetail(p);
      reload();
    } catch (e: any) { setErr(e?.message || "Could not add milestone"); }
  };

  const toggleMilestone = async (m: Milestone) => {
    if (!detail) return;
    await patch(`/api/projects/${detail.id}/milestones/${m.id}`, { title: m.title, due_date: m.due_date, status: m.status === "done" ? "todo" : "done" });
    const p = await get<Project>(`/api/projects/${detail.id}`);
    setDetail(p);
    reload();
  };

  if (loading) return <Loading />;
  if (error) return <div className="card card-pad"><EmptyState icon="⚠" title="Couldn’t load projects" detail={error} /></div>;

  return (
    <>
      <PageHeader title="Projects" subtitle="Milestones, deadlines, progress">
        <Button onClick={openCreate}>＋ New project</Button>
      </PageHeader>
      {err ? <ErrorBanner message={err} onDismiss={() => setErr(null)} /> : null}

      {items.length === 0 ? (
        <div className="card card-pad"><EmptyState icon="◉" title="No projects yet" detail="Projects group tasks, milestones and deadlines under one client." action={<Button onClick={openCreate}>＋ New project</Button>} /></div>
      ) : (
        <div className="grid-2">
          {items.map((p) => (
            <div key={p.id} className="card card-pad" style={{ cursor: "pointer" }} onClick={() => openDetail(p.id)}>
              <div className="between" style={{ marginBottom: 10 }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15 }}>{p.name}</div>
                  <div className="text-xs">{p.client_name || "No client"} · {dateStr(p.deadline)}</div>
                </div>
                <StatusBadge status={p.status} />
              </div>
              <Progress value={p.progress} />
              <div className="between" style={{ marginTop: 10 }}>
                <span className="text-xs">{Math.round(p.progress)}% complete</span>
                <span className="text-xs">{p.milestones?.length || 0} milestones</span>
              </div>
              <div className="between" style={{ marginTop: 14 }}>
                <span className="chip">{p.priority}</span>
                <div className="flex" style={{ gap: 6 }} onClick={(e) => e.stopPropagation()}>
                  <Button size="sm" variant="secondary" onClick={() => openEdit(p)}>Edit</Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {modal ? (
        <Modal title={editing ? "Edit project" : "New project"} subtitle={editing ? `Updating ${editing.name}` : "Track one line of work"} onClose={() => setModal(false)}
          footer={<><Button variant="secondary" onClick={() => setModal(false)}>Cancel</Button><Button onClick={save}>Save project</Button></>}>
          <div className="form-grid">
            {err ? <ErrorBanner message={err} onDismiss={() => setErr(null)} /> : null}
            <Field label="Name" required><Input value={form.name} onChange={(v) => setForm({ ...form, name: v })} placeholder="Website redesign" autoFocus /></Field>
            <Field label="Description"><Textarea value={form.description} onChange={(v) => setForm({ ...form, description: v })} rows={3} /></Field>
            <div className="form-row">
              <Field label="Client"><Select value={form.client_id || ""} onChange={(v) => setForm({ ...form, client_id: v })} placeholder="No client" options={clientOptions} /></Field>
              <Field label="Priority"><Select value={form.priority} onChange={(v) => setForm({ ...form, priority: v })} options={["low", "medium", "high", "critical"].map((v) => ({ value: v, label: v }))} /></Field>
            </div>
            <div className="form-row">
              <Field label="Start date"><Input type="date" value={form.start_date || ""} onChange={(v) => setForm({ ...form, start_date: v })} /></Field>
              <Field label="Deadline"><Input type="date" value={form.deadline || ""} onChange={(v) => setForm({ ...form, deadline: v })} /></Field>
            </div>
            <div className="form-row">
              <Field label="Status"><Select value={form.status} onChange={(v) => setForm({ ...form, status: v })} options={["active", "on_hold", "completed", "cancelled"].map((v) => ({ value: v, label: v.replace("_", " ") }))} /></Field>
              <Field label="Progress (%)"><Input type="number" min="0" max="100" value={String(form.progress)} onChange={(v) => setForm({ ...form, progress: Number(v) || 0 })} /></Field>
            </div>
            <Field label="Notes"><Textarea value={form.notes} onChange={(v) => setForm({ ...form, notes: v })} rows={3} /></Field>
          </div>
        </Modal>
      ) : null}

      {detail ? (
        <Modal title={detail.name} subtitle={`${detail.client_name || "No client"} · ${detail.status}`} onClose={() => setDetailId(null)} wide
          footer={<><Button variant="secondary" onClick={() => setDetailId(null)}>Close</Button></>}>
          <div className="form-grid">
            <div className="between">
              <div className="subtle">Progress</div>
              <div style={{ fontWeight: 700 }}>{Math.round(detail.progress)}%</div>
            </div>
            <Progress value={detail.progress} />
            <div className="divider" />
            <div className="subtle" style={{ textTransform: "uppercase", letterSpacing: "0.08em", fontSize: 11, fontWeight: 700 }}>Milestones</div>
            {detail.milestones.length === 0 ? <p className="subtle" style={{ margin: 0 }}>No milestones yet.</p> : (
              <ul className="nowrap-list" style={{ gap: 8 }}>
                {detail.milestones.map((m) => (
                  <li key={m.id} className="between">
                    <label style={{ display: "flex", gap: 8, alignItems: "center", cursor: "pointer" }}>
                      <input type="checkbox" checked={m.status === "done"} onChange={() => toggleMilestone(m)} />
                      <span style={m.status === "done" ? { textDecoration: "line-through", color: "var(--text-3)" } : undefined}>{m.title}</span>
                    </label>
                    <span className="text-xs">{m.due_date ? dateStr(m.due_date) : "no due date"}</span>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex" style={{ gap: 8 }}>
              <Input value={milestoneText} onChange={setMilestoneText} placeholder="Add a milestone…" />
              <Button onClick={addMilestone} variant="secondary" size="sm">Add</Button>
            </div>
            <div className="divider" />
            <div className="subtle" style={{ textTransform: "uppercase", letterSpacing: "0.08em", fontSize: 11, fontWeight: 700 }}>Notes</div>
            <p className="text-sm" style={{ margin: 0 }}>{detail.notes || "(none)"}</p>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
