import React, { useMemo, useState } from "react";
import { useFetch } from "../lib/hooks";
import { get, post, put, patch, del } from "../lib/api";
import { PageHeader, Button, Modal, Field, Input, Select, Textarea, Loading, ErrorBanner, StatusBadge, Table, EmptyState, StatCard } from "../components/ui";
import { dateStr } from "../lib/format";

interface Task { id: string; title: string; description: string; priority: string; status: string; project_id: string | null; project_name: string | null; client_id: string | null; client_name: string | null; start_date: string | null; due_date: string | null; completed_at: string | null; recurrence: string }
interface Project { id: string; name: string }
interface Client { id: string; name: string }

const EMPTY = { title: "", description: "", priority: "medium", status: "todo", project_id: "", client_id: "", start_date: "", due_date: "", recurrence: "" };

type Filter = "all" | "today" | "upcoming" | "overdue" | "done";

export default function Tasks() {
  const [filter, setFilter] = useState<Filter>("all");
  const { data, loading, error, reload } = useFetch<{ items: Task[] }>("/api/tasks/?include_done=true&limit=1000");
  const { data: clients } = useFetch<{ items: Client[] }>("/api/clients/");
  const { data: projects } = useFetch<{ items: Project[] }>("/api/projects/");
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<Task | null>(null);
  const [form, setForm] = useState(EMPTY as any);
  const [err, setErr] = useState<string | null>(null);

  const items = data?.items || [];
  const today = new Date().toISOString().split("T")[0];

  const filtered = useMemo(() => {
    const list = items;
    switch (filter) {
      case "today": return list.filter((t) => t.due_date === today && t.status !== "done" && t.status !== "archived");
      case "upcoming": return list.filter((t) => t.due_date && t.due_date >= today && t.status !== "done" && t.status !== "archived");
      case "overdue": return list.filter((t) => t.due_date && t.due_date < today && t.status !== "done" && t.status !== "archived");
      case "done": return list.filter((t) => t.status === "done");
      default: return list;
    }
  }, [items, filter, today]);

  const counts = useMemo(() => ({
    today: items.filter((t) => t.due_date === today && t.status !== "done" && t.status !== "archived").length,
    upcoming: items.filter((t) => t.due_date && t.due_date >= today && t.status !== "done" && t.status !== "archived").length,
    overdue: items.filter((t) => t.due_date && t.due_date < today && t.status !== "done" && t.status !== "archived").length,
    done: items.filter((t) => t.status === "done").length,
  }), [items, today]);

  const openCreate = () => { setForm(EMPTY as any); setEditing(null); setErr(null); setModal(true); };
  const openEdit = (t: Task) => {
    setForm({ title: t.title, description: t.description, priority: t.priority, status: t.status, project_id: t.project_id || "", client_id: t.client_id || "", start_date: t.start_date || "", due_date: t.due_date || "", recurrence: t.recurrence });
    setEditing(t); setErr(null); setModal(true);
  };

  const save = async () => {
    setErr(null);
    const payload = { ...form, project_id: form.project_id || null, client_id: form.client_id || null, start_date: form.start_date || null, due_date: form.due_date || null };
    try {
      if (editing) await put(`/api/tasks/${editing.id}`, payload);
      else await post("/api/tasks/", payload);
      setModal(false);
      reload();
    } catch (e: any) { setErr(e?.message || "Could not save task"); }
  };

  const toggleDone = async (t: Task) => {
    const newStatus = t.status === "done" ? "todo" : "done";
    try { await patch(`/api/tasks/${t.id}/status`, { status: newStatus }); reload(); } catch (e: any) { setErr(e?.message || "Failed"); }
  };

  const remove = async (t: Task) => {
    if (!window.confirm(`Remove "${t.title}"?`)) return;
    try { await del(`/api/tasks/${t.id}`); reload(); } catch (e: any) { setErr(e?.message || "Failed"); }
  };

  return (
    <>
      <PageHeader title="Tasks" subtitle="Delegate, track, complete">
        <Button onClick={openCreate}>＋ New task</Button>
      </PageHeader>
      {err ? <ErrorBanner message={err} onDismiss={() => setErr(null)} /> : null}
      {loading ? <Loading /> : (
        <>
          <div className="stat-grid" style={{ marginBottom: 16 }}>
            <button className={`card stat-card ${filter === "today" ? "active" : ""}`} style={{ border: "none", textAlign: "left", padding: 16 }} onClick={() => setFilter("today")}>
              <div className="stat-label">Today</div><div className="stat-value">{counts.today}</div>
            </button>
            <button className="card stat-card" style={{ border: "none", textAlign: "left", padding: 16 }} onClick={() => setFilter("upcoming")}>
              <div className="stat-label">Upcoming</div><div className="stat-value">{counts.upcoming}</div>
            </button>
            <button className="card stat-card" style={{ border: "none", textAlign: "left", padding: 16, borderColor: counts.overdue > 0 ? "#fecaca" : undefined }} onClick={() => setFilter("overdue")}>
              <div className="stat-label">Overdue</div><div className="stat-value" style={{ color: counts.overdue > 0 ? "var(--danger)" : undefined }}>{counts.overdue}</div>
            </button>
            <button className="card stat-card" style={{ border: "none", textAlign: "left", padding: 16 }} onClick={() => setFilter("done")}>
              <div className="stat-label">Completed</div><div className="stat-value">{counts.done}</div>
            </button>
          </div>

          <div className="tabs">
            {(["all", "today", "upcoming", "overdue", "done"] as Filter[]).map((f) => (
              <button key={f} className={`tab-btn ${filter === f ? "active" : ""}`} onClick={() => setFilter(f)}>{f[0].toUpperCase() + f.slice(1)}</button>
            ))}
          </div>

          {filtered.length === 0 ? (
            <div className="card card-pad"><EmptyState icon="✓" title="Nothing here" detail="Try a different filter or add a task." action={<Button onClick={openCreate}>＋ New task</Button>} /></div>
          ) : (
            <Table
              rowKey={(r: Task) => r.id}
              rows={filtered}
              columns={[
                { key: "check", label: "", render: (t: Task) => (
                  <button onClick={() => toggleDone(t)} title={t.status === "done" ? "Mark pending" : "Mark done"}
                    style={{ width: 22, height: 22, borderRadius: 6, border: "2px solid var(--border-strong)", background: t.status === "done" ? "var(--success)" : "transparent", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 12, fontWeight: 700 }}>
                    {t.status === "done" ? "✓" : ""}
                  </button>
                )},
                { key: "title", label: "Task", render: (t: Task) => (
                  <div>
                    <div style={{ fontWeight: 650, textDecoration: t.status === "done" ? "line-through" : "none", color: t.status === "done" ? "var(--text-3)" : undefined }}>{t.title}</div>
                    <div className="text-xs">{t.project_name ? `${t.project_name}` : "—"}{t.client_name ? ` · ${t.client_name}` : ""}</div>
                  </div>
                )},
                { key: "priority", label: "Priority", render: (t: Task) => <span className="chip">{t.priority}</span> },
                { key: "due_date", label: "Due", render: (t: Task) => <span className={t.due_date && t.due_date < today && t.status !== "done" ? "badge badge-danger" : "text-xs"}>{t.due_date ? dateStr(t.due_date) : "—"}</span> },
                { key: "status", label: "Status", render: (t: Task) => <StatusBadge status={t.status} /> },
                { key: "actions", label: "", render: (t: Task) => (
                  <div className="flex" style={{ gap: 6 }}>
                    <Button size="sm" variant="secondary" onClick={() => openEdit(t)}>Edit</Button>
                    <Button size="sm" variant="danger" onClick={() => remove(t)}>✕</Button>
                  </div>
                )},
              ]}
            />
          )}
        </>
      )}

      {modal ? (
        <Modal title={editing ? "Edit task" : "New task"} subtitle={editing ? `Updating "${editing.title}"` : "Add a task with a due date and priority"} onClose={() => setModal(false)}
          footer={<><Button variant="secondary" onClick={() => setModal(false)}>Cancel</Button><Button onClick={save}>Save task</Button></>}>
          <div className="form-grid">
            {err ? <ErrorBanner message={err} onDismiss={() => setErr(null)} /> : null}
            <Field label="Title" required><Input value={form.title} onChange={(v) => setForm({ ...form, title: v })} placeholder="Finish the weekly report" autoFocus /></Field>
            <Field label="Description"><Textarea value={form.description} onChange={(v) => setForm({ ...form, description: v })} rows={3} /></Field>
            <div className="form-row">
              <Field label="Priority"><Select value={form.priority} onChange={(v) => setForm({ ...form, priority: v })} options={["low", "medium", "high", "critical"].map((v) => ({ value: v, label: v }))} /></Field>
              <Field label="Status"><Select value={form.status} onChange={(v) => setForm({ ...form, status: v })} options={["todo", "in_progress", "blocked", "done", "archived"].map((v) => ({ value: v, label: v.replace("_", " ") }))} /></Field>
            </div>
            <div className="form-row">
              <Field label="Project"><Select value={form.project_id || ""} onChange={(v) => setForm({ ...form, project_id: v })} placeholder="None" options={(projects?.items || []).map((p) => ({ value: p.id, label: p.name }))} /></Field>
              <Field label="Client"><Select value={form.client_id || ""} onChange={(v) => setForm({ ...form, client_id: v })} placeholder="None" options={(clients?.items || []).map((c) => ({ value: c.id, label: c.name }))} /></Field>
            </div>
            <div className="form-row">
              <Field label="Start"><Input type="date" value={form.start_date || ""} onChange={(v) => setForm({ ...form, start_date: v })} /></Field>
              <Field label="Due"><Input type="date" value={form.due_date || ""} onChange={(v) => setForm({ ...form, due_date: v })} /></Field>
            </div>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
