/**
 * Test helpers: render components with routing + a real AuthProvider whose
 * network calls are stubbed with `vi.spyOn(api, ...)` in each test.
 */

import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { ChakraProvider, defaultSystem } from "@chakra-ui/react";
import { AuthProvider } from "../auth/AuthContext";
import type { User } from "../api/types";

export const mockUser: User = {
  id: 1,
  email: "asha@example.com",
  full_name: "Asha Verma",
  target_role: "Data Analyst",
  experience_level: "fresher",
  created_at: "2026-09-10T12:00:00",
};

export const mockTokens = {
  token_type: "bearer" as const,
  access_token: "access-token",
  refresh_token: "refresh-token",
  expires_in: 1800,
};

export interface RenderOptions {
  route?: string;
  withUser?: boolean;
}

export function renderWithProviders(ui: ReactNode, options: RenderOptions = {}) {
  const { route = "/", withUser = false } = options;
  if (withUser) {
    localStorage.setItem("pragatishala.access_token", "access-token");
    localStorage.setItem("pragatishala.refresh_token", "refresh-token");
  }
  return render(
    <ChakraProvider value={defaultSystem}>
      <MemoryRouter initialEntries={[route]}>
        <AuthProvider>{ui}</AuthProvider>
      </MemoryRouter>
    </ChakraProvider>,
  );
}
