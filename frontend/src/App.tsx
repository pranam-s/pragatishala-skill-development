import { Navigate, Route, Routes } from "react-router-dom";
import { Container, Heading, List, Text, VStack } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import Footer from "./components/Footer";
import LearningPath from "./components/LearningPath";
import LoginPage from "./components/LoginPage";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import RegistrationPage from "./components/RegistrationPage";
import RouteTitle from "./components/RouteTitle";
import SkillAssessment from "./components/SkillAssessment";

/** Public landing page for signed-out visitors. */
function HomePage() {
  return (
    <Container as="main" centerContent py={16}>
      <VStack gap={5} maxW="2xl" textAlign="center">
        <Heading size="3xl">PragatiShala</Heading>
        <Text fontSize="xl">
          AI-powered skill assessments, honest market insight, and personalized learning paths —
          built for Indian learners.
        </Text>
        <VStack gap={2} align="start">
          <Text fontWeight="bold">What you can do today:</Text>
          <List.Root pl={4}>
            <List.Item>
              Run a skill assessment from a plain-language description of your skills
            </List.Item>
            <List.Item>Generate a personalized, milestone-based learning path</List.Item>
            <List.Item>See which engine analysed your data (AI or offline rules)</List.Item>
          </List.Root>
        </VStack>
        <RouterLink
          to="/register"
          style={{ fontWeight: "bold", color: "inherit", textDecoration: "underline" }}
        >
          Create your free account to get started
        </RouterLink>
      </VStack>
    </Container>
  );
}

/** Routes for signed-in users; the wrapper keeps a signed-out visitor on /login. */
function AuthenticatedRoutes() {
  return (
    <ProtectedRoute>
      <Routes>
        <Route path="/assessment" element={<SkillAssessment />} />
        <Route path="/learning-path" element={<LearningPath />} />
        <Route path="*" element={<Navigate to="/assessment" replace />} />
      </Routes>
    </ProtectedRoute>
  );
}

function AppRoutes() {
  const { user } = useAuth();
  return (
    <Routes>
      <Route
        path="/"
        element={user ? <Navigate to="/assessment" replace /> : <HomePage />}
      />
      <Route path="/login" element={user ? <Navigate to="/assessment" replace /> : <LoginPage />} />
      <Route
        path="/register"
        element={user ? <Navigate to="/assessment" replace /> : <RegistrationPage />}
      />
      <Route path="*" element={<AuthenticatedRoutes />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <RouteTitle />
      <Navbar />
      <AppRoutes />
      <Footer />
    </AuthProvider>
  );
}
