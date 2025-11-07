import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Box, Heading, VStack, Link as ChakraLink } from '@chakra-ui/react';
import LoginPage from './components/LoginPage';
import RegistrationPage from './components/RegistrationPage';
import SkillAssessment from './components/SkillAssessment';
import LearningPath from './components/LearningPath';
import Navbar from './components/Navbar';
import Footer from './components/Footer';

const HomePage = () => (
  <Box p={8}>
    <VStack spacing={4}>
      <Heading>Welcome to PragatiShala</Heading>
      <ChakraLink as={Link} to="/login">Login</ChakraLink>
      <ChakraLink as={Link} to="/register">Register</ChakraLink>
      <ChakraLink as={Link} to="/assessment">Skill Assessment</ChakraLink>
      <ChakraLink as={Link} to="/learning-path">Learning Path</ChakraLink>
    </VStack>
  </Box>
);

function App() {
  return (
    <Router>
      <Navbar />
      <Box p={8}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegistrationPage />} />
          <Route path="/assessment" element={<SkillAssessment />} />
          <Route path="/learning-path" element={<LearningPath />} />
        </Routes>
      </Box>
      <Footer />
    </Router>
  );
}

export default App;
