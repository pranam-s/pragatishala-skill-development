import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, clearTokens, setTokens } from "../api/client";

const jsonBody = (data: unknown, status = 200) =>
  Promise.resolve(
    new Response(JSON.stringify(data), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );

const mockUserBody = {
  id: 1,
  email: "x@y.com",
  full_name: "",
  target_role: null,
  experience_level: null,
  created_at: "now",
};

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("api client", () => {
  it("sends login credentials as an OAuth2 form", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() =>
        jsonBody({ token_type: "bearer", access_token: "a", refresh_token: "r", expires_in: 60 }),
      );

    const tokens = await api.login("me@example.com", "pw");

    expect(tokens.access_token).toBe("a");
    const [, init] = fetchSpy.mock.calls[0];
    expect(init?.method).toBe("POST");
    expect(String(init?.body)).toContain("username=me%40example.com");
    expect((init?.headers as Record<string, string>)["Content-Type"]).toBe(
      "application/x-www-form-urlencoded",
    );
  });

  it("attaches the bearer token to authenticated requests", async () => {
    setTokens({ access_token: "tok-1", refresh_token: "ref-1" });
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() => jsonBody(mockUserBody));

    await api.me();

    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe("/api/v1/auth/me");
    expect((init?.headers as Record<string, string>).Authorization).toBe("Bearer tok-1");
  });

  it("refreshes once on a 401 and retries the original request", async () => {
    setTokens({ access_token: "expired", refresh_token: "ref" });
    let meCalls = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return jsonBody({
          token_type: "bearer",
          access_token: "fresh",
          refresh_token: "ref2",
          expires_in: 60,
        });
      }
      meCalls += 1;
      if (meCalls === 1) {
        return Promise.resolve(new Response(JSON.stringify({ detail: "expired" }), { status: 401 }));
      }
      return jsonBody(mockUserBody);
    });

    const me = await api.me();

    expect(me.id).toBe(1);
    expect(localStorage.getItem("pragatishala.access_token")).toBe("fresh");
    expect(meCalls).toBe(2); // original + retry
  });

  it("surfaces FastAPI string detail messages as ApiError", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      jsonBody({ detail: "an account with a@b.com already exists" }, 409),
    );

    await expect(
      api.register({ email: "a@b.com", password: "password123" }),
    ).rejects.toMatchObject({ name: "ApiError", status: 409 });
  });

  it("uses the first validation message for 422 responses", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      jsonBody(
        { detail: [{ msg: "String should have at least 20 characters" }, { msg: "second" }] },
        422,
      ),
    );

    await expect(api.runAssessment("short", null)).rejects.toThrow(/at least 20 characters/);
  });

  it("clears tokens on logout", () => {
    setTokens({ access_token: "a", refresh_token: "r" });
    clearTokens();
    expect(localStorage.getItem("pragatishala.access_token")).toBeNull();
    expect(localStorage.getItem("pragatishala.refresh_token")).toBeNull();
    expect(new ApiError(400, "x").status).toBe(400);
  });
});

describe("api client error paths", () => {
  it("does not loop when the refresh request itself fails", async () => {
    setTokens({ access_token: "expired", refresh_token: "ref" });
    let meCalls = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return jsonBody({ detail: "invalid or expired refresh token" }, 401);
      }
      meCalls += 1;
      return Promise.resolve(new Response(JSON.stringify({ detail: "expired" }), { status: 401 }));
    });

    await expect(api.me()).rejects.toMatchObject({ status: 401 });
    expect(meCalls).toBe(1);
    expect(localStorage.getItem("pragatishala.access_token")).toBeNull();
  });

  it("keeps the original 401 when no refresh token exists", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      jsonBody({ detail: "not authenticated" }, 401),
    );

    await expect(api.me()).rejects.toThrow(/not authenticated/);
  });

  it("patches the profile with bearer auth", async () => {
    setTokens({ access_token: "tok", refresh_token: "ref" });
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(() => jsonBody({ ...mockUserBody, full_name: "New Name" }));

    const updated = await api.updateProfile({ full_name: "New Name" });

    expect(updated.full_name).toBe("New Name");
    const [url, init] = fetchSpy.mock.calls[0];
    expect(url).toBe("/api/v1/users/me");
    expect(init?.method).toBe("PATCH");
    expect(String(init?.body)).toContain("New Name");
  });

  it("keeps tokens when refresh fails transiently (network error)", async () => {
    setTokens({ access_token: "expired", refresh_token: "ref" });
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return Promise.reject(new TypeError("network down"));
      }
      return Promise.resolve(new Response(JSON.stringify({ detail: "expired" }), { status: 401 }));
    });

    // A network blip must NOT destroy the stored session.
    await expect(api.me()).rejects.toMatchObject({ status: 401 });
    expect(localStorage.getItem("pragatishala.refresh_token")).toBe("ref");
  });
});
