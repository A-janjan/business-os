import React, { useState, useEffect } from "react";
import { statusBadgeTone } from "../lib/format";

// ---------- Buttons ----------
export function Button({ children, variant = "primary", size, loading, onClick, type = "button", disabled, title }: {
  children: React.ReactNode; variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "lg"; loading?: boolean; onClick?: () => void; type?: "button" | "submit";
  disabled?: boolean; title?: string;
}) {
  const cls = ["btn", `btn-${variant}`, size === "sm" ? "btn-sm" : "", size === "lg" ? "btn-lg" : "", loading ? "loading" : ""].filter(Boolean).join(" ");
  return (
    <button type={type} className={cls} title={title} disabled={disabled || loading} onClick={onClick}>
      {loading ? <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> : children}
    </button>
  );
}

// ---------- Badges ----------
export function StatusBadge({ status }: { status: string }) {
  const tone = statusBadgeTone(status);
  return <span className={`badge badge-${tone}`}>{status.replace(/_/g, " ")}</span>;
}

export function Chip({ children }: { children: React.ReactNode }) {
  return <span className="chip">{children}</span>;
}

// ---------- Cards ----------
export function StatCard({ label, value, detail, tone }: { label: string; value: string | number; detail?: string; tone?: "primary" | "danger" }) {
  const color = tone === "primary" ? "accent" : "";
  return (
    <div className="card stat-card">
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${color}`}>{value}</div>
      {detail ? <div className="stat-detail">{detail}</div> : null}
    </div>
  );
}

// ---------- Modal ----------
export function Modal({ title, subtitle, onClose, children, footer, wide }: {
  title: string; subtitle?: string; onClose: () => void; children: React.ReactNode; footer?: React.ReactNode; wide?: boolean;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-label={title}>
      <div className="modal" style={wide ? { maxWidth: 780 } : undefined} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <div className="modal-title">{title}</div>
            {subtitle ? <div className="modal-sub">{subtitle}</div> : null}
          </div>
          <button className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="modal-body">{children}</div>
        {footer ? <div className="modal-footer">{footer}</div> : null}
      </div>
    </div>
  );
}

// ---------- Forms ----------
export function Field({ label, children, hint, required }: { label?: string; children: React.ReactNode; hint?: string; required?: boolean }) {
  return (
    <label className="field">
      {label ? <span>{label}{required ? " *" : ""}</span> : null}
      {children}
      {hint ? <span className="help">{hint}</span> : null}
    </label>
  );
}

export function Input({ value, onChange, placeholder, type = "text", min, max, step, autoFocus, style, ...rest }: {
  value: string; onChange: (v: string) => void; placeholder?: string; type?: string; min?: string; max?: string; step?: string; autoFocus?: boolean; style?: React.CSSProperties;
} & Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange" | "value" | "style">) {
  return (
    <input
      type={type}
      className="input"
      style={style}
      value={value}
      autoFocus={autoFocus}
      min={min} max={max} step={step}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
      {...rest}
    />
  );
}

export function Textarea({ value, onChange, placeholder, rows = 5, mono }: {
  value: string; onChange: (v: string) => void; placeholder?: string; rows?: number; mono?: boolean;
}) {
  return (
    <textarea
      className={mono ? "editor" : "textarea"}
      value={value}
      rows={rows}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

export function Select({ value, onChange, options, placeholder, style }: {
  value: string; onChange: (v: string) => void; options: { value: string; label: string }[]; placeholder?: string; style?: React.CSSProperties;
}) {
  return (
    <select className="select" style={style} value={value} onChange={(e) => onChange(e.target.value)}>
      {placeholder ? <option value="">{placeholder}</option> : null}
      {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}

// ---------- Table ----------
export function Table({ columns, rows, empty = "Nothing here yet.", rowKey }: {
  columns: { key: string; label: string; render?: (row: any) => React.ReactNode; className?: string }[];
  rows: any[]; empty?: string; rowKey: (row: any) => string;
}) {
  if (!rows || rows.length === 0) {
    return <div className="table-wrap"><div className="table-empty">{empty}</div></div>;
  }
  return (
    <div className="table-wrap">
      <table className="data">
        <thead>
          <tr>{columns.map((c) => <th key={c.key} className={c.className}>{c.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={rowKey(row) || i}>
              {columns.map((c) => <td key={c.key} className={c.className}>{c.render ? c.render(row) : row[c.key]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------- states ----------
export function Loading() {
  return <div className="loading-state"><div className="spinner" /><div>Loading…</div></div>;
}

export function EmptyState({ icon = "✦", title, detail, action }: { icon?: string; title: string; detail?: string; action?: React.ReactNode }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon}</div>
      <h3>{title}</h3>
      {detail ? <p className="subtle">{detail}</p> : null}
      {action ? <div style={{ marginTop: 14 }}>{action}</div> : null}
    </div>
  );
}

export function ErrorBanner({ message, onDismiss }: { message: string; onDismiss?: () => void }) {
  return (
    <div className="error-banner" role="alert">
      <span>⚠</span>
      <span style={{ flex: 1 }}>{message}</span>
      {onDismiss ? <button className="btn btn-ghost btn-sm" onClick={onDismiss}>Dismiss</button> : null}
    </div>
  );
}

// ---------- Page header ----------
export function PageHeader({ title, subtitle, children }: { title: string; subtitle?: string; children?: React.ReactNode }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {subtitle ? <div className="sub">{subtitle}</div> : null}
      </div>
      {children ? <div className="actions">{children}</div> : null}
    </div>
  );
}

// ---------- Progress ----------
export function Progress({ value, tone = "primary" }: { value: number; tone?: "primary" | "danger" }) {
  return (
    <div className="progress" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100} style={{ width: "100%" }}>
      <span style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: tone === "danger" ? "var(--danger)" : undefined }} />
    </div>
  );
}
