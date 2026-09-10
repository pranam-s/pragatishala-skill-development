import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api, ApiError } from "../api/client";
import type { LearningPath } from "../api/types";
import { renderWithProviders } from "../test/helpers";
import LearningPathPage from "./LearningPath";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

const samplePath: LearningPath = {
  id: 3,
  assessment_id: 7,
  target_role: "Data Analyst",
  status: "completed",
  engine_used: "rule_based",
  created_at: "2026-09-10T12:05:00",
  content: {
    headline: "Your path to Data Analyst: 2 modules, ~50 hours",
    target_role: "Data Analyst",
    total_estimated_hours: 50,
    modules: [
      {
        title: "Foundations: SQL",
        description: "Selects, joins, aggregations.",
        skills_covered: ["SQL"],
        estimated_hours: 30,
        resources: ["https://sqlbolt.com/"],
        milestone: "Answer 20 analytical questions.",
      },
      {
        title: "Statistics",
        description: "Distributions and hypothesis testing.",
        skills_covered: ["Statistics"],
        estimated_hours: 20,
        resources: [],
        milestone: "Report findings with confidence intervals.",
      },
    ],
    next_steps: ["Schedule weekly study blocks."],
  },
};

describe("LearningPathPage", () => {
  it("offers a generate button before any path exists", () => {
    renderWithProviders(<LearningPathPage />);
    expect(
      screen.getByRole("button", { name: /generate my learning path/i }),
    ).toBeInTheDocument();
  });

  it("generates a path and renders modules as an ordered list", async () => {
    const user = userEvent.setup();
    const generateSpy = vi.spyOn(api, "generateLearningPath").mockResolvedValue(samplePath);

    renderWithProviders(<LearningPathPage />);
    await user.click(screen.getByRole("button", { name: /generate my learning path/i }));

    await waitFor(() => {
      expect(generateSpy).toHaveBeenCalledWith(null);
    });

    expect(await screen.findByText(/2 modules, ~50 hours/i)).toBeInTheDocument();
    // The module roadmap is an <ol>; resource links render nested <ul> lists.
    const lists = screen.getAllByRole("list");
    expect(lists[0].tagName).toBe("OL");
    expect(screen.getByText(/Foundations: SQL/)).toBeInTheDocument();
    expect(screen.getByText(/Estimated hours: 30/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /sqlbolt/i })).toHaveAttribute(
      "href",
      "https://sqlbolt.com/",
    );
  });

  it("points users to the assessment when none exists yet", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "generateLearningPath").mockRejectedValue(
      new ApiError(404, "run a skill assessment first or provide an assessment_id"),
    );

    renderWithProviders(<LearningPathPage />);
    await user.click(screen.getByRole("button", { name: /generate my learning path/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/no assessment found yet/i);
    expect(screen.getByRole("link", { name: /go to skill assessment/i })).toBeInTheDocument();
  });
});

it("shows the error message for non-404 failures", async () => {
  const user = userEvent.setup();
  vi.spyOn(api, "generateLearningPath").mockRejectedValue(new Error("backend exploded"));

  renderWithProviders(<LearningPathPage />);
  await user.click(screen.getByRole("button", { name: /generate my learning path/i }));

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent(/backend exploded/i);
  expect(screen.queryByRole("link", { name: /go to skill assessment/i })).not.toBeInTheDocument();
});
