import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "../api/client";
import type { Assessment } from "../api/types";
import { mockUser, renderWithProviders } from "../test/helpers";
import SkillAssessment from "./SkillAssessment";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

const sampleAssessment: Assessment = {
  id: 7,
  target_role: "Data Analyst",
  status: "completed",
  engine_used: "rule_based",
  created_at: "2026-09-10T12:00:00",
  result: {
    summary: "Detected 3 skills across 2 areas.",
    skills: [
      { name: "Python", category: "programming", level: "intermediate", evidence: "mentioned 2x" },
      { name: "SQL", category: "data", level: "beginner", evidence: "mentioned 1x" },
    ],
    strengths: ["Python"],
    gaps: ["Statistics"],
    recommended_roles: ["Data Analyst"],
    readiness_score: 55,
  },
};

function renderSignedIn() {
  localStorage.setItem("pragatishala.access_token", "access-token");
  localStorage.setItem("pragatishala.refresh_token", "refresh-token");
  vi.spyOn(api, "me").mockResolvedValue(mockUser);
  return renderWithProviders(<SkillAssessment />, { route: "/assessment", withUser: true });
}

describe("SkillAssessment", () => {
  it("renders a labelled textarea and submit button", () => {
    vi.spyOn(api, "me").mockResolvedValue(mockUser);
    renderWithProviders(<SkillAssessment />, { route: "/assessment" });

    expect(screen.getByLabelText(/your skills and experience/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /assess my skills/i }),
    ).toBeInTheDocument();
  });

  it("submits the narrative and renders the structured result", async () => {
    const user = userEvent.setup();
    const assessSpy = vi
      .spyOn(api, "runAssessment")
      .mockImplementation(() => new Promise((resolve) => setTimeout(() => resolve(sampleAssessment), 10)));
    renderSignedIn();

    await user.type(
      screen.getByLabelText(/your skills and experience/i),
      "I know Python and a bit of SQL from college projects.",
    );
    await user.click(screen.getByRole("button", { name: /assess my skills/i }));

    await waitFor(() => {
      expect(assessSpy).toHaveBeenCalledWith(
        "I know Python and a bit of SQL from college projects.",
        "Data Analyst",
      );
    });

    expect(await screen.findByText(/Assessment #7 results/i)).toBeInTheDocument();
    expect(screen.getByText(/55 \/ 100/)).toBeInTheDocument();
    expect(screen.getByText(/Python — intermediate/)).toBeInTheDocument();
    expect(screen.getByText(/Statistics/)).toBeInTheDocument();
  });

  it("announces backend errors without losing the draft", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "runAssessment").mockRejectedValue(new Error("Could not validate credentials"));
    renderSignedIn();

    const textarea = screen.getByLabelText(/your skills and experience/i);
    await user.type(textarea, "My draft narrative that must not disappear on failure.");
    await user.click(screen.getByRole("button", { name: /assess my skills/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/could not validate credentials/i);
    expect(textarea).toHaveValue("My draft narrative that must not disappear on failure.");
  });
});
