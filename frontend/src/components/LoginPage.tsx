import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  Stack,
  Heading,
} from '@chakra-ui/react';

const LoginPage = () => {
  return (
    <Box p={8}>
      <Stack spacing={4}>
        <Heading>Login</Heading>
        <FormControl id="email">
          <FormLabel>Email address</FormLabel>
          <Input type="email" />
        </FormControl>
        <FormControl id="password">
          <FormLabel>Password</FormLabel>
          <Input type="password" />
        </FormControl>
        <Button colorScheme="blue">Login</Button>
      </Stack>
    </Box>
  );
};

export default LoginPage;
