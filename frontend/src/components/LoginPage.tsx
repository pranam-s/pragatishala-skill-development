import { useState } from "react";
import type { FormEvent } from "react";
import { Link as RouterLink, useLocation, useNavigate } from "react-router-dom";
import { Button, Field, Heading, Input, Link, Stack, Text } from "@chakra-ui/react";
import { useAuth } from "../auth/AuthContext";

/**
 * Sign-in page. Fully keyboard operable: labelled inputs, a visible submit
 * button, and an inline error region announced by screen readers.
 */
export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const from = (location.state as { from?: string } | null)?.from ?? "/assessment";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email.trim(), password);
      navigate(from, { replace: true });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to sign in.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Stack as="main" gap={6} maxW="md" mx="auto" pt={10}>
      <Heading size="2xl">Sign in</Heading>
      <Text color="fg.muted">
        Welcome back. Sign in to run assessments and build your learning path.
      </Text>

      {error ? (
        <Text role="alert" color="fg.error" fontWeight="bold">
          {error}
        </Text>
      ) : null}

      <form onSubmit={handleSubmit} noValidate>
        <Stack gap={4}>
          <Field.Root id="login-email" required>
            <Field.Label>
              Email address <Field.RequiredIndicator />
            </Field.Label>
            <Input
              type="email"
              name="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              disabled={busy}
            />
          </Field.Root>

          <Field.Root id="login-password" required>
            <Field.Label>
              Password <Field.RequiredIndicator />
            </Field.Label>
            <Input
              type="password"
              name="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={busy}
            />
          </Field.Root>

          <Button type="submit" colorPalette="blue" size="lg" loading={busy} width="full">
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </Stack>
      </form>

      <Text>
        New here?{" "}
        <Link asChild>
          <RouterLink to="/register">Create an account</RouterLink>
        </Link>
      </Text>
    </Stack>
  );
}
