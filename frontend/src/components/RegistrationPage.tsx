import { useState } from "react";
import type { FormEvent } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import { Button, Field, Heading, Input, Link, NativeSelect, Stack, Text } from "@chakra-ui/react";
import { EXPERIENCE_LEVELS } from "../api/types";
import { useAuth } from "../auth/AuthContext";


/**
 * Registration page. Creates the account, signs the user in, and routes them
 * to their first assessment. All inputs are labelled and the inline error
 * region is announced by screen readers.
 */
export default function RegistrationPage() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [targetRole, setTargetRole] = useState("");
  const [experienceLevel, setExperienceLevel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setBusy(true);
    try {
      await register({
        email: email.trim(),
        password,
        full_name: fullName.trim(),
        target_role: targetRole.trim() || null,
        experience_level: experienceLevel || null,
      });
      navigate("/assessment");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to create the account.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Stack as="main" gap={6} maxW="md" mx="auto" pt={10}>
      <Heading size="2xl">Create your account</Heading>
      <Text color="fg.muted">
        Tell us a little about yourself so we can tailor assessments and roadmaps.
      </Text>

      {error ? (
        <Text role="alert" color="fg.error" fontWeight="bold">
          {error}
        </Text>
      ) : null}

      <form onSubmit={handleSubmit} noValidate>
        <Stack gap={4}>
          <Field.Root id="register-name">
            <Field.Label>Full name</Field.Label>
            <Input
              type="text"
              name="name"
              autoComplete="name"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              disabled={busy}
            />
          </Field.Root>

          <Field.Root id="register-email" required>
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

          <Field.Root id="register-password" required>
            <Field.Label>
              Password <Field.RequiredIndicator />
            </Field.Label>
            <Input
              type="password"
              name="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={busy}
            />
            <Field.HelperText>At least 8 characters.</Field.HelperText>
          </Field.Root>

          <Field.Root id="register-target-role">
            <Field.Label>Target role (optional)</Field.Label>
            <Input
              type="text"
              name="target-role"
              placeholder="e.g. Data Analyst"
              value={targetRole}
              onChange={(event) => setTargetRole(event.target.value)}
              disabled={busy}
            />
          </Field.Root>

          <Field.Root id="register-experience">
            <Field.Label>Experience level (optional)</Field.Label>
            <NativeSelect.Root>
              <NativeSelect.Field
                name="experience-level"
                value={experienceLevel}
                onChange={(event) => setExperienceLevel(event.target.value)}
              >
                <option value="">Prefer not to say</option>
                {EXPERIENCE_LEVELS.map((level) => (
                  <option key={level.value} value={level.value}>
                    {level.label}
                  </option>
                ))}
              </NativeSelect.Field>
              <NativeSelect.Indicator />
            </NativeSelect.Root>
          </Field.Root>

          <Button type="submit" colorPalette="blue" size="lg" loading={busy} width="full">
            {busy ? "Creating account…" : "Create account"}
          </Button>
        </Stack>
      </form>

      <Text>
        Already have an account?{" "}
        <Link asChild>
          <RouterLink to="/login">Sign in</RouterLink>
        </Link>
      </Text>
    </Stack>
  );
}
