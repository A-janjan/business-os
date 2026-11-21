import React, { useState } from "react";
import { useFetch } from "../lib/hooks";
import { get, post, put, del } from "../lib/api";
import { PageHeader, Button, Modal, Field, Input, Select, Textarea, StatCard, Loading, ErrorBanner, StatusBadge, Table, EmptyState } from "../components/ui";
import { money, dateStr } from "../lib/format";

interface Client { id: string; name: string; company: string; status: string; email: string; phone: string; payment_terms: string; contract_notes: string; notes: string; revenue_total: number }

const EMPTY = { name: "", company: "", status: "active", email: "", phone: "", payment_terms: "", contract_notes: "", notes: "" };

export default function Clients() {
  const { data, loading, error, reload } = useFetch<{ items: Client[] }>("/api/clients/");
  const [modal, setModal] = useState<"create" | "edit" | null>(null);
  const [editing, setEditing] = useState<Client | null>(null);
  const [form, setForm] = useState(EMPTY);
  const [err, setErr] = useState<string | null>(null);

  const items = data?.items || [];
  const totalRevenue = items.reduce((s, c) => s + (c.revenue_total || 0), 0);

  const openCreate = () => { setForm(EMPTY); setEditing(null); setErr(null); setModal("create"); };
  const openEdit = (c: Client) => { setForm({ name: c.name, company: c.company, status: c.status, email: c.email, phone: c.phone, payment_terms: c.payment_terms, contract_notes: c.contract_notes, notes: c.notes }); setEditing(c); setErr(null); setModal("edit"); };

  const save = async () => {
    setErr(null);
    try {
      if (editing) await put(`/api/clients/${editing.id}`, form);
      else await post("/api/clients/", form);
      setModal(null);
      reload();
    } catch (e: any) { setErr(e?.message || "Could not save client"); }
  };

  const remove = async (c: Client) => {
    if (!window.confirm(`Mark ${c.name} as churned?`)) return;
    try { await del(`/api/clients/${c.id}`); reload(); } catch (e: any) { setErr(e?.message || "Failed"); }
  };

  return (
    <>
      <PageHeader title="Clients" subtitle="Relationships, payment terms, revenue per client">
        <Button onClick={openCreate}>＋ New client</Button>
      </PageHeader>
      {err ? <ErrorBanner message={err} onDismiss={() => setErr(null)} /> : null}
      {loading ? <Loading /> : (
        <>
          <div className="stat-grid" style={{ marginBottom: 18 }}>
            <StatCard label="Total clients" value={items.length} detail="all statuses" />
            <StatCard label="Active" value={items.filter((c) => c.status === "active").length} detail="in good standing" />
            <StatCard label="Prospects" value={items.filter((c) => c.status === "prospect").length} detail="pipeline" />
            <StatCard label="Total revenue" value={money(totalRevenue)} detail="recorded income" tone="primary" />
          </div>

          {items.length === 0 ? (
            <div className="card card-pad"><EmptyState icon="◈" title="No clients yet" detail="Add your first client to start tracking revenue and contracts." action={<Button onClick={openCreate}>＋ New client</Button>} /></div>
          ) : (
            <Table
              rowKey={(r: Client) => r.id}
              rows={items}
              columns={[
                { key: "name", label: "Client", render: (c: Client) => (
                  <div>
                    <div style={{ fontWeight: 650 }}>{c.name}</div>
                    <div className="text-xs">{c.company || "—"}</div>
                  </div>
                )},
                { key: "status", label: "Status", render: (c: Client) => <StatusBadge status={c.status} /> },
                { key: "email", label: "Contact", render: (c: Client) => <span className="text-xs">{c.email || "—"}{c.phone ? <span> · {c.phone}</span> : null}</span> },
                { key: "revenue_total", label: "Revenue", render: (c: Client) => <span style={{ fontWeight: 700 }}>{money(c.revenue_total)}</span> },
                { key: "actions", label: "", render: (c: Client) => (
                  <div className="flex" style={{ gap: 6 }}>
                    <Button size="sm" variant="secondary" onClick={() => openEdit(c)}>Edit</Button>
                    <Button size="sm" variant="danger" onClick={() => remove(c)}>Remove</Button>
                  </div>
                )},
              ]}
            />
          )}
        </>
      )}

      {modal ? (
        <Modal title={editing ? "Edit client" : "New client"} subtitle={editing ? `Updating ${editing.name}` : "Add a client to your book"} onClose={() => setModal(null)}
          footer={<><Button variant="secondary" onClick={() => setModal(null)}>Cancel</Button><Button onClick={save}>Save client</Button></>}>
          <div className="form-grid">
            {err ? <ErrorBanner message={err} onDismiss={() => setErr(null)} /> : null}
            <div className="form-row">
              <Field label="Name" required><Input value={form.name} onChange={(v) => setForm({ ...form, name: v })} placeholder="Acme Corp" autoFocus /></Field>
              <Field label="Company"><Input value={form.company} onChange={(v) => setForm({ ...form, company: v })} placeholder="Acme Inc." /></Field>
            </div>
            <div className="form-row">
              <Field label="Status"><Select value={form.status} onChange={(v) => setForm({ ...form, status: v })} options={[{ value: "active", label: "Active" }, { value: "prospect", label: "Prospect" }, { value: "inactive", label: "Inactive" }, { value: "churned", label: "Churned" }]} /></Field>
              <Field label="Payment terms"><Input value={form.payment_terms} onChange={(v) => setForm({ ...form, payment_terms: v })} placeholder="Net 30" /></Field>
            </div>
            <div className="form-row">
              <Field label="Email"><Input value={form.email} onChange={(v) => setForm({ ...form, email: v })} placeholder="jane@acme.com" type="email" /></Field>
              <Field label="Phone"><Input value={form.phone} onChange={(v) => setForm({ ...form, phone: v })} /></Field>
            </div>
            <Field label="Contract notes"><Textarea value={form.contract_notes} onChange={(v) => setForm({ ...form, contract_notes: v })} rows={3} /></Field>
            <Field label="Internal notes"><Textarea value={form.notes} onChange={(v) => setForm({ ...form, notes: v })} rows={3} /></Field>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
