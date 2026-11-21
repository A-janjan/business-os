import React, { useMemo } from "react";
import { useFetch } from "../lib/hooks";
import { StatCard, Loading, EmptyState, PageHeader, Progress, StatusBadge } from "../components/ui";
import { money, relativeTime, dateStr } from "../lib/format";
import { Link } from "react-router-dom";

interface Summary {
  today: string;
  active_projects: number;
  active_clients: number;
  pending_tasks: number;
  overdue_tasks: number;
  month_income: number;
  month_expense: number;
  month_net: number;
  upcoming_tasks: Array<{ id: string; title: string; priority: string; due_date: string | null; status: string }>;
  upcoming_deadlines: Array<{ id: string; name: string; deadline: string; days_left: number }>;
  overdue_invoices: Array<{ id: string; number: string; amount: number; currency: string; due_date: string | null }>;
  recent_activity: Array<{ id: string; actor: string; summary: string; entity_type: string; created_at: string }>;
  recent_ai_executions: Array<{ id: string; agent: string; status: string; created_at: string }>;
}

export default function Dashboard() {
  const { data, loading, error, reload } = useFetch<Summary>("/api/dashboard/summary");

  const urgency = useMemo(() => {
    if (!data) return "";
    const parts: string[] = [];
    if (data.overdue_tasks > 0) parts.push(`${data.overdue_tasks} overdue task${data.overdue_tasks > 1 ? "s" : ""}`);
    if (data.overdue_invoices.length > 0) parts.push(`${data.overdue_invoices.length} overdue invoice${data.overdue_invoices.length > 1 ? "s" : ""}`);
    return parts.join(" · ");
  }, [data]);

  if (loading) return <Loading />;
  if (error || !data) return <div className="card card-pad"><EmptyState icon="⚠" title="Couldn’t load dashboard" detail={error || "Unknown error"} /></div>;

  return (
    <>
      <PageHeader title="Welcome back" subtitle={`${new Date(data.today).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })} — money in: ${money(data.month_income)} · tasks pending: ${data.pending_tasks}`}>
        <Link to="/tasks" className="btn btn-primary">Open tasks</Link>
      </PageHeader>

      {urgency ? <div className="info-banner" style={{ marginBottom: 18 }}>⚠ <strong>Needs attention:</strong> {urgency}</div> : null}

      <div className="stat-grid" style={{ marginBottom: 18 }}>
        <StatCard label="Active projects" value={data.active_projects} detail="in progress" tone="primary" />
        <StatCard label="Pending tasks" value={data.pending_tasks} detail={data.overdue_tasks > 0 ? `${data.overdue_tasks} overdue` : "none overdue"} />
        <StatCard label="Active clients" value={data.active_clients} detail="in good standing" />
        <StatCard label="Net this month" value={money(data.month_net)} detail={`Income ${money(data.month_income)} · Expenses ${money(data.month_expense)}`} tone={data.month_net >= 0 ? "primary" : undefined} />
      </div>

      <div className="grid-sidebar">
        <div style={{ display: "grid", gap: 18 }}>
          <section className="card card-pad">
            <div className="between" style={{ marginBottom: 12 }}>
              <div><h3 style={{ fontSize: 16 }}>Upcoming tasks</h3><div className="subtle">{data.upcoming_tasks.length} scheduled</div></div>
              <Link to="/tasks" className="link">View all</Link>
            </div>
            {data.upcoming_tasks.length === 0 ? <p className="subtle" style={{ margin: 0 }}>Nothing due soon. Enjoy the calm.</p> : (
              <ul className="nowrap-list">
                {data.upcoming_tasks.map((t) => (
                  <li key={t.id}>
                    <StatusBadge status={t.status} />
                    <span style={{ flex: 1 }}>{t.title}</span>
                    <span className="text-xs">{t.due_date ? dateStr(t.due_date) : "no due date"}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card card-pad">
            <div className="between" style={{ marginBottom: 12 }}>
              <h3 style={{ fontSize: 16 }}>Upcoming deadlines</h3>
              <Link to="/projects" className="link">Projects</Link>
            </div>
            {data.upcoming_deadlines.length === 0 ? <p className="subtle" style={{ margin: 0 }}>No deadlines in the near term.</p> : (
              <ul className="nowrap-list">
                {data.upcoming_deadlines.map((p) => (
                  <li key={p.id}>
                    <div style={{ flex: 1 }}>{p.name}</div>
                    <span className={p.days_left <= 3 ? "risk-pill" : "text-xs"}>
                      {p.days_left <= 0 ? "due today" : p.days_left === 1 ? "1 day left" : `${p.days_left} days left`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card card-pad">
            <div className="between" style={{ marginBottom: 12 }}>
              <h3 style={{ fontSize: 16 }}>Recent activity</h3>
              <Link to="/notes" className="link">Daily notes</Link>
            </div>
            {data.recent_activity.length === 0 ? <p className="subtle" style={{ margin: 0 }}>No activity yet.</p> : (
              <div className="timeline">
                {data.recent_activity.map((a) => (
                  <div key={a.id} className="timeline-item">
                    <div className="t"><span className="text-xs" style={{ color: "var(--text)", fontWeight: 700, marginRight: 6 }}>{a.actor.toUpperCase()}</span>{a.summary}</div>
                    <div className="when">{relativeTime(a.created_at)}</div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>

        <aside style={{ display: "grid", gap: 18, alignContent: "start" }}>
          <section className="card card-pad">
            <h3 style={{ fontSize: 16, marginBottom: 12 }}>Finance snapshot</h3>
            <div className="subtle">Income</div>
            <div className="text-sm" style={{ fontWeight: 700, marginBottom: 10 }}>{money(data.month_income)}</div>
            <div className="subtle">Expenses</div>
            <div className="text-sm" style={{ fontWeight: 700, marginBottom: 10 }}>{money(data.month_expense)}</div>
            <div className="divider" />
            <div className="between"><span className="subtle">Net</span><span style={{ fontWeight: 750, color: data.month_net >= 0 ? "var(--success)" : "var(--danger)" }}>{money(data.month_net)}</span></div>
            {data.overdue_invoices.length > 0 ? (
              <>
                <div className="divider" />
                <div className="subtle">Overdue invoices</div>
                {data.overdue_invoices.map((i) => (
                  <div key={i.id} className="between text-xs" style={{ marginTop: 6 }}>
                    <span style={{ fontWeight: 700 }}>{i.number}</span>
                    <span>{money(i.amount, i.currency)}</span>
                  </div>
                ))}
              </>
            ) : null}
            <Link to="/finance" className="link" style={{ marginTop: 12, display: "inline-block" }}>Open finance →</Link>
          </section>

          <section className="card card-pad">
            <div className="between" style={{ marginBottom: 12 }}>
              <h3 style={{ fontSize: 16 }}>AI activity</h3>
              <Link to="/ai" className="link">Agents</Link>
            </div>
            {data.recent_ai_executions.length === 0 ? <p className="subtle" style={{ margin: 0 }}>No executions yet.</p> : (
              <ul className="nowrap-list" style={{ gap: 8 }}>
                {data.recent_ai_executions.map((e) => (
                  <li key={e.id} className="between">
                    <span className="text-xs" style={{ fontWeight: 650 }}>{e.agent}</span>
                    <StatusBadge status={e.status} />
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card card-pad">
            <h3 style={{ fontSize: 16, marginBottom: 10 }}>Do you need it?</h3>
            <p className="subtle">The daily brief, weekly review, and AI agents live in <Link to="/reports" className="link">Reports</Link>. Human-in-the-loop approvals gate consequential actions.</p>
          </section>
        </aside>
      </div>
    </>
  );
}
