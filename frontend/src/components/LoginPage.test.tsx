import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "../api/client";
import { mockTokens, mockUser, renderWithProviders } from "../test/helpers";
import LoginPage from "./LoginPage";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("LoginPage", () => {
  it("renders labelled, focusable form controls", () => {
    renderWithProviders(<LoginPage />, { route: "/login" });
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("performs the login flow and stores the issued tokens", async () => {
    const user = userEvent.setup();
    const loginSpy = vi.spyOn(api, "login").mockResolvedValue(mockTokens);
    const meSpy = vi.spyOn(api, "me").mockResolvedValue(mockUser);

    renderWithProviders(<LoginPage />, { route: "/login" });

    await user.type(screen.getByLabelText(/email address/i), "asha@example.com");
    await user.type(screen.getByLabelText(/password/i), "super-secret-pass-123");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(loginSpy).toHaveBeenCalledWith("asha@example.com", "super-secret-pass-123");
    });
    await waitFor(() => {
      expect(meSpy).toHaveBeenCalled();
    });
    expect(localStorage.getItem("pragatishala.access_token")).toBe("access-token");
    expect(localStorage.getItem("pragatishala.refresh_token")).toBe("refresh-token");
  });

  it("announces failures in an alert region and re-enables the form", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "login").mockRejectedValue(new Error("incorrect email or password"));

    renderWithProviders(<LoginPage />, { route: "/login" });

    await user.type(screen.getByLabelText(/email address/i), "asha@example.com");
    await user.type(screen.getByLabelText(/password/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/incorrect email or password/i);
    expect(screen.getByRole("button", { name: /sign in/i })).toBeEnabled();
  });
});
