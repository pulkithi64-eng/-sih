// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, request, requestBlob, session, UNAUTHORIZED_EVENT } from "../lib/api";

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); session.clear(); });

describe("API transport", () => {
  it("sends auth and a request ID, preserving cancellation", async () => {
    session.set("synthetic-token", {} as never);
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true }), { headers: { "content-type": "application/json" } }));
    vi.stubGlobal("fetch", fetcher);
    const controller = new AbortController();
    expect(await request("/health", { signal: controller.signal })).toEqual({ ok: true });
    expect(fetcher.mock.calls[0][1].headers.Authorization).toBe("Bearer synthetic-token");
    expect(fetcher.mock.calls[0][1].headers["X-Request-ID"]).toBeTruthy();
    expect(fetcher.mock.calls[0][1].signal).toBe(controller.signal);
  });
  it("clears expired credentials and exposes trace ID", async () => {
    session.set("expired", {} as never);
    const listener = vi.fn();
    window.addEventListener(UNAUTHORIZED_EVENT, listener);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Expired" }), { status: 401, headers: { "X-Request-ID": "trace-1234" } })));
    await expect(request("/applications")).rejects.toMatchObject({ status: 401, requestId: "trace-1234" });
    expect(session.getToken()).toBeNull();
    expect(listener).toHaveBeenCalledOnce();
    window.removeEventListener(UNAUTHORIZED_EVENT, listener);
  });
  it("preserves AbortError and reports network outages", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new DOMException("Aborted", "AbortError")));
    await expect(requestBlob("/documents/1/file")).rejects.toMatchObject({ name: "AbortError" });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Offline")));
    await expect(request("/applications")).rejects.toBeInstanceOf(ApiError);
  });
});
