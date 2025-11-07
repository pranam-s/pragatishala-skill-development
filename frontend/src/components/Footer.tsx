import { Box, Text } from '@chakra-ui/react';

const Footer = () => {
  return (
    <Box as="footer" py={4} textAlign="center" mt={8}>
      <Text>&copy; {new Date().getFullYear()} PragatiShala. All rights reserved.</Text>
    </Box>
  );
};

export default Footer;
