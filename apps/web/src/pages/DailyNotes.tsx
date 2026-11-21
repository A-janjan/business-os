import React, { useEffect, useMemo, useState } from "react";
import { get, put, post } from "../lib/api";
import { PageHeader, Button, Loading, ErrorBanner, Textarea, StatusBadge, EmptyState } from "../components/ui";
import { dateTimeStr } from "../lib/format";

interface NoteList { path: string; title: string; folder: string; frontmatter: Record<string, any>; is_daily_note: boolean }
interface DailyNoteDetail { path: string; title: string; body: string; sections: Record<string, string[]>; finance_lines: Array<{ kind: string; amount: number | null; currency: string; client: string }> }

export default function DailyNotes() {
  const [notes, setNotes] = useState<NoteList[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(new Date().toISOString().split("T")[0]);
  const [detail, setDetail] = useState<DailyNoteDetail | null>(null);
  const [body, setBody] = useState("");
  const [title, setTitle] = useState("");
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await get<{ items: NoteList[] }>("/api/notes/");
      setNotes(r.items || []);
    } catch (e: any) { setErr(e?.message || "Could not load daily notes"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const openNote = async (d: string) => {
    setSelected(d);
    setErr(null);
    try {
      const r = await get<DailyNoteDetail>(`/api/notes/${d}`);
      setDetail(r);
      setBody(r.body || "");
      setTitle(r.title || `Daily Note - ${d}`);
    } catch {
      setDetail(null);
      setBody(`# Daily Note - ${d}\n\n## Completed\n\n## Tasks\n- [ ]\n\n## Meetings\n\n## Decisions\n\n## Income\n\n## Expenses\n\n## Ideas\n\n## Blockers\n`);
      setTitle(`Daily Note - ${d}`);
    }
  };

  useEffect(() => { if (selected) openNote(selected); }, [selected]);

  const save = async () => {
    if (!selected) return;
    setSaving(true);
    setErr(null);
    try {
      await put(`/api/notes/${selected}`, { title, body });
      await openNote(selected);
      await load();
    } catch (e: any) { setErr(e?.message || "Could not save daily note"); }
    finally { setSaving(false); }
  };

  const destructure = useMemo(() => {
    if (!detail) return { sections: {} as Record<string, string[]>, finances: [] as any[] };
    return { sections: detail.sections || {}, finances: detail.finance_lines || [] };
  }, [detail]);

  const today = new Date().toISOString().split("T")[0];

  return (
    <>
      <PageHeader title="Daily Notes" subtitle="Journal with automatic structured extraction — notes are plain Markdown, extraction never modifies the original">
        <Button variant="secondary" onClick={() => openNote(today)}>↺ Today</Button>
      </PageHeader>
      {err ? <ErrorBanner message={err} onDismiss={() => setErr(null)} /> : null}

      <div className="grid-sidebar">
        <div>
          <div className="toolbar">
            <input
              type="date"
              className="input"
              style={{ maxWidth: 220 }}
              value={selected || ""}
              onChange={(e) => setSelected(e.target.value)}
            />
            <Button variant="secondary" size="sm" onClick={save} loading={saving}>Save draft</Button>
          </div>

          {loading ? <Loading /> : (
            <div className="card card-pad">
              <div className="mono subtle" style={{ marginBottom: 8 }}>07-DAILY-NOTES/{selected}-daily.md</div>
              <Textarea mono rows={22} value={body} onChange={setBody} />
            </div>
          )}
        </div>

        <aside style={{ display: "grid", gap: 16, alignContent: "start" }}>
          <section className="card card-pad">
            <h3 style={{ fontSize: 15, marginBottom: 10 }}>Structured extraction</h3>
            {destructure.sections && Object.keys(destructure.sections).length > 0 ? (
              Object.entries(destructure.sections).map(([name, items]) => (
                <div key={name} style={{ marginBottom: 10 }}>
                  <div className="mono" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-3)", fontWeight: 700 }}>{name}</div>
                  {items.slice(0, 8).map((line, i) => <div key={i} className="text-xs" style={{ marginTop: 3 }}>{line}</div>)}
                </div>
              ))
            ) : <p className="subtle" style={{ margin: 0 }}>Write sections like <code className="mono">## Completed</code>, <code className="mono">## Income</code>, <code className="mono">## Tasks</code> and see them extracted here.</p>}
            {destructure.finances.length > 0 ? (
              <div style={{ marginTop: 10 }}>
                <div className="mono" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-3)", fontWeight: 700, marginBottom: 6 }}>Detected income</div>
                {destructure.finances.map((f, i) => (
                  <div key={i} className="between text-xs" style={{ padding: "6px 0", borderBottom: "1px dashed var(--border)" }}>
                    <span>{f.client}</span>
                    <span style={{ fontWeight: 700 }}>{f.amount ?? "?"} {f.currency}</span>
                  </div>
                ))}
              </div>
            ) : null}
          </section>

          <section className="card card-pad">
            <div className="between" style={{ marginBottom: 10 }}>
              <h3 style={{ fontSize: 15 }}>Note history</h3>
              <span className="chip">{notes.length}</span>
            </div>
            {notes.length === 0 ? <p className="subtle" style={{ margin: 0 }}>No daily notes yet.</p> : (
              <ul className="nowrap-list" style={{ gap: 8 }}>
                {notes.slice(0, 20).map((n) => (
                  <li key={n.path} className="between">
                    <button className="link" style={{ border: "none", background: "transparent", padding: 0, textAlign: "left" }} onClick={() => openNote(String(n.frontmatter?.date || ""))}>
                      <div className="text-sm" style={{ fontWeight: 650 }}>{String(n.frontmatter?.date || "—")}</div>
                      <div className="text-xs">{n.title}</div>
                    </button>
                    {selected === String(n.frontmatter?.date || "") ? <StatusBadge status="today" /> : null}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </aside>
      </div>
    </>
  );
}
