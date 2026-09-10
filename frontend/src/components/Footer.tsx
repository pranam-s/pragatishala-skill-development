import { Container, Text } from "@chakra-ui/react";

export default function Footer() {
  return (
    <Container as="footer" centerContent py={6} mt={8}>
      <Text fontSize="sm" color="fg.muted">
        © {new Date().getFullYear()} PragatiShala — AI-powered skill development for Indian
        learners.
      </Text>
    </Container>
  );
}
