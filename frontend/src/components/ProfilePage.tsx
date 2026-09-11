import { useState } from "react";
import type { FormEvent } from "react";
import {
  Button,
  Field,
  Heading,
  Input,
  NativeSelect,
  Stack,
  Text,
} from "@chakra-ui/react";
import { EXPERIENCE_LEVELS } from "../api/types";
import { useAuth } from "../auth/AuthContext";


/**
 * Profile management: edit the fields the backend exposes. The email address
 * is the immutable account identifier and is shown read-only.
 */
export default function ProfilePage() {
  const { user, updateProfile, logout } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [targetRole, setTargetRole] = useState(user?.target_role ?? "");
  const [experienceLevel, setExperienceLevel] = useState(user?.experience_level ?? "");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSaved(false);
    setBusy(true);
    try {
      await updateProfile({
        full_name: fullName.trim(),
        target_role: targetRole.trim() || null,
        experience_level: experienceLevel || null,
      });
      setSaved(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to save.");
    } finally {
      setBusy(false);
    }
  }

  if (!user) return null;

  return (
    <Stack as="main" gap={6} maxW="md" mx="auto" pt={10}>
      <Heading size="2xl">Your profile</Heading>

      {error ? (
        <Text role="alert" color="fg.error" fontWeight="bold">
          {error}
        </Text>
      ) : null}
      {saved ? (
        <Text role="status" color="fg.success" fontWeight="bold">
          Profile saved.
        </Text>
      ) : null}

      <form onSubmit={handleSubmit} noValidate>
        <Stack gap={4}>
          <Field.Root id="profile-email">
            <Field.Label>Email address</Field.Label>
            <Input type="email" value={user.email} readOnly />
            <Field.HelperText>Your email cannot be changed.</Field.HelperText>
          </Field.Root>

          <Field.Root id="profile-name">
            <Field.Label>Full name</Field.Label>
            <Input
              type="text"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              disabled={busy}
            />
          </Field.Root>

          <Field.Root id="profile-target-role">
            <Field.Label>Target role</Field.Label>
            <Input
              type="text"
              placeholder="e.g. Data Analyst"
              value={targetRole}
              onChange={(event) => setTargetRole(event.target.value)}
              disabled={busy}
            />
            <Field.HelperText>Used as the default target for new assessments.</Field.HelperText>
          </Field.Root>

          <Field.Root id="profile-experience">
            <Field.Label>Experience level</Field.Label>
            <NativeSelect.Root>
              <NativeSelect.Field
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

          <Button type="submit" colorPalette="blue" loading={busy}>
            {busy ? "Saving…" : "Save changes"}
          </Button>
        </Stack>
      </form>

      <Text fontSize="sm" color="fg.muted">
        Member since {new Date(user.created_at).toLocaleDateString()}.
      </Text>
      <Button variant="outline" onClick={logout}>
        Log out
      </Button>
    </Stack>
  );
}
