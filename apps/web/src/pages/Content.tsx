import React, { useMemo, useState } from "react";
import { useFetch } from "../lib/hooks";
import { get, post, put, patch, del } from "../lib/api";
import { PageHeader, Button, Modal, Field, Input, Select, Textarea, Loading, ErrorBanner, StatusBadge, Table, EmptyState, StatCard } from "../components/ui";
import { dateStr } from "../lib/format";

interface ContentItem { id: string; title: string; platform: string; format: string; status: string; body: string; scheduled_for: string | null; published_url: string; performance: Record<string, any>; tags: string[]; notes: string; created_at: string }

const EMPTY = { title: "", platform: "linkedin", format: "post", status: "idea", body: "", scheduled_for: "", published_url: "", performance: {}, tags: [], notes: "" };

export default function ContentStudio() {
  const { data, loading, error, reload } = useFetch<{ items: ContentItem[] }>("/api/content/");
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<ContentItem | null>(null);
  const [form, setForm] = useState(EMPTY as any);
  const [err, setErr] = useState<string | null>(null);

  const items = data?.items || [];
  const byStatus = useMemo(() => ({
    idea: items.filter((i) => i.status === "idea").length,
    draft: items.filter((i) => i.status === "draft").length,
    review: items.filter((i) => i.status === "review").length,
    published: items.filter((i) => i.status === "published").length,
  }), [items]);

  const openCreate = () => { setForm(EMPTY as any); setEditing(null); setErr(null); setModal(true); };
  const openEdit = (c: ContentItem) => {
    setForm({ title: c.title, platform: c.platform, format: c.format, status: c.status, body: c.body, scheduled_for: c.scheduled_for ? c.scheduled_for.slice(0, 16) : "", published_url: c.published_url, performance: c.performance, tags: c.tags || [], notes: c.notes });
    setEditing(c); setErr(null); setModal(true);
  };

  const save = async () => {
    setErr(null);
    const payload = { ...form, scheduled_for: form.scheduled_for || null };
    try {
      if (editing) await put(`/api/content/${editing.id}`, payload);
      else await post("/api/content/", payload);
      setModal(false);
      reload();
    } catch (e: any) { setErr(e?.message || "Could not save content"); }
  };

  const setStatus = async (c: ContentItem, status: string) => {
    try { await patch(`/api/content/${c.id}/status`, { status }); reload(); } catch (e: any) { setErr(e?.message || "Failed"); }
  };

  const remove = async (c: ContentItem) => {
    if (!window.confirm(`Archive "${c.title}"?`)) return;
    try { await del(`/api/content/${c.id}`); reload(); } catch (e: any) { setErr(e?.message || "Failed"); }
  };

  return (
    <>
      <PageHeader title="Content Studio" subtitle="Ideas, drafts, publishing status — AI drafts require human review before publication">
        <Button onClick={openCreate}>＋ New content</Button>
      </PageHeader>
      {err ? <ErrorBanner message={err} onDismiss={() => setErr(null)} /> : null}
      {loading ? <Loading /> : (
        <>
          <div className="stat-grid" style={{ marginBottom: 18 }}>
            <StatCard label="Ideas" value={byStatus.idea} detail="captured" />
            <StatCard label="Drafts" value={byStatus.draft} detail="in progress" />
            <StatCard label="For review" value={byStatus.review} detail="awaiting sign-off" tone="primary" />
            <StatCard label="Published" value={byStatus.published} detail="went out" />
          </div>

          {items.length === 0 ? (
            <div className="card card-pad"><EmptyState icon="✦" title="No content yet" detail="Ideas can be saved manually or produced from the AI Content agent (see AI Agents page). No content is published automatically." action={<Button onClick={openCreate}>＋ New content</Button>} /></div>
          ) : (
            <Table
              rowKey={(r: ContentItem) => r.id}
              rows={items}
              columns={[
                { key: "title", label: "Title", render: (c: ContentItem) => (
                  <div>
                    <div style={{ fontWeight: 650 }}>{c.title}</div>
                    <div className="text-xs">{c.platform} · {c.format}{c.published_url ? " · published" : ""}</div>
                  </div>
                )},
                { key: "status", label: "Status", render: (c: ContentItem) => <StatusBadge status={c.status} /> },
                { key: "scheduled_for", label: "Scheduled", render: (c: ContentItem) => <span className="text-xs">{c.scheduled_for ? dateStr(c.scheduled_for) : "—"}</span> },
                { key: "actions", label: "", render: (c: ContentItem) => (
                  <div className="flex" style={{ gap: 6, flexWrap: "wrap" }}>
                    {c.status !== "review" ? <Button size="sm" variant="secondary" onClick={() => setStatus(c, "review")}>To review</Button> : null}
                    {c.status !== "published" ? <Button size="sm" variant="secondary" onClick={() => setStatus(c, "published")}>Mark published</Button> : null}
                    <Button size="sm" variant="secondary" onClick={() => openEdit(c)}>Edit</Button>
                    <Button size="sm" variant="danger" onClick={() => remove(c)}>✕</Button>
                  </div>
                )},
              ]}
            />
          )}
        </>
      )}

      {modal ? (
        <Modal title={editing ? "Edit content" : "New content"} subtitle={editing ? `Updating "${editing.title}"` : "Save an idea or a draft"} onClose={() => setModal(false)}
          footer={<><Button variant="secondary" onClick={() => setModal(false)}>Cancel</Button><Button onClick={save}>Save content</Button></>}>
          <div className="form-grid">
            {err ? <ErrorBanner message={err} onDismiss={() => setErr(null)} /> : null}
            <Field label="Title" required><Input value={form.title} onChange={(v) => setForm({ ...form, title: v })} placeholder="Why I switched from bullet lists to structured posts" autoFocus /></Field>
            <div className="form-row">
              <Field label="Platform"><Select value={form.platform} onChange={(v) => setForm({ ...form, platform: v })} options={["linkedin", "blog", "newsletter", "article", "twitter", "other"].map((v) => ({ value: v, label: v }))} /></Field>
              <Field label="Format"><Select value={form.format} onChange={(v) => setForm({ ...form, format: v })} options={["post", "article", "newsletter", "thread", "video-script"].map((v) => ({ value: v, label: v }))} /></Field>
            </div>
            <div className="form-row">
              <Field label="Status"><Select value={form.status} onChange={(v) => setForm({ ...form, status: v })} options={["idea", "draft", "review", "scheduled", "published", "archived"].map((v) => ({ value: v, label: v }))} /></Field>
              <Field label="Scheduled for"><Input type="datetime-local" value={form.scheduled_for || ""} onChange={(v) => setForm({ ...form, scheduled_for: v })} /></Field>
            </div>
            <Field label="Body"><Textarea mono rows={12} value={form.body} onChange={(v) => setForm({ ...form, body: v })} placeholder="Markdown content…" /></Field>
            <Field label="Published URL"><Input value={form.published_url} onChange={(v) => setForm({ ...form, published_url: v })} placeholder="https://…" /></Field>
            <Field label="Tags (comma separated)"><Input value={(form.tags || []).join(", ")} onChange={(v) => setForm({ ...form, tags: v.split(",").map((t) => t.trim()).filter(Boolean) })} /></Field>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
