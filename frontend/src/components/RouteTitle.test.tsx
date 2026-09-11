import { afterEach, describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import RouteTitle from "./RouteTitle";

afterEach(() => {
  document.title = "";
});

function renderAt(route: string) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <RouteTitle />
      <Routes>
        <Route path="*" element={<div>page</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("RouteTitle", () => {
  it("sets a page-specific title for known routes", () => {
    renderAt("/login");
    expect(document.title).toBe("Sign in — PragatiShala");
  });

  it("titles the profile page", () => {
    renderAt("/profile");
    expect(document.title).toBe("Profile — PragatiShala");
  });

  it("falls back to the app name for unknown routes", () => {
    renderAt("/nowhere");
    expect(document.title).toBe("PragatiShala — PragatiShala");
  });
});
