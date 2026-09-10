import { Navigate, useLocation } from "react-router-dom";
import { Container, Spinner, Text, VStack } from "@chakra-ui/react";
import type { ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";

/**
 * Gate for authenticated routes. While the session is bootstrapping we show a
 * labelled spinner instead of bouncing the user to /login prematurely.
 */
export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, initializing } = useAuth();
  const location = useLocation();

  if (initializing) {
    return (
      <Container as="main" centerContent py={16}>
        <VStack gap={3} role="status">
          <Spinner size="lg" />
          <Text>Checking your session…</Text>
        </VStack>
      </Container>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}
