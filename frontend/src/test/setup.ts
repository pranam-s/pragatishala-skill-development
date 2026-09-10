import { beforeEach } from "vitest";
import "@testing-library/jest-dom/vitest";

// jsdom lacks some browser APIs; nothing extra needed. Clean storage per test.
beforeEach(() => {
  localStorage.clear();
});
