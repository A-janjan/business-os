// Formatters.
export function money(amount: number | string | null | undefined, currency = "USD"): string {
  const n = typeof amount === "string" ? Number(amount) : amount ?? 0;
  const amt = Number.isFinite(n as number) ? (n as number) : 0;
  return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 2 }).format(amt);
}

export function dateStr(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

export function dateTimeStr(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function relativeTime(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  const diffMs = Date.now() - d.getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return dateStr(value);
}

export function initials(name: string): string {
  return (name || "?")
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

export function statusBadgeTone(status: string): "success" | "warning" | "danger" | "neutral" | "info" {
  const s = status.toLowerCase();
  if (["done", "completed", "paid", "published", "success", "approved", "active"].includes(s)) return "success";
  if (["todo", "pending", "draft", "review", "scheduled", "idea", "sent", "on_hold", "in_progress", "queued", "running"].includes(s)) return "warning";
  if (["overdue", "failed", "error", "churned", "cancelled", "void", "blocked", "rejected"].includes(s)) return "danger";
  if (["inactive", "archived", "cancelled"].includes(s)) return "neutral";
  return "info";
}
