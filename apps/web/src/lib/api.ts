// Thin fetch wrapper around the backend. All paths are relative (/api/...).
const TOKEN_KEY = "bo_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export interface ApiError extends Error {
  status?: number;
}

export async function api<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(path, { ...options, headers });
  const text = await res.text();
  const data = text ? safeJson(text) : null;

  if (!res.ok) {
    const issue: ApiError = new Error(
      (data && (data.detail || data.message)) || `Request failed (${res.status})`,
    );
    issue.status = res.status;
    throw issue;
  }
  return data as T;
}

function safeJson(text: string): any {
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

export function get<T = unknown>(path: string): Promise<T> {
  return api<T>(path, { method: "GET" });
}

export function post<T = unknown>(path: string, body?: unknown): Promise<T> {
  return api<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
}

export function put<T = unknown>(path: string, body: unknown): Promise<T> {
  return api<T>(path, { method: "PUT", body: JSON.stringify(body) });
}

export function patch<T = unknown>(path: string, body: unknown): Promise<T> {
  return api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
}

export function del(path: string): Promise<void> {
  return api<void>(path, { method: "DELETE" });
}
