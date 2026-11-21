import React, { useState } from "react";
import { useFetch } from "../lib/hooks";
import { get, post, put, del } from "../lib/api";
import { PageHeader, Button, Modal, Field, Input, Textarea, Loading, ErrorBanner, Table, EmptyState, StatusBadge, Chip } from "../components/ui";
import { dateStr } from "../lib/format";

interface Research { id: string; title: string; source_urls: string[]; summary: string; tags: string[]; related_projects: string[]; created_from: string; created_at: string; updated_at: string }

const EMPTY = { title: "", source_urls: [], summary: "", tags: [], related_projects: [], created_from: "manual" };

export default function Research() {
  const { data, loading, error, reload } = useFetch<{ items: Research[] }>("/api/research/");
  const [modal, setModal] = useState(false);
  const [editing, setEditing] = useState<Research | null>(null);
  const [form, setForm] = useState(EMPTY as any);
  const [err, setErr] = useState<string | null>(null);

  const items = data?.items || [];

  const openCreate = () => { setForm(EMPTY as any); setEditing(null); setErr(null); setModal(true); };
  const openEdit = (r: Research) => {
    setForm({ title: r.title, source_urls: r.source_urls || [], summary: r.summary, tags: r.tags || [], related_projects: r.related_projects || [], created_from: r.created_from });
    setEditing(r); setErr(null); setModal(true);
  };

  const save = async () => {
    setErr(null);
    try {
      if (editing) await put(`/api/research/${editing.id}`, form);
      else await post("/api/research/", form);
      setModal(false);
      reload();
    } catch (e: any) { setErr(e?.message || "Could not save research"); }
  };

  const remove = async (r: Research) => {
    if (!window.confirm(`Delete "${r.title}"?`)) return;
    try { await del(`/api/research/${r.id}`); reload(); } catch (e: any) { setErr(e?.message || "Failed"); }
  };

  return (
    <>
      <PageHeader title="Research" subtitle="Market, competitors, strategic notes — source-backed, no fabricated facts">
        <Button onClick={openCreate}>＋ New research</Button>
      </PageHeader>
      {err ? <ErrorBanner message={err} onDismiss={() => setErr(null)} /> : null}
      {loading ? <Loading /> : (
        <>
          {items.length === 0 ? (
            <div className="card card-pad"><EmptyState icon="⌕" title="No research yet" detail="Add market analysis, competitor notes, or internal summaries. Sources and retrieval dates are kept with each entry." action={<Button onClick={openCreate}>＋ New research</Button>} /></div>
          ) : (
            <div className="grid-2">
              {items.map((r) => (
                <div key={r.id} className="card card-pad" style={{ cursor: "pointer" }} onClick={() => openEdit(r)}>
                  <div className="between" style={{ marginBottom: 8 }}>
                    <h3 style={{ fontSize: 15, lineHeight: 1.35 }}>{r.title}</h3>
                    <StatusBadge status={r.created_from} />
                  </div>
                  <p className="subtle" style={{ margin: "0 0 10px" }}>{(r.summary || "No summary yet.").slice(0, 220)}{(r.summary || "").length > 220 ? "…" : ""}</p>
                  <div className="badge-list">{(r.tags || []).map((t) => <Chip key={t}>{t}</Chip>)}</div>
                  <div className="between" style={{ marginTop: 12 }}>
                    <span className="text-xs">{dateStr(r.updated_at)}</span>
                    <div className="flex" style={{ gap: 6 }} onClick={(e) => e.stopPropagation()}>
                      <Button size="sm" variant="secondary" onClick={() => openEdit(r)}>Edit</Button>
                      <Button size="sm" variant="danger" onClick={() => remove(r)}>✕</Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {modal ? (
        <Modal title={editing ? "Edit research" : "New research"} subtitle={editing ? `Updating "${editing.title}"` : "Store source-backed notes"} onClose={() => setModal(false)}
          footer={<><Button variant="secondary" onClick={() => setModal(false)}>Cancel</Button><Button onClick={save}>Save research</Button></>} wide>
          <div className="form-grid">
            {err ? <ErrorBanner message={err} onDismiss={() => setErr(null)} /> : null}
            <Field label="Title" required><Input value={form.title} onChange={(v) => setForm({ ...form, title: v })} autoFocus /></Field>
            <Field label="Source URLs (one per line)" hint="Each URL will stay with the note forever — never invented.">
              <Textarea mono rows={3} value={(form.source_urls || []).join("\n")} onChange={(v) => setForm({ ...form, source_urls: v.split("\n").map((u) => u.trim()).filter(Boolean) })} placeholder="https://…" />
            </Field>
            <Field label="Summary"><Textarea mono rows={8} value={form.summary} onChange={(v) => setForm({ ...form, summary: v })} placeholder="Key takeaways, evidence, sources…" /></Field>
            <Field label="Tags (comma separated)"><Input value={(form.tags || []).join(", ")} onChange={(v) => setForm({ ...form, tags: v.split(",").map((t) => t.trim()).filter(Boolean) })} /></Field>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
