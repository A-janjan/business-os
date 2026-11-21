import React, { useState } from "react";
import { useAuth } from "../lib/auth";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { Button, Input, Field, ErrorBanner } from "../components/ui";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "register") {
        await api("/api/auth/register", {
          method: "POST",
          body: JSON.stringify({ email, password, name }),
        });
        await login(email, password);
      } else {
        await login(email, password);
      }
      navigate("/", { replace: true });
    } catch (err: any) {
      setError(err?.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="landing">
      <div className="landing-card card card-pad">
        <div className="mark">B</div>
        <h1>Business OS</h1>
        <p>A personal business operating system — knowledge, clients, projects, tasks, content, finance, and AI agents in one place.</p>

        {error ? <ErrorBanner message={error} onDismiss={() => setError(null)} /> : null}

        <form onSubmit={submit}>
          {mode === "register" ? (
            <Field label="Name">
              <Input value={name} onChange={setName} placeholder="Your name" autoFocus />
            </Field>
          ) : null}
          <Field label="Email" required>
            <Input value={email} onChange={setEmail} placeholder="you@example.com" type="email" autoFocus={mode === "login"} />
          </Field>
          <Field label="Password" required hint="At least 8 characters. The first registration becomes the admin.">
            <Input value={password} onChange={setPassword} placeholder="••••••••" type="password" />
          </Field>
          <Button type="submit" variant="primary" loading={loading} size="lg">
            {mode === "register" ? "Create account" : "Sign in"}
          </Button>
        </form>

        <div className="divider" />
        <button className="btn btn-ghost" style={{ width: "100%" }} onClick={() => { setMode(mode === "register" ? "login" : "register"); setError(null); }}>
          {mode === "register" ? "Already have an account? Sign in" : "First time? Create the admin account"}
        </button>
        <p className="help" style={{ textAlign: "center", marginTop: 10 }}>
          Registration is available only until the first admin account exists.
        </p>
      </div>
    </div>
  );
}
