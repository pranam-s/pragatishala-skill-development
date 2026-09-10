import { HStack, Heading, Button, Text, Flex } from "@chakra-ui/react";
import { NavLink as RouterNavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const NAV_ITEMS = [
  { to: "/assessment", label: "Assessment" },
  { to: "/learning-path", label: "Learning path" },
] as const;

/**
 * Top navigation. Uses the router's NavLink so the current page is exposed to
 * assistive technology via aria-current="page".
 */
export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <Flex
      as="nav"
      aria-label="Main navigation"
      align="center"
      justify="space-between"
      wrap="wrap"
      gap={4}
      px={6}
      py={4}
      bg="bg.emphasized"
    >
      <Heading as="h1" size="lg">
        <RouterNavLink
          to={user ? "/assessment" : "/"}
          style={{ textDecoration: "none", color: "inherit" }}
        >
          PragatiShala
        </RouterNavLink>
      </Heading>

      <HStack as="ul" listStyleType="none" gap={5} m={0} p={0}>
        {user ? (
          <>
            {NAV_ITEMS.map((item) => (
              <Text as="li" key={item.to}>
                <RouterNavLink to={item.to}>
                  {({ isActive }) => (
                    <Text
                      as="span"
                      fontWeight={isActive ? "bold" : "normal"}
                      aria-current={isActive ? "page" : undefined}
                      textDecoration={isActive ? "underline" : "none"}
                    >
                      {item.label}
                    </Text>
                  )}
                </RouterNavLink>
              </Text>
            ))}
            <Text as="li">
              <Text as="span" color="fg.muted">
                Signed in as {user.email}
              </Text>
            </Text>
            <Text as="li">
              <Button size="sm" variant="outline" onClick={handleLogout}>
                Log out
              </Button>
            </Text>
          </>
        ) : (
          <>
            <Text as="li">
              <RouterNavLink to="/login">Sign in</RouterNavLink>
            </Text>
            <Text as="li">
              <RouterNavLink to="/register">Register</RouterNavLink>
            </Text>
          </>
        )}
      </HStack>
    </Flex>
  );
}
