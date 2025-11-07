import {
  Box,
  Heading,
  VStack,
  Text,
  List,
  ListItem,
  ListIcon,
} from '@chakra-ui/react';
import { MdCheckCircle } from 'react-icons/md';

const LearningPath = () => {
  return (
    <Box p={8}>
      <VStack spacing={4}>
        <Heading>Your Personalized Learning Path</Heading>
        <Text>Based on your skill assessment, here is a recommended learning path to achieve your career goals:</Text>
        <List spacing={3}>
          <ListItem>
            <ListIcon as={MdCheckCircle} color="green.500" />
            Introduction to Python
          </ListItem>
          <ListItem>
            <ListIcon as={MdCheckCircle} color="green.500" />
            Data Structures and Algorithms
          </ListItem>
          <ListItem>
            <ListIcon as={MdCheckCircle} color="green.500" />
            Introduction to Machine Learning
          </ListItem>
          <ListItem>
            <ListIcon as={MdCheckCircle} color="green.500" />
            Deep Learning Specialization
          </ListItem>
        </List>
      </VStack>
    </Box>
  );
};

export default LearningPath;
