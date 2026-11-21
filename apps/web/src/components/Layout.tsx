import React, { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

interface NavItem { to: string; label: string; icon: string; end?: boolean }
const NAV: { section: string; items: NavItem[] }[] = [
  { section: "Overview", items: [
    { to: "/", label: "Dashboard", icon: "▦", end: true },
  ]},
  { section: "Business", items: [
    { to: "/clients", label: "Clients", icon: "◈", end: false },
    { to: "/projects", label: "Projects", icon: "◉" },
    { to: "/tasks", label: "Tasks", icon: "✓" },
  ]},
  { section: "Knowledge", items: [
    { to: "/knowledge", label: "Knowledge Base", icon: "▤" },
    { to: "/notes", label: "Daily Notes", icon: "✎" },
  ]},
  { section: "Operations", items: [
    { to: "/content", label: "Content Studio", icon: "✦" },
    { to: "/finance", label: "Finance", icon: "◔" },
    { to: "/research", label: "Research", icon: "⌕" },
  ]},
  { section: "Intelligence", items: [
    { to: "/reports", label: "Reports", icon: "◈" },
    { to: "/ai", label: "AI Agents", icon: "❖" },
    { to: "/automation", label: "Automations", icon: "⚙" },
  ]},
  { section: "System", items: [
    { to: "/settings", label: "Settings", icon: "⌘" },
  ]},
];

const TITLES: Record<string, { title: string; sub: string }> = {
  "/": { title: "Dashboard", sub: "What is happening right now, and what needs your attention" },
  "/clients": { title: "Clients", sub: "Relationships, revenue, payment terms" },
  "/projects": { title: "Projects", sub: "Active work, milestones, deadlines" },
  "/tasks": { title: "Tasks", sub: "What to do, when, and why" },
  "/knowledge": { title: "Knowledge Base", sub: "Obsidian-compatible Markdown vault" },
  "/notes": { title: "Daily Notes", sub: "Journal, structured extraction, work history" },
  "/content": { title: "Content Studio", sub: "Ideas, drafts, publishing status" },
  "/finance": { title: "Finance", sub: "Income, expenses, invoices" },
  "/research": { title: "Research", sub: "Market, competitors, strategic notes" },
  "/reports": { title: "Reports", sub: "Generated reviews and AI briefs" },
  "/ai": { title: "AI Agents", sub: "Specialized agents, executions, approval queue" },
  "/automation": { title: "Automations", sub: "n8n workflows and execution history" },
  "/settings": { title: "Settings", sub: "Configuration and account" },
};

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const key = "/" + location.pathname.split("/").filter(Boolean)[0];
  const meta = TITLES[key] || { title: "Business OS", sub: "" };

  useEffect(() => { setMobileOpen(false); }, [location.pathname]);

  return (
    <div className="app-shell">
      <aside className={`app-sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-logo">B</div>
          <div>
            <div className="brand-name">Business OS</div>
            <div className="brand-sub">Obsidian · FastAPI · n8n</div>
          </div>
        </div>
        <nav className="app-nav" aria-label="Primary">
          {NAV.map((group) => (
            <div key={group.section}>
              <div className="app-nav-group">{group.section}</div>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) => `app-nav-item ${isActive ? "active" : ""}`}
                >
                  <span>{item.icon}</span><span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="subtle" style={{ marginBottom: 10 }}>
            {user?.name || user?.email}
            <div className="text-xs">{user?.role}</div>
          </div>
          <button className="btn btn-ghost btn-sm" style={{ width: "100%" }} onClick={() => { logout(); navigate("/login"); }}>
            Sign out
          </button>
        </div>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <button className="btn btn-ghost btn-sm mobile-menu-btn" aria-label="Toggle menu" onClick={() => setMobileOpen((v) => !v)}>☰</button>
          <div>
            <div className="topbar-title">
              {meta.title}<span className="topbar-sub">{meta.sub}</span>
            </div>
          </div>
          <div style={{ marginLeft: "auto" }} />
          <div className="chip" style={{ background: "var(--success-soft)", color: "var(--success)", borderColor: "#bbf7d0" }}>● live</div>
        </header>
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
