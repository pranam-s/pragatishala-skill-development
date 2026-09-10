/**
 * Authentication context: session bootstrap, login, registration, logout.
 *
 * Tokens live in localStorage. This keeps sessions alive across reloads for a
 * local-first SPA; the trade-off (readable by JS in the page) is accepted for
 * this MVP because the API is same-machine in development. Documented in
 * docs/adr/0002-authentication.md.
 */

/* eslint-disable react-refresh/only-export-components -- provider and hook form one cohesive auth module */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api, clearTokens, getAccessToken, setTokens } from "../api/client";
import type { RegisterPayload } from "../api/client";
import type { User } from "../api/types";

interface AuthState {
  user: User | null;
  /** True until the stored token (if any) has been checked once. */
  initializing: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (payload: RegisterPayload) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [initializing, setInitializing] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      if (!getAccessToken()) {
        setInitializing(false);
        return;
      }
      try {
        const me = await api.me();
        if (!cancelled) setUser(me);
      } catch {
        clearTokens();
      } finally {
        if (!cancelled) setInitializing(false);
      }
    }
    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await api.login(email, password);
    setTokens(tokens);
    const me = await api.me();
    setUser(me);
    return me;
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    const created = await api.register(payload);
    // Log the freshly created user in so they land on their dashboard.
    const tokens = await api.login(payload.email, payload.password);
    setTokens(tokens);
    const me = await api.me();
    setUser(me);
    return created;
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  const value = useMemo<AuthState>(
    () => ({ user, initializing, login, register, logout }),
    [user, initializing, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return context;
}
