import { Box, Flex, Link as ChakraLink, Heading } from '@chakra-ui/react';
import { Link } from 'react-router-dom';

const Navbar = () => {
  return (
    <Flex
      as="nav"
      align="center"
      justify="space-between"
      wrap="wrap"
      padding="1.5rem"
      bg="blue.500"
      color="white"
    >
      <Flex align="center" mr={5}>
        <Heading as="h1" size="lg" letterSpacing={'-.1rem'}>
          <Link to="/">PragatiShala</Link>
        </Heading>
      </Flex>

      <Box>
        <ChakraLink as={Link} to="/login" mr={4}>
          Login
        </ChakraLink>
        <ChakraLink as={Link} to="/register" mr={4}>
          Register
        </ChakraLink>
        <ChakraLink as={Link} to="/assessment" mr={4}>
          Assessment
        </ChakraLink>
        <ChakraLink as={Link} to="/learning-path">
          Learning Path
        </ChakraLink>
      </Box>
    </Flex>
  );
};

export default Navbar;
