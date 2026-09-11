import { useEffect } from "react";
import { useLocation } from "react-router-dom";

const TITLES: Record<string, string> = {
  "/": "Home",
  "/login": "Sign in",
  "/register": "Create your account",
  "/assessment": "Skill assessment",
  "/learning-path": "Learning path",
  "/profile": "Profile",
};

/**
 * Keeps `document.title` in sync with the route. Screen readers surface the
 * title on navigation, which restores the page-context cue that SPAs otherwise
 * lose compared to multi-page sites.
 */
export default function RouteTitle() {
  const { pathname } = useLocation();

  useEffect(() => {
    const page = TITLES[pathname] ?? "PragatiShala";
    document.title = `${page} — PragatiShala`;
  }, [pathname]);

  return null;
}
