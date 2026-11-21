import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./lib/auth";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Clients from "./pages/Clients";
import Projects from "./pages/Projects";
import Tasks from "./pages/Tasks";
import Knowledge from "./pages/Knowledge";
import DailyNotes from "./pages/DailyNotes";
import ContentStudio from "./pages/Content";
import Finance from "./pages/Finance";
import Research from "./pages/Research";
import Reports from "./pages/Reports";
import AIAgents from "./pages/AIAgents";
import Automations from "./pages/Automations";
import Settings from "./pages/Settings";

function FullScreen({ children }: { children: React.ReactNode }) {
  return <div style={{ minHeight: "100vh" }}>{children}</div>;
}

function Protected() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && !user) navigate("/login", { replace: true });
  }, [loading, user, navigate]);

  if (loading) {
    return <FullScreen><div className="loading-state" style={{ minHeight: "100vh" }}><div className="spinner" /></div></FullScreen>;
  }
  if (!user) return null;
  return <Layout />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={<Protected />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/clients" element={<Clients />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/knowledge" element={<Knowledge />} />
            <Route path="/notes" element={<DailyNotes />} />
            <Route path="/content" element={<ContentStudio />} />
            <Route path="/finance" element={<Finance />} />
            <Route path="/research" element={<Research />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/ai" element={<AIAgents />} />
            <Route path="/automation" element={<Automations />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
