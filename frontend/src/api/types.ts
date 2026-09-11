/** Types mirroring the backend Pydantic schemas (see backend/app/schemas.py). */

export interface User {
  id: number;
  email: string;
  full_name: string;
  target_role: string | null;
  experience_level: string | null;
  created_at: string;
}

export interface TokenPair {
  token_type: "bearer";
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export interface SkillScore {
  name: string;
  category: string;
  level: "beginner" | "intermediate" | "advanced" | "expert";
  evidence: string;
}

export interface AssessmentResult {
  summary: string;
  skills: SkillScore[];
  strengths: string[];
  gaps: string[];
  recommended_roles: string[];
  readiness_score: number;
}

export interface Assessment {
  id: number;
  target_role: string | null;
  status: string;
  result: AssessmentResult | null;
  engine_used: string;
  created_at: string;
}

export interface LearningModule {
  title: string;
  description: string;
  skills_covered: string[];
  estimated_hours: number;
  resources: string[];
  milestone: string;
}

export interface LearningPathContent {
  headline: string;
  target_role: string | null;
  total_estimated_hours: number;
  modules: LearningModule[];
  next_steps: string[];
}

export interface LearningPath {
  id: number;
  assessment_id: number | null;
  target_role: string | null;
  status: string;
  content: LearningPathContent | null;
  engine_used: string;
  created_at: string;
}

/**
 * Experience levels, mirrored from the backend `Literal` in
 * backend/app/schemas.py (single source of truth: keep in sync).
 */
export const EXPERIENCE_LEVELS = [
  { value: "fresher", label: "Fresher" },
  { value: "student", label: "Student" },
  { value: "junior", label: "Junior (1-3 years)" },
  { value: "mid", label: "Mid-level (3-7 years)" },
  { value: "senior", label: "Senior (7+ years)" },
] as const;

export type ExperienceLevel = (typeof EXPERIENCE_LEVELS)[number]["value"];
