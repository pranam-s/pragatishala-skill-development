import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ChakraProvider, defaultSystem } from "@chakra-ui/react";
import { api } from "../api/client";
import { mockUser } from "../test/helpers";
import { AuthProvider } from "../auth/AuthContext";
import ProtectedRoute from "./ProtectedRoute";
import ProfilePage from "./ProfilePage";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

// Mirror the real app: the page renders only once the session exists.
function renderSignedIn() {
  localStorage.setItem("pragatishala.access_token", "access-token");
  localStorage.setItem("pragatishala.refresh_token", "refresh-token");
  vi.spyOn(api, "me").mockResolvedValue(mockUser);
  return render(
    <ChakraProvider value={defaultSystem}>
      <AuthProvider>
        <MemoryRouter initialEntries={["/profile"]}>
          <Routes>
            <Route
              path="/profile"
              element={
                <ProtectedRoute>
                  <ProfilePage />
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </ChakraProvider>,
  );
}

describe("ProfilePage", () => {
  it("renders the form pre-filled from the signed-in profile", async () => {
    renderSignedIn();

    expect(await screen.findByLabelText(/email address/i)).toHaveValue(mockUser.email);
    expect(screen.getByLabelText(/full name/i)).toHaveValue(mockUser.full_name);
    expect(screen.getByLabelText(/target role/i)).toHaveValue(mockUser.target_role);
    expect(screen.getByLabelText(/experience level/i)).toHaveValue(mockUser.experience_level);
    expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument();
  });

  it("saves changes and confirms with a status message", async () => {
    const user = userEvent.setup();
    const updateSpy = vi
      .spyOn(api, "updateProfile")
      .mockResolvedValue({ ...mockUser, full_name: "Asha V.", target_role: "Analytics Engineer" });
    renderSignedIn();

    const name = await screen.findByLabelText(/full name/i);
    await user.clear(name);
    await user.type(name, "Asha V.");
    await user.clear(screen.getByLabelText(/target role/i));
    await user.type(screen.getByLabelText(/target role/i), "Analytics Engineer");
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith({
        full_name: "Asha V.",
        target_role: "Analytics Engineer",
        experience_level: mockUser.experience_level,
      });
    });
    expect(await screen.findByRole("status")).toHaveTextContent(/profile saved/i);
  });

  it("announces backend errors without losing edits", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "updateProfile").mockRejectedValue(new Error("Could not validate credentials"));
    renderSignedIn();

    const name = await screen.findByLabelText(/full name/i);
    await user.clear(name);
    await user.type(name, "Edited Name");
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/could not validate credentials/i);
    expect(screen.getByLabelText(/full name/i)).toHaveValue("Edited Name");
  });
});
