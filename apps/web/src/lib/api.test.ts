import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { getToken, setToken, api } from "./api";

describe("api", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
  });
  afterEach(() => vi.unstubAllGlobals());

  it("returns parsed JSON on success", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    const data = await api<{ ok: boolean }>("/api/health");
    expect(data.ok).toBe(true);
  });

  it("attaches the bearer token when present", async () => {
    setToken("test-token");
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));
    await api("/api/me");
    const headers = vi.mocked(fetch).mock.calls[0][1]?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer test-token");
  });

  it("throws an Error with detail on failure", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ detail: "boom" }), { status: 422 }));
    await expect(api("/api/x")).rejects.toThrow("boom");
  });
});
