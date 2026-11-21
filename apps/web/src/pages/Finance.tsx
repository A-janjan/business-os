import React, { useMemo, useState } from "react";
import { useFetch } from "../lib/hooks";
import { get, post, del, put } from "../lib/api";
import { PageHeader, Button, Modal, Field, Input, Select, Loading, ErrorBanner, StatusBadge, Table, EmptyState, StatCard } from "../components/ui";
import { money, dateStr } from "../lib/format";

interface Tx { id: string; kind: string; amount: number; currency: string; category: string; client_id: string | null; project_id: string | null; date: string; description: string }
interface Invoice { id: string; number: string; client_id: string | null; amount: number; currency: string; due_date: string | null; status: string; paid_date: string | null; description: string }
interface Summary { month: string; income: number; expenses: number; net: number; open_invoice_amount: number; overdue_invoices: number }

const EMPTY_TX = { kind: "income", amount: "", currency: "USD", category: "", client_id: "", project_id: "", date: "", description: "" };
const EMPTY_INV = { number: "", client_id: "", amount: "", currency: "USD", due_date: "", status: "draft", paid_date: "", description: "" };

export default function Finance() {
  const today = new Date();
  const [month, setMonth] = useState(today.toISOString().slice(0, 7));
  const [tab, setTab] = useState<"overview" | "transactions" | "invoices">("overview");
  const { data: txData, reload: reloadTx } = useFetch<{ items: Tx[] }>(`/api/finance/transactions?start=${month}-01&limit=200`);
  const { data: invData, reload: reloadInv } = useFetch<{ items: Invoice[]; overdue: number }>("/api/finance/invoices");
  const { data: summData, reload: reloadSumm } = useFetch<Summary>(`/api/finance/summary?month=${month}`);
  const reload = () => { reloadTx(); reloadInv(); reloadSumm(); };
  const { data: clients } = useFetch<{ items: Array<{ id: string; name: string }> }>("/api/clients/");

  const [txModal, setTxModal] = useState(false);
  const [invModal, setInvModal] = useState(false);
  const [txForm, setTxForm] = useState(EMPTY_TX as any);
  const [invForm, setInvForm] = useState(EMPTY_INV as any);
  const [err, setErr] = useState<string | null>(null);

  const transactions = txData?.items || [];
  const invoices = invData?.items || [];

  const saveTx = async () => {
    setErr(null);
    try {
      await post("/api/finance/transactions", {
        ...txForm,
        amount: Number(txForm.amount),
        client_id: txForm.client_id || null,
        project_id: txForm.project_id || null,
        date: txForm.date || new Date().toISOString().slice(0, 10),
      });
      setTxModal(false);
      setTxForm(EMPTY_TX as any);
      reloadTx(); reloadSumm(); reload();
    } catch (e: any) { setErr(e?.message || "Could not save transaction"); }
  };

  const saveInvoice = async () => {
    setErr(null);
    try {
      await post("/api/finance/invoices", {
        ...invForm, amount: Number(invForm.amount), client_id: invForm.client_id || null, due_date: invForm.due_date || null, paid_date: invForm.paid_date || null,
      });
      setInvModal(false);
      setInvForm(EMPTY_INV as any);
      reloadInv(); reloadSumm(); reload();
    } catch (e: any) { setErr(e?.message || "Could not save invoice"); }
  };

  const markPaid = async (i: Invoice) => {
    try {
      await put(`/api/finance/invoices/${i.id}`, { ...i, amount: i.amount, status: "paid", paid_date: new Date().toISOString().slice(0, 10) });
      reloadInv(); reload();
    } catch (e: any) { setErr(e?.message || "Failed"); }
  };

  const payTx = async (t: Tx) => {
    if (!window.confirm("Delete this transaction?")) return;
    try { await del(`/api/finance/transactions/${t.id}`); reloadTx(); reloadSumm(); reload(); } catch (e: any) { setErr(e?.message || "Failed"); }
  };

  return (
    <>
      <PageHeader title="Finance" subtitle="Income, expenses, invoices — decimal-accurate, multi-currency">
        <Input type="month" value={month} onChange={(v) => setMonth(v)} style={{ width: 170 }} />
      </PageHeader>
      {err ? <ErrorBanner message={err} onDismiss={() => setErr(null)} /> : null}
      <div className="tabs">
        {(["overview", "transactions", "invoices"] as const).map((t) => (
          <button key={t} className={`tab-btn ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>{t[0].toUpperCase() + t.slice(1)}</button>
        ))}
      </div>

      {tab === "overview" ? (
        <>
          <div className="stat-grid" style={{ marginBottom: 18 }}>
            <StatCard label="Income" value={money(summData?.income || 0)} detail={`${month}`} tone="primary" />
            <StatCard label="Expenses" value={money(summData?.expenses || 0)} detail={`${month}`} />
            <StatCard label="Net" value={money(summData?.net || 0)} detail="income minus expenses" tone="primary" />
            <StatCard label="Open invoices" value={money(summData?.open_invoice_amount || 0)} detail={`${summData?.overdue_invoices || 0} overdue`} />
          </div>
          <div className="grid-2">
            <section className="card card-pad">
              <div className="between" style={{ marginBottom: 12 }}>
                <h3 style={{ fontSize: 16 }}>Recent transactions</h3>
                <Button size="sm" onClick={() => setTxModal(true)}>＋ Add</Button>
              </div>
              {transactions.slice(0, 6).map((t) => (
                <div key={t.id} className="between" style={{ padding: "9px 0", borderBottom: "1px dashed var(--border)" }}>
                  <div><div className="text-sm" style={{ fontWeight: 650 }}>{t.description || t.category || "Transaction"}</div><div className="text-xs">{t.category} · {dateStr(t.date)}</div></div>
                  <span style={{ fontWeight: 750, color: t.kind === "income" ? "var(--success)" : "var(--danger)" }}>{t.kind === "income" ? "+" : "−"}{money(t.amount, t.currency)}</span>
                </div>
              ))}
              {transactions.length === 0 ? <EmptyState title="No transactions yet" detail="Record income or expenses to see them here." /> : null}
            </section>
            <section className="card card-pad">
              <div className="between" style={{ marginBottom: 12 }}>
                <h3 style={{ fontSize: 16 }}>Invoices due</h3>
                <Button size="sm" onClick={() => setInvModal(true)}>＋ Invoice</Button>
              </div>
              {invoices.slice(0, 6).map((i) => (
                <div key={i.id} className="between" style={{ padding: "9px 0", borderBottom: "1px dashed var(--border)" }}>
                  <div><div className="text-sm" style={{ fontWeight: 650 }}>{i.number}</div><div className="text-xs">{i.description || "—"} · due {dateStr(i.due_date)}</div></div>
                  <div className="flex" style={{ gap: 8 }}>
                    <span style={{ fontWeight: 750 }}>{money(i.amount, i.currency)}</span>
                    <StatusBadge status={i.status} />
                  </div>
                </div>
              ))}
              {invoices.length === 0 ? <EmptyState title="No invoices yet" detail="Create an invoice to track revenue." /> : null}
            </section>
          </div>
        </>
      ) : null}

      {tab === "transactions" ? (
        <>
          <Button size="sm" onClick={() => setTxModal(true)}>＋ Add transaction</Button>
          <div style={{ marginTop: 12 }}>
            <Table rowKey={(r: Tx) => r.id} rows={transactions}
              columns={[
                { key: "date", label: "Date", render: (t: Tx) => <span className="text-xs">{dateStr(t.date)}</span> },
                { key: "kind", label: "Kind", render: (t: Tx) => <StatusBadge status={t.kind} /> },
                { key: "description", label: "Description", render: (t: Tx) => <div><div className="text-sm">{t.description || t.category}</div></div> },
                { key: "amount", label: "Amount", render: (t: Tx) => <span style={{ fontWeight: 750 }}>{money(t.amount, t.currency)}</span> },
                { key: "actions", label: "", render: (t: Tx) => <Button size="sm" variant="danger" onClick={() => payTx(t)}>✕</Button> },
              ]}
            />
          </div>
        </>
      ) : null}

      {tab === "invoices" ? (
        <>
          <Button size="sm" onClick={() => setInvModal(true)}>＋ Add invoice</Button>
          <div style={{ marginTop: 12 }}>
            <Table rowKey={(r: Invoice) => r.id} rows={invoices}
              columns={[
                { key: "number", label: "Number", render: (i: Invoice) => <span className="mono">{i.number}</span> },
                { key: "client_id", label: "Client", render: (i: Invoice) => <span className="text-xs">{(clients?.items || []).find((c) => c.id === i.client_id)?.name || "—"}</span> },
                { key: "due_date", label: "Due", render: (i: Invoice) => <span className="text-xs">{dateStr(i.due_date)}</span> },
                { key: "amount", label: "Amount", render: (i: Invoice) => <span style={{ fontWeight: 750 }}>{money(i.amount, i.currency)}</span> },
                { key: "status", label: "Status", render: (i: Invoice) => <StatusBadge status={i.status} /> },
                { key: "actions", label: "", render: (i: Invoice) => (
                  i.status !== "paid" ? <Button size="sm" variant="secondary" onClick={() => markPaid(i)}>Mark paid</Button> : null
                )},
              ]}
            />
          </div>
        </>
      ) : null}

      {txModal ? (
        <Modal title="New transaction" subtitle="Record income or an expense" onClose={() => setTxModal(false)}
          footer={<><Button variant="secondary" onClick={() => setTxModal(false)}>Cancel</Button><Button onClick={saveTx}>Save</Button></>}>
          <div className="form-grid">
            <div className="form-row">
              <Field label="Kind"><Select value={txForm.kind} onChange={(v) => setTxForm({ ...txForm, kind: v })} options={[{ value: "income", label: "Income" }, { value: "expense", label: "Expense" }]} /></Field>
              <Field label="Amount" required><Input type="number" min="0" step="0.01" value={txForm.amount} onChange={(v) => setTxForm({ ...txForm, amount: v })} placeholder="500.00" autoFocus /></Field>
            </div>
            <div className="form-row">
              <Field label="Currency"><Input value={txForm.currency} onChange={(v) => setTxForm({ ...txForm, currency: v.toUpperCase() })} placeholder="USD" /></Field>
              <Field label="Category"><Input value={txForm.category} onChange={(v) => setTxForm({ ...txForm, category: v })} placeholder="Consulting" /></Field>
            </div>
            <div className="form-row">
              <Field label="Client"><Select value={txForm.client_id || ""} onChange={(v) => setTxForm({ ...txForm, client_id: v })} placeholder="No client" options={(clients?.items || []).map((c) => ({ value: c.id, label: c.name }))} /></Field>
              <Field label="Date"><Input type="date" value={txForm.date || ""} onChange={(v) => setTxForm({ ...txForm, date: v })} /></Field>
            </div>
            <Field label="Description"><Input value={txForm.description} onChange={(v) => setTxForm({ ...txForm, description: v })} placeholder="Invoice A-102" /></Field>
          </div>
        </Modal>
      ) : null}

      {invModal ? (
        <Modal title="New invoice" subtitle="Track a receivable" onClose={() => setInvModal(false)}
          footer={<><Button variant="secondary" onClick={() => setInvModal(false)}>Cancel</Button><Button onClick={saveInvoice}>Save</Button></>}>
          <div className="form-grid">
            <div className="form-row">
              <Field label="Number" required><Input value={invForm.number} onChange={(v) => setInvForm({ ...invForm, number: v })} placeholder="INV-1001" autoFocus /></Field>
              <Field label="Amount" required><Input type="number" min="0" step="0.01" value={invForm.amount} onChange={(v) => setInvForm({ ...invForm, amount: v })} placeholder="1000.00" /></Field>
            </div>
            <div className="form-row">
              <Field label="Client"><Select value={invForm.client_id || ""} onChange={(v) => setInvForm({ ...invForm, client_id: v })} placeholder="No client" options={(clients?.items || []).map((c) => ({ value: c.id, label: c.name }))} /></Field>
              <Field label="Status"><Select value={invForm.status} onChange={(v) => setInvForm({ ...invForm, status: v })} options={["draft", "sent", "paid", "overdue", "void"].map((v) => ({ value: v, label: v }))} /></Field>
            </div>
            <div className="form-row">
              <Field label="Due date"><Input type="date" value={invForm.due_date || ""} onChange={(v) => setInvForm({ ...invForm, due_date: v })} /></Field>
              <Field label="Currency"><Input value={invForm.currency} onChange={(v) => setInvForm({ ...invForm, currency: v.toUpperCase() })} placeholder="USD" /></Field>
            </div>
            <Field label="Description"><Input value={invForm.description} onChange={(v) => setInvForm({ ...invForm, description: v })} placeholder="Consulting retainer" /></Field>
          </div>
        </Modal>
      ) : null}
    </>
  );
}
