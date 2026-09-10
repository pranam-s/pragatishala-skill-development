import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "../api/client";
import { mockTokens, mockUser, renderWithProviders } from "../test/helpers";
import RegistrationPage from "./RegistrationPage";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

async function fillForm(user: ReturnType<typeof userEvent.setup>, password = "super-secret-pass-123") {
  // Sequential typing: concurrent userEvent typings race on re-renders.
  await user.type(screen.getByLabelText(/full name/i), "Asha Verma");
  await user.type(screen.getByLabelText(/email address/i), "asha@example.com");
  await user.type(screen.getByLabelText(/^password/i), password);
}

describe("RegistrationPage", () => {
  it("renders labelled form controls including optional fields", () => {
    renderWithProviders(<RegistrationPage />, { route: "/register" });
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/target role/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/experience level/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /create account/i }),
    ).toBeInTheDocument();
  });

  it("registers the account, signs the user in, and stores tokens", async () => {
    const user = userEvent.setup();
    const registerSpy = vi.spyOn(api, "register").mockResolvedValue(mockUser);
    const loginSpy = vi.spyOn(api, "login").mockResolvedValue(mockTokens);
    const meSpy = vi.spyOn(api, "me").mockResolvedValue(mockUser);

    renderWithProviders(<RegistrationPage />, { route: "/register" });

    await fillForm(user);
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => {
      expect(registerSpy).toHaveBeenCalledWith({
        email: "asha@example.com",
        password: "super-secret-pass-123",
        full_name: "Asha Verma",
        target_role: null,
        experience_level: null,
      });
    });
    expect(loginSpy).toHaveBeenCalledWith("asha@example.com", "super-secret-pass-123");
    await waitFor(() => {
      expect(meSpy).toHaveBeenCalled();
    });
    expect(localStorage.getItem("pragatishala.access_token")).toBe("access-token");
  });

  it("rejects short passwords client-side without touching the API", async () => {
    const user = userEvent.setup();
    const registerSpy = vi.spyOn(api, "register");

    renderWithProviders(<RegistrationPage />, { route: "/register" });

    await fillForm(user, "short");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/at least 8 characters/i);
    expect(registerSpy).not.toHaveBeenCalled();
  });

  it("shows backend errors (e.g. duplicate email) in the alert region", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "register").mockRejectedValue(
      new Error("an account with asha@example.com already exists"),
    );

    renderWithProviders(<RegistrationPage />, { route: "/register" });

    await fillForm(user);
    await user.click(screen.getByRole("button", { name: /create account/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/already exists/i);
  });
});
