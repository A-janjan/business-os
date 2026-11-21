import React, { useMemo, useState } from "react";
import { get, post, patch } from "../lib/api";
import { useFetch } from "../lib/hooks";
import { PageHeader, Button, Modal, Field, Input, Select, Textarea, Loading, ErrorBanner, Table, EmptyState, StatusBadge, Chip } from "../components/ui";
import { dateStr } from "../lib/format";

interface Note { path: string; title: string; folder: string; tags: string[]; frontmatter: Record<string, any>; updated_at: number; size: number; is_daily_note: boolean }

const FOLDERS = ["00-SYSTEM", "01-CLIENTS", "02-PROJECTS", "03-OPERATIONS", "04-CONTENT", "05-FINANCES", "06-RESEARCH", "07-DAILY-NOTES", "08-QUEUE", "09-GENERATED", "10-ARCHIVE"];

export default function Knowledge() {
  const [q, setQ] = useState("");
  const [folder, setFolder] = useState("");
  const [tag, setTag] = useState("");
  const { data, loading, error, reload } = useFetch<{ items: Note[] }>(`/api/knowledge/notes?q=${encodeURIComponent(q)}&folder=${encodeURIComponent(folder)}&tag=${encodeURIComponent(tag)}`);
  const [editor, setEditor] = useState<Note | null>(null);
  const [body, setBody] = useState("");
  const [fm, setFm] = useState<Record<string, any>>({});
  const [err, setErr] = useState<string | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [newPath, setNewPath] = useState("");
  const [backlinks, setBacklinks] = useState<string[] | null>(null);
  const [structure, setStructure] = useState<{ folders: Array<{ name: string; count: number }>; notes_total: number } | null>(null);

  React.useEffect(() => {
    get<any>("/api/knowledge/structure").then((s) => setStructure(s as any)).catch(() => setStructure(null));
  }, []);

  const items = data?.items || [];

  const openNote = async (n: Note) => {
    setErr(null);
    try {
      const full = await get<any>(`/api/knowledge/note?path=${encodeURIComponent(n.path)}`);
      setEditor({ ...n, frontmatter: full.frontmatter || {} });
      setBody(full.body || "");
      setFm(full.frontmatter || {});
      setIsNew(false);
      setBacklinks(full.links || []);
    } catch (e: any) { setErr(e?.message || "Could not open note"); }
  };

  const openCreate = () => {
    setEditor(null);
    setIsNew(true);
    setNewPath("01-CLIENTS/new-note.md");
    setBody("");
    setFm({ title: "", type: "note", tags: [] });
    setBacklinks(null);
    setErr(null);
  };

  const loadBacklinks = async (path: string) => {
    try {
      const r = await get<{ backlinks: string[] }>(`/api/knowledge/backlinks?path=${encodeURIComponent(path)}`);
      setBacklinks(r.backlinks);
    } catch { setBacklinks([]); }
  };

  const save = async () => {
    setErr(null);
    try {
      if (isNew) {
        const title = fm.title || newPath.split("/").pop()?.replace(/\.md$/, "") || "Untitled";
        await post("/api/knowledge/notes", { path: newPath, frontmatter: { ...fm, title }, body });
      } else {
        await patch("/api/knowledge/note", { path: editor!.path, frontmatter: fm, body });
      }
      setEditor(null);
      setIsNew(false);
      setBacklinks(null);
      reload();
    } catch (e: any) { setErr(e?.message || "Could not save note"); }
  };

  const archive = async () => {
    if (!editor || !window.confirm(`Archive ${editor.title}? It will move to 10-ARCHIVE.`)) return;
    try {
      await post("/api/knowledge/note/archive", { path: editor.path });
      setEditor(null);
      setIsNew(false);
      setBacklinks(null);
      reload();
    } catch (e: any) { setErr(e?.message || "Could not archive note"); }
  };

  return (
    <>
      <PageHeader title="Knowledge Base" subtitle="Obsidian-compatible Markdown vault — plain files, not a hidden database">
        <Button onClick={openCreate}>＋ New note</Button>
      </PageHeader>
      {err ? <ErrorBanner message={err} onDismiss={() => setErr(null)} /> : null}

      <div className="grid-sidebar">
        <div>
          <div className="toolbar">
            <div className="search-input">
              <span>⌕</span>
              <input placeholder="Search notes, tags, frontmatter…" value={q} onChange={(e) => setQ(e.target.value)} />
            </div>
            <Select value={folder} onChange={setFolder} placeholder="All folders" options={FOLDERS.map((f) => ({ value: f, label: f }))} style={{ width: 200 }} />
            <Input value={tag} onChange={setTag} placeholder="Filter by tag" style={{ width: 180 }} />
          </div>

          {loading ? <Loading /> : (
            <Table
              rowKey={(r: Note) => r.path}
              rows={items}
              empty="No notes match. Create your first note."
              columns={[
                { key: "title", label: "Title", render: (n: Note) => (
                  <button className="link" style={{ border: "none", background: "transparent", padding: 0, textAlign: "left" }} onClick={() => openNote(n)}>
                    <div style={{ fontWeight: 650, color: "var(--text)" }}>{n.title}</div>
                    <div className="text-xs">{n.folder} · {n.size.toLocaleString()} B</div>
                  </button>
                )},
                { key: "folder", label: "Folder", render: (n: Note) => <span className="text-xs">{n.folder}</span> },
                { key: "tags", label: "Tags", render: (n: Note) => (
                  <div className="badge-list">
                    {(n.tags || []).slice(0, 4).map((t: string) => <span key={t} className="tag">{t}</span>)}
                    {(n.tags || []).length > 4 ? <span className="text-xs">+{(n.tags || []).length - 4}</span> : null}
                  </div>
                )},
                { key: "updated_at", label: "Updated", render: (n: Note) => <span className="text-xs">{dateStr(new Date(n.updated_at * 1000).toISOString())}</span> },
              ]}
            />
          )}
        </div>

        <aside style={{ display: "grid", gap: 16, alignContent: "start" }}>
          <section className="card card-pad">
            <h3 style={{ fontSize: 15, marginBottom: 10 }}>Vault structure</h3>
            {structure ? (
              <>
                <p className="subtle" style={{ margin: "0 0 10px" }}>{structure.notes_total} notes across {structure.folders.length} folders</p>
                <ul className="nowrap-list" style={{ gap: 6 }}>
                  {structure.folders.map((f) => (
                    <li key={f.name} className="between">
                      <span className="text-sm">{f.name}</span>
                      <span className="text-xs">{f.count}</span>
                    </li>
                  ))}
                </ul>
              </>
            ) : <p className="subtle">Loading…</p>}
          </section>

          <section className="card card-pad">
            <h3 style={{ fontSize: 15, marginBottom: 10 }}>How it stays Obsidian-compatible</h3>
            <p className="subtle" style={{ margin: 0 }}>Files are plain Markdown with YAML frontmatter under <code className="mono">knowledge/</code>. Open the vault folder directly in Obsidian or any editor — no plugin required.</p>
          </section>
        </aside>
      </div>

      {editor || isNew ? (
        <Modal
          title={isNew ? "New note" : editor!.title}
          subtitle={isNew ? "Create a Markdown note in the vault" : editor!.path}
          onClose={() => { setEditor(null); setIsNew(false); setBacklinks(null); }}
          wide
          footer={<>
            <Button variant="secondary" onClick={() => { setEditor(null); setIsNew(false); setBacklinks(null); }}>Cancel</Button>
            {editor ? <Button variant="danger" onClick={archive}>Archive</Button> : null}
            <Button onClick={save}>Save note</Button>
          </>}
        >
          <div className="form-grid">
            {err ? <ErrorBanner message={err} onDismiss={() => setErr(null)} /> : null}
            {isNew ? (
              <Field label="Path" hint="Relative path inside the vault, e.g. 01-CLIENTS/Acme-Corp.md">
                <Input value={newPath} onChange={setNewPath} className="mono" />
              </Field>
            ) : null}
            <div className="form-row">
              <Field label="Title"><Input value={String(fm.title || "")} onChange={(v) => setFm({ ...fm, title: v })} /></Field>
              <Field label="Type"><Input value={String(fm.type || "")} onChange={(v) => setFm({ ...fm, type: v })} placeholder="client / project / research / …" /></Field>
            </div>
            <Field label="Tags (comma separated)"><Input value={(fm.tags || []).join(", ")} onChange={(v) => setFm({ ...fm, tags: v.split(",").map((t) => t.trim()).filter(Boolean) })} /></Field>
            <Field label="Body"><Textarea mono rows={12} value={body} onChange={setBody} placeholder="# Note title\n\nWrite here…" /></Field>
            {backlinks ? (
              <div>
                <div className="subtle" style={{ textTransform: "uppercase", letterSpacing: "0.08em", fontSize: 11, fontWeight: 700, marginBottom: 6 }}>Wiki links in this note</div>
                <div className="badge-list">{backlinks.length ? backlinks.map((l) => <Chip key={l}>{l}</Chip>) : <span className="subtle">No wiki links. Use [[Note-Name]] syntax.</span>}</div>
              </div>
            ) : null}
          </div>
        </Modal>
      ) : null}
    </>
  );
}
