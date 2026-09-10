/**
 * Minimal typed HTTP client for the PragatiShala API.
 *
 * - Base URL defaults to a relative `/api/v1` (the Vite dev server proxies it
 *   to FastAPI — see `vite.config.ts`); override with `VITE_API_BASE_URL`.
 * - Access tokens are attached automatically; on a 401 the client tries one
 *   refresh round-trip before giving up so short access tokens stay invisible
 *   to users.
 */

import type { Assessment, LearningPath, TokenPair, User } from "./types";

export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

const ACCESS_KEY = "pragatishala.access_token";
const REFRESH_KEY = "pragatishala.refresh_token";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(tokens: Pick<TokenPair, "access_token" | "refresh_token">): void {
  localStorage.setItem(ACCESS_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

function headersWithAuth(extra?: HeadersInit): HeadersInit {
  const token = getAccessToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

async function readError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    const detail = body.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      // FastAPI validation errors: prefer the first human-readable message.
      const first = detail[0] as { msg?: string } | undefined;
      if (first?.msg) return first.msg;
    }
  } catch {
    // fall through to generic message
  }
  return `Request failed with status ${response.status}`;
}

async function request<T>(
  path: string,
  init: RequestInit & { auth?: boolean },
  allowRefresh: boolean,
): Promise<T> {
  const headers =
    init.auth === false
      ? { "Content-Type": "application/json", ...init.headers }
      : headersWithAuth(init.headers);
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });

  if (response.status === 401 && allowRefresh && getRefreshToken()) {
    const refreshed = await tryRefresh();
    if (refreshed) return request<T>(path, init, false);
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readError(response));
  }
  return (await response.json()) as T;
}

async function tryRefresh(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) {
      clearTokens();
      return false;
    }
    setTokens((await response.json()) as TokenPair);
    return true;
  } catch {
    return false;
  }
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string;
  target_role?: string | null;
  experience_level?: string | null;
}

export const api = {
  register(payload: RegisterPayload): Promise<User> {
    return request<User>(
      "/auth/register",
      { method: "POST", body: JSON.stringify(payload), auth: false },
      false,
    );
  },

  /** OAuth2 password flow: the backend expects form-encoded credentials. */
  login(email: string, password: string): Promise<TokenPair> {
    const form = new URLSearchParams({ username: email, password });
    return request<TokenPair>(
      "/auth/login",
      {
        method: "POST",
        body: form.toString(),
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        auth: false,
      },
      false,
    );
  },

  me(): Promise<User> {
    return request<User>("/auth/me", { method: "GET" }, true);
  },

  updateProfile(
    payload: Partial<Pick<User, "full_name" | "target_role" | "experience_level">>,
  ): Promise<User> {
    return request<User>("/users/me", { method: "PATCH", body: JSON.stringify(payload) }, true);
  },

  runAssessment(inputText: string, targetRole: string | null): Promise<Assessment> {
    return request<Assessment>(
      "/assessments",
      { method: "POST", body: JSON.stringify({ input_text: inputText, target_role: targetRole }) },
      true,
    );
  },

  generateLearningPath(assessmentId: number | null): Promise<LearningPath> {
    return request<LearningPath>(
      "/learning-paths/generate",
      {
        method: "POST",
        body: JSON.stringify(assessmentId ? { assessment_id: assessmentId } : {}),
      },
      true,
    );
  },
};
