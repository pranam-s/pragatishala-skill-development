import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import {
  Button,
  Container,
  Heading,
  Link,
  List,
  Stack,
  Text,
} from "@chakra-ui/react";
import { api, ApiError } from "../api/client";
import type { LearningPath } from "../api/types";

/**
 * Learning path: generates a personalized roadmap from the user's most recent
 * assessment and renders it as an ordered, screen-reader friendly list.
 */
export default function LearningPathPage() {
  const [path, setPath] = useState<LearningPath | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleGenerate() {
    setError(null);
    setBusy(true);
    try {
      const generated = await api.generateLearningPath(null);
      setPath(generated);
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 404) {
        setError("No assessment found yet — run a skill assessment first.");
      } else {
        setError(cause instanceof Error ? cause.message : "Unable to generate a learning path.");
      }
    } finally {
      setBusy(false);
    }
  }

  const content = path?.content;

  return (
    <Container maxW="3xl">
      <Stack as="main" gap={6} py={8}>
        <Heading size="2xl">Your learning path</Heading>
        <Text color="fg.muted">
          We build an ordered roadmap from your latest skill assessment — foundational modules
          first, with milestones you can show to employers.
        </Text>

        {error ? (
          <Stack gap={2} role="alert">
            <Text color="fg.error" fontWeight="bold">
              {error}
            </Text>
            {error.includes("assessment") ? (
              <Link asChild>
                <RouterLink to="/assessment">Go to skill assessment</RouterLink>
              </Link>
            ) : null}
          </Stack>
        ) : null}

        <div>
          <Button colorPalette="blue" size="lg" onClick={handleGenerate} loading={busy}>
            {busy ? "Generating…" : path ? "Regenerate my path" : "Generate my learning path"}
          </Button>
        </div>

        <Stack aria-live="polite" gap={6}>
          {content ? (
            <>
              <Stack gap={2}>
                <Heading size="xl" id="path-headline">
                  {content.headline}
                </Heading>
                {content.target_role ? (
                  <Text>
                    Target role: <strong>{content.target_role}</strong>
                  </Text>
                ) : null}
                <Text>
                  About <strong>{content.total_estimated_hours} hours</strong> across{" "}
                  {content.modules.length} module{content.modules.length === 1 ? "" : "s"}.
                </Text>
              </Stack>

              <ol>
                {content.modules.map((module, index) => (
                  <Stack
                    as="li"
                    key={`${index}-${module.title}`}
                    gap={1}
                    py={3}
                    borderTopWidth="1px"
                    aria-labelledby={`module-${index}-title`}
                  >
                    <Heading size="md" id={`module-${index}-title`}>
                      {index + 1}. {module.title}
                    </Heading>
                    <Text>{module.description}</Text>
                    <Text fontSize="sm" color="fg.muted">
                      Estimated hours: {module.estimated_hours}
                    </Text>
                    <Text fontSize="sm">
                      <strong>Milestone:</strong> {module.milestone}
                    </Text>
                    {module.resources.length ? (
                      <List.Root gap={1} pl={4} mt={1}>
                        {module.resources.map((resource, resourceIndex) => (
                          <List.Item key={`${resourceIndex}-${resource}`}>
                            <Link
                              href={resource}
                              target="_blank"
                              rel="noreferrer"
                              variant="underline"
                            >
                              {resource}
                            </Link>
                          </List.Item>
                        ))}
                      </List.Root>
                    ) : null}
                  </Stack>
                ))}
              </ol>

              {content.next_steps.length ? (
                <Stack gap={2}>
                  <Heading size="md">Next steps</Heading>
                  <List.Root gap={1} pl={4}>
                    {content.next_steps.map((step, stepIndex) => (
                      <List.Item key={`${stepIndex}-${step}`}>{step}</List.Item>
                    ))}
                  </List.Root>
                </Stack>
              ) : null}
            </>
          ) : null}
        </Stack>
      </Stack>
    </Container>
  );
}
