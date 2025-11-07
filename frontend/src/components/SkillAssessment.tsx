import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Textarea,
  Stack,
  Heading,
  useToast,
} from '@chakra-ui/react';
import { useState } from 'react';

const SkillAssessment = () => {
  const [text, setText] = useState('');
  const toast = useToast();

  const handleSubmit = () => {
    toast({
      title: 'Assessment Complete',
      description: "We've analyzed your skills.",
      status: 'success',
      duration: 5000,
      isClosable: true,
    });
  };

  return (
    <Box p={8}>
      <Stack spacing={4}>
        <Heading>Skill Assessment</Heading>
        <FormControl id="skill-text">
          <FormLabel>Tell us about your skills</FormLabel>
          <Textarea value={text} onChange={(e) => setText(e.target.value)} />
        </FormControl>
        <Button colorScheme="blue" onClick={handleSubmit}>
          Assess My Skills
        </Button>
      </Stack>
    </Box>
  );
};

export default SkillAssessment;
