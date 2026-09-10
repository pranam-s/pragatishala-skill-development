import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { api } from "../api/client";
import { mockUser } from "../test/helpers";
import { ChakraProvider, defaultSystem } from "@chakra-ui/react";
import { AuthProvider, useAuth } from "../auth/AuthContext";
import ProtectedRoute from "../components/ProtectedRoute";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

function LogoutProbe() {
  const { user, logout } = useAuth();
  return (
    <div>
      <span>{user ? `user:${user.email}` : "anonymous"}</span>
      <button onClick={logout}>Log out</button>
    </div>
  );
}

describe("AuthContext", () => {
  it("starts anonymous when no tokens are stored", async () => {
    render(
      <AuthProvider>
        <LogoutProbe />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("anonymous")).toBeInTheDocument();
    });
  });

  it("restores the session from a stored token on mount", async () => {
    localStorage.setItem("pragatishala.access_token", "stored");
    localStorage.setItem("pragatishala.refresh_token", "stored-refresh");
    const meSpy = vi.spyOn(api, "me").mockResolvedValue(mockUser);

    render(
      <AuthProvider>
        <LogoutProbe />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText(`user:${mockUser.email}`)).toBeInTheDocument();
    });
    expect(meSpy).toHaveBeenCalled();
  });

  it("clears the session on logout", async () => {
    const user = userEvent.setup();
    localStorage.setItem("pragatishala.access_token", "stored");
    localStorage.setItem("pragatishala.refresh_token", "stored-refresh");
    vi.spyOn(api, "me").mockResolvedValue(mockUser);

    render(
      <AuthProvider>
        <LogoutProbe />
      </AuthProvider>,
    );
    await screen.findByText(`user:${mockUser.email}`);

    await user.click(screen.getByRole("button", { name: /log out/i }));

    expect(await screen.findByText("anonymous")).toBeInTheDocument();
    expect(localStorage.getItem("pragatishala.access_token")).toBeNull();
  });

  it("drops invalid stored tokens instead of failing forever", async () => {
    localStorage.setItem("pragatishala.access_token", "bad");
    localStorage.setItem("pragatishala.refresh_token", "bad");
    vi.spyOn(api, "me").mockRejectedValue(new Error("expired"));

    render(
      <AuthProvider>
        <LogoutProbe />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("anonymous")).toBeInTheDocument();
    });
    expect(localStorage.getItem("pragatishala.access_token")).toBeNull();
  });
});

describe("ProtectedRoute", () => {
  function renderAtRoute(route: string, element: React.ReactNode) {
    return render(
      <ChakraProvider value={defaultSystem}>
      <AuthProvider>
        <MemoryRouter initialEntries={[route]}>
          <Routes>
            <Route path="/login" element={<div>login page</div>} />
            <Route path="/assessment" element={element} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
      </ChakraProvider>,
    );
  }

  it("redirects anonymous visitors to /login", async () => {
    renderAtRoute(
      "/assessment",
      <ProtectedRoute>
        <div>secret</div>
      </ProtectedRoute>,
    );

    expect(await screen.findByText("login page")).toBeInTheDocument();
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });

  it("renders children for signed-in users", async () => {
    localStorage.setItem("pragatishala.access_token", "a");
    localStorage.setItem("pragatishala.refresh_token", "r");
    vi.spyOn(api, "me").mockResolvedValue(mockUser);

    renderAtRoute(
      "/assessment",
      <ProtectedRoute>
        <div>assessment content</div>
      </ProtectedRoute>,
    );

    expect(await screen.findByText("assessment content")).toBeInTheDocument();
  });
});

describe("useAuth guard", () => {
  it("throws a helpful error when used outside AuthProvider", () => {
    function Orphan() {
      useAuth();
      return null;
    }
    expect(() => render(<Orphan />)).toThrow(/useAuth must be used inside/i);
  });
});
