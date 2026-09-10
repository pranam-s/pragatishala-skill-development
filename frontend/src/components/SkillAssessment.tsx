import { useState } from "react";
import type { FormEvent } from "react";
import { Link as RouterLink } from "react-router-dom";
import {
  Button,
  Container,
  Field,
  Heading,
  Link,
  List,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
} from "@chakra-ui/react";
import { api, ApiError } from "../api/client";
import type { Assessment } from "../api/types";
import { useAuth } from "../auth/AuthContext";

const MIN_LENGTH = 20;

/**
 * Skill assessment: submit a free-form skills narrative and render the
 * structured analysis. Results and status changes are announced via a polite
 * live region so screen-reader users hear progress without focus jumps.
 */
export default function SkillAssessment() {
  const { user } = useAuth();
  const [narrative, setNarrative] = useState("");
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setAssessment(null);
    setBusy(true);
    try {
      const result = await api.runAssessment(narrative, user?.target_role ?? null);
      setAssessment(result);
    } catch (cause) {
      setError(
        cause instanceof ApiError || cause instanceof Error
          ? cause.message
          : "Unable to run the assessment.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Container maxW="3xl">
      <Stack as="main" gap={6} py={8}>
        <Heading size="2xl">Skill assessment</Heading>
        <Text color="fg.muted">
          Describe your skills, studies, and experience in your own words. We analyse the text and
          estimate where you stand for your target role
          {user?.target_role ? ` (${user.target_role})` : ""}.
        </Text>

        {error ? (
          <Text role="alert" color="fg.error" fontWeight="bold">
            {error}
          </Text>
        ) : null}

        <form onSubmit={handleSubmit} noValidate>
          <Field.Root id="assessment-input" required>
            <Field.Label>Your skills and experience</Field.Label>
            <Textarea
              name="narrative"
              rows={8}
              required
              minLength={MIN_LENGTH}
              maxLength={8000}
              placeholder="e.g. I have been learning Python for a year, I know basic SQL, and I built a small website with HTML and CSS…"
              value={narrative}
              onChange={(event) => setNarrative(event.target.value)}
              disabled={busy}
            />
            <Field.HelperText>At least {MIN_LENGTH} characters.</Field.HelperText>
          </Field.Root>
          <Button type="submit" colorPalette="blue" size="lg" mt={4} loading={busy}>
            {busy ? "Analysing…" : "Assess my skills"}
          </Button>
        </form>

        {/* Polite live region: announces analysis readiness without stealing focus. */}
        <Text aria-live="polite" color="fg.muted">
          {busy ? "Analysing your skills; results will appear shortly." : ""}
        </Text>

        {assessment?.result ? (
          <Stack gap={6} aria-labelledby="assessment-result-heading">
            <Heading id="assessment-result-heading" size="xl">
              Assessment #{assessment.id} results
            </Heading>

            <Stack gap={2}>
              <Text fontSize="lg">{assessment.result.summary}</Text>
              <Text>
                Estimated readiness: <strong>{assessment.result.readiness_score} / 100</strong>
              </Text>
              <Text fontSize="sm" color="fg.muted">
                Engine used: {assessment.engine_used === "rule_based" ? "offline rule-based" : assessment.engine_used}
              </Text>
            </Stack>

            <SimpleGrid columns={{ base: 1, md: 2 }} gap={6}>
              <Stack gap={2}>
                <Heading size="md">Detected skills</Heading>
                {assessment.result.skills.length ? (
                  <List.Root gap={1} pl={4}>
                    {assessment.result.skills.map((skill) => (
                      <List.Item key={skill.name}>
                        {skill.name} — {skill.level} ({skill.category})
                      </List.Item>
                    ))}
                  </List.Root>
                ) : (
                  <Text color="fg.muted">No known skills detected yet.</Text>
                )}
              </Stack>

              <Stack gap={6}>
                <Stack gap={2}>
                  <Heading size="md">Strengths</Heading>
                  <List.Root gap={1} pl={4}>
                    {assessment.result.strengths.map((strength) => (
                      <List.Item key={strength}>{strength}</List.Item>
                    ))}
                  </List.Root>
                </Stack>
                <Stack gap={2}>
                  <Heading size="md">Gaps to close</Heading>
                  <List.Root gap={1} pl={4}>
                    {assessment.result.gaps.map((gap) => (
                      <List.Item key={gap}>{gap}</List.Item>
                    ))}
                  </List.Root>
                </Stack>
              </Stack>
            </SimpleGrid>

            <Text>
              Ready for the next step?{" "}
              <Link asChild>
                <RouterLink to="/learning-path">Generate your learning path</RouterLink>
              </Link>
            </Text>
          </Stack>
        ) : null}
      </Stack>
    </Container>
  );
}
