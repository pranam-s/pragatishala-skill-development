"""Curated domain data powering the offline (rule-based) engine.

Skill taxonomy, target-role requirements, and market snapshots are maintained
here so the platform produces useful, deterministic output with no API keys.
When an LLM provider is configured its output takes precedence and this data
remains the validation-informed fallback.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SkillDef:
    """A known skill with matching aliases and market weight (0-10)."""

    name: str
    category: str
    aliases: tuple[str, ...] = ()
    demand: int = 5


SKILLS: tuple[SkillDef, ...] = (
    SkillDef("Python", "programming", ("python3", "py"), 9),
    SkillDef("JavaScript", "programming", ("js", "es6", "ecmascript"), 9),
    SkillDef("TypeScript", "programming", ("ts",), 8),
    SkillDef("Java", "programming", ("core java", "java8"), 8),
    SkillDef("C++", "programming", ("cpp", "c plus plus"), 7),
    SkillDef("Go", "programming", ("golang",), 7),
    SkillDef("Rust", "programming", (), 6),
    SkillDef("C", "programming", ("c language",), 5),
    SkillDef("C#", "programming", ("csharp", "c sharp", ".net"), 7),
    SkillDef("SQL", "data", ("mysql", "postgresql", "postgres", "sqlite"), 9),
    SkillDef("HTML", "web", ("html5",), 5),
    SkillDef("CSS", "web", ("css3",), 5),
    SkillDef("React", "web", ("reactjs", "react.js", "react js"), 9),
    SkillDef("Node.js", "web", ("nodejs", "node js", "node"), 8),
    SkillDef("Next.js", "web", ("nextjs",), 7),
    SkillDef("Django", "web", (), 7),
    SkillDef("FastAPI", "web", ("fast api",), 7),
    SkillDef("Flask", "web", (), 6),
    SkillDef("Angular", "web", (), 6),
    SkillDef("Vue.js", "web", ("vue", "vuejs"), 6),
    SkillDef("Machine Learning", "data", ("ml", "machine-learning"), 9),
    SkillDef("Deep Learning", "data", ("neural networks", "dl"), 8),
    SkillDef("Data Analysis", "data", ("data analytics", "analytics"), 8),
    SkillDef("Statistics", "data", ("stats", "statistical analysis"), 7),
    SkillDef("Pandas", "data", (), 7),
    SkillDef("NumPy", "data", ("numpy",), 6),
    SkillDef(
        "Data Visualization",
        "data",
        ("data viz", "matplotlib", "seaborn", "tableau", "power bi"),
        7,
    ),
    SkillDef(
        "Generative AI",
        "ai",
        ("genai", "gen ai", "llm", "large language models", "prompt engineering"),
        9,
    ),
    SkillDef("NLP", "ai", ("natural language processing",), 7),
    SkillDef("Computer Vision", "ai", ("cv", "opencv"), 6),
    SkillDef("AWS", "cloud", ("amazon web services", "ec2", "s3", "lambda"), 9),
    SkillDef("Azure", "cloud", ("microsoft azure",), 8),
    SkillDef("GCP", "cloud", ("google cloud", "google cloud platform"), 7),
    SkillDef("Docker", "devops", ("containers", "containerization"), 8),
    SkillDef("Kubernetes", "devops", ("k8s",), 8),
    SkillDef(
        "CI/CD", "devops", ("ci cd", "continuous integration", "jenkins", "github actions"), 8
    ),
    SkillDef("Linux", "devops", ("unix", "bash"), 7),
    SkillDef("Git", "devops", ("github", "gitlab", "version control"), 7),
    SkillDef("MongoDB", "data", ("mongo",), 7),
    SkillDef("Redis", "data", (), 6),
    SkillDef("GraphQL", "web", (), 6),
    SkillDef("REST APIs", "web", ("rest", "restful", "api development", "apis"), 8),
    SkillDef(
        "Communication", "soft", ("communication skills", "verbal", "written communication"), 7
    ),
    SkillDef("Teamwork", "soft", ("collaboration", "team player", "cross-functional"), 7),
    SkillDef(
        "Problem Solving",
        "soft",
        ("analytical thinking", "critical thinking", "troubleshooting"),
        8,
    ),
    SkillDef("Leadership", "soft", ("led", "mentoring", "managed a team"), 7),
    SkillDef("Time Management", "soft", ("prioritization", "deadlines"), 6),
    SkillDef("Adaptability", "soft", ("fast learner", "quick learner", "flexible"), 6),
    SkillDef("Figma", "design", (), 6),
    SkillDef(
        "UI/UX Design", "design", ("ui design", "ux design", "user experience", "user interface"), 7
    ),
    SkillDef(
        "Digital Marketing", "marketing", ("seo", "sem", "social media marketing", "google ads"), 7
    ),
    SkillDef("Content Writing", "marketing", ("copywriting", "blogging", "content creation"), 6),
    SkillDef("Excel", "productivity", ("microsoft excel", "advanced excel", "spreadsheets"), 6),
    SkillDef("Android Development", "mobile", ("android", "android sdk", "jetpack compose"), 7),
    SkillDef("iOS Development", "mobile", ("ios", "swift", "swiftui"), 6),
    SkillDef("Flutter", "mobile", (), 6),
    SkillDef("React Native", "mobile", (), 6),
)

_ALIAS_INDEX: dict[str, SkillDef] = {
    key.lower(): skill for skill in SKILLS for key in (skill.name, *skill.aliases)
}


def find_skill(token: str) -> SkillDef | None:
    """Look up a skill by canonical name or alias (case-insensitive)."""
    return _ALIAS_INDEX.get(token.strip().lower())


@dataclass(frozen=True)
class RoleProfile:
    """Expected skills for a target role family."""

    title: str
    required: tuple[str, ...]
    recommended: tuple[str, ...] = ()
    related_titles: tuple[str, ...] = field(default_factory=tuple)


ROLE_PROFILES: tuple[RoleProfile, ...] = (
    RoleProfile(
        "Software Engineer",
        ("Python", "JavaScript", "SQL", "Git", "REST APIs", "Problem Solving"),
        ("Docker", "AWS", "TypeScript", "CI/CD"),
        ("Backend Developer", "Full Stack Developer", "SDE"),
    ),
    RoleProfile(
        "Data Scientist",
        ("Python", "SQL", "Machine Learning", "Statistics", "Data Analysis"),
        ("Deep Learning", "Pandas", "Data Visualization", "Generative AI"),
        ("ML Engineer", "Data Analyst", "AI Engineer"),
    ),
    RoleProfile(
        "Data Analyst",
        ("SQL", "Excel", "Data Analysis", "Data Visualization", "Statistics"),
        ("Python", "Pandas", "Communication"),
        ("Business Analyst", "Analytics Engineer"),
    ),
    RoleProfile(
        "Web Developer",
        ("HTML", "CSS", "JavaScript", "React", "Git"),
        ("TypeScript", "Node.js", "REST APIs", "Next.js"),
        ("Frontend Developer", "Full Stack Developer"),
    ),
    RoleProfile(
        "DevOps Engineer",
        ("Linux", "Docker", "Kubernetes", "CI/CD", "AWS"),
        ("Python", "Git", "Terraform"),
        ("SRE", "Platform Engineer", "Cloud Engineer"),
    ),
    RoleProfile(
        "Machine Learning Engineer",
        ("Python", "Machine Learning", "Deep Learning", "SQL", "Docker"),
        ("AWS", "Generative AI", "Computer Vision", "NLP"),
        ("Data Scientist", "AI Engineer", "MLOps Engineer"),
    ),
    RoleProfile(
        "Mobile App Developer",
        ("Android Development", "JavaScript", "REST APIs", "Git"),
        ("Flutter", "React Native", "iOS Development", "UI/UX Design"),
        ("Flutter Developer", "iOS Developer", "Cross-platform Developer"),
    ),
    RoleProfile(
        "Product Manager",
        ("Communication", "Problem Solving", "Data Analysis", "Leadership"),
        ("SQL", "UI/UX Design", "Excel"),
        ("Associate Product Manager", "Program Manager"),
    ),
    RoleProfile(
        "UI/UX Designer",
        ("UI/UX Design", "Figma", "Communication"),
        ("HTML", "CSS", "Problem Solving"),
        ("Product Designer", "Interaction Designer"),
    ),
    RoleProfile(
        "Digital Marketer",
        ("Digital Marketing", "Content Writing", "Communication", "Data Analysis"),
        ("Excel", "Generative AI"),
        ("SEO Specialist", "Growth Marketer", "Social Media Manager"),
    ),
)

_FALLBACK_ROLE = RoleProfile(
    "Technology Professional",
    ("Communication", "Problem Solving"),
    ("Python", "SQL", "Data Analysis", "Digital Marketing", "UI/UX Design"),
    ("Software Engineer", "Data Analyst", "Web Developer"),
)


def role_profile(role: str | None) -> RoleProfile:
    """Match a free-text role to the closest known role family.

    Falls back to a generic technology profile when nothing matches.
    """
    if not role:
        return _FALLBACK_ROLE
    needle = role.lower().strip()
    best: RoleProfile | None = None
    best_score = 0
    for profile in ROLE_PROFILES:
        title_tokens = set(profile.title.lower().split())
        role_tokens = set(needle.split())
        overlap = len(title_tokens & role_tokens)
        if overlap > best_score:
            best = profile
            best_score = overlap
    return best if best is not None else _FALLBACK_ROLE


@dataclass(frozen=True)
class MarketSnapshot:
    """Offline market dataset entry for a role family."""

    demand_level: str
    median_salary_range_inr: str
    growth_outlook: str
    top_skills: tuple[str, ...]
    trending_skills: tuple[str, ...]
    typical_employers: tuple[str, ...]
    recommended_certifications: tuple[str, ...]
    advice: tuple[str, ...]


MARKET_DATA: dict[str, MarketSnapshot] = {
    "Software Engineer": MarketSnapshot(
        demand_level="very high",
        median_salary_range_inr="₹6-25 LPA (fresher to senior)",
        growth_outlook="Sustained double-digit growth driven by product companies and GCCs hiring across India.",
        top_skills=("Python", "JavaScript", "SQL", "REST APIs", "Git"),
        trending_skills=("Generative AI", "TypeScript", "Go", "Rust"),
        typical_employers=(
            "Product startups",
            "Global capability centers",
            "IT services majors",
            "Fintech companies",
        ),
        recommended_certifications=(
            "AWS Certified Developer",
            "Microsoft Azure Fundamentals (AZ-900)",
        ),
        advice=(
            "Build two deployed projects with public repositories - hiring managers read code.",
            "Practice data structures and algorithms consistently; they still gate most interviews.",
            "Contribute to one open-source project to demonstrate collaboration.",
        ),
    ),
    "Data Scientist": MarketSnapshot(
        demand_level="high",
        median_salary_range_inr="₹8-30 LPA (fresher to senior)",
        growth_outlook="High demand as firms industrialize analytics and GenAI; premium for engineers who ship models to production.",
        top_skills=("Python", "SQL", "Machine Learning", "Statistics", "Data Visualization"),
        trending_skills=("Generative AI", "LLM fine-tuning", "MLOps", "PyTorch"),
        typical_employers=(
            "E-commerce and marketplaces",
            "Banks and NBFCs",
            "Healthcare analytics",
            "AI-first startups",
        ),
        recommended_certifications=(
            "Google Advanced Data Analytics",
            "AWS Machine Learning Specialty",
        ),
        advice=(
            "Publish two end-to-end case studies with measurable business impact.",
            "Learn to deploy models behind APIs, not just train notebooks.",
            "Strengthen SQL - it remains the most-screened skill in data interviews.",
        ),
    ),
    "Data Analyst": MarketSnapshot(
        demand_level="high",
        median_salary_range_inr="₹4-14 LPA (fresher to senior)",
        growth_outlook="Steady demand across every industry; a common entry door into data careers.",
        top_skills=("SQL", "Excel", "Data Visualization", "Data Analysis", "Statistics"),
        trending_skills=("Power BI", "Python", "Generative AI for reporting"),
        typical_employers=(
            "Consulting firms",
            "Banks and insurers",
            "Retail chains",
            "SaaS companies",
        ),
        recommended_certifications=(
            "Microsoft PL-300 (Power BI)",
            "Google Data Analytics Certificate",
        ),
        advice=(
            "Master SQL window functions - they separate candidates in interviews.",
            "Build a dashboard portfolio on real public datasets.",
            "Practice translating charts into one-line business recommendations.",
        ),
    ),
    "Web Developer": MarketSnapshot(
        demand_level="high",
        median_salary_range_inr="₹4-18 LPA (fresher to senior)",
        growth_outlook="Consistent demand for engineers who can ship complete features; full-stack profiles command premiums.",
        top_skills=("JavaScript", "React", "HTML", "CSS", "Git"),
        trending_skills=("Next.js", "TypeScript", "Tailwind CSS", "AI-assisted development"),
        typical_employers=(
            "Digital agencies",
            "SaaS startups",
            "D2C brands",
            "Freelance platforms",
        ),
        recommended_certifications=("Meta Front-End Developer", "AWS Certified Cloud Practitioner"),
        advice=(
            "Deploy every project - live URLs beat screenshots.",
            "Learn accessibility (WCAG); it is increasingly contractual in India.",
            "Add one project with authentication and payments to cover real-world flows.",
        ),
    ),
    "DevOps Engineer": MarketSnapshot(
        demand_level="very high",
        median_salary_range_inr="₹7-28 LPA (fresher to senior)",
        growth_outlook="Cloud adoption and platform engineering keep demand ahead of supply.",
        top_skills=("Linux", "Docker", "Kubernetes", "CI/CD", "AWS"),
        trending_skills=(
            "Terraform",
            "GitOps",
            "Observability (OpenTelemetry)",
            "Platform engineering",
        ),
        typical_employers=(
            "Cloud consultancies",
            "Product companies",
            "Fintech scale-ups",
            "Managed service providers",
        ),
        recommended_certifications=(
            "Certified Kubernetes Administrator (CKA)",
            "AWS Solutions Architect Associate",
        ),
        advice=(
            "Automate a deployment pipeline end to end and document it.",
            "Learn one infrastructure-as-code tool deeply.",
            "Practice incident write-ups - reliability thinking is interviewed.",
        ),
    ),
    "Machine Learning Engineer": MarketSnapshot(
        demand_level="very high",
        median_salary_range_inr="₹10-35 LPA (fresher to senior)",
        growth_outlook="Explosive demand from GenAI adoption; production ML skills command top-of-market pay.",
        top_skills=("Python", "Machine Learning", "Deep Learning", "Docker", "SQL"),
        trending_skills=("LLM applications", "RAG architectures", "MLOps", "Vector databases"),
        typical_employers=(
            "AI startups",
            "Large tech R&D centers",
            "Fintech risk teams",
            "Healthcare AI",
        ),
        recommended_certifications=(
            "AWS Machine Learning Specialty",
            "Google Professional ML Engineer",
        ),
        advice=(
            "Ship one LLM-backed feature with evaluation metrics.",
            "Learn model serving and latency budgeting, not just training.",
            "Build a public portfolio of reproducible ML pipelines.",
        ),
    ),
    "Mobile App Developer": MarketSnapshot(
        demand_level="moderate",
        median_salary_range_inr="₹5-20 LPA (fresher to senior)",
        growth_outlook="Stable demand with a shift toward cross-platform stacks and app modernization.",
        top_skills=("Android Development", "REST APIs", "Git", "JavaScript"),
        trending_skills=("Flutter", "React Native", "Kotlin Multiplatform"),
        typical_employers=(
            "App product companies",
            "Agencies",
            "BFSI apps",
            "Health-tech startups",
        ),
        recommended_certifications=(
            "Google Associate Android Developer",
            "Meta React Native (community tracks)",
        ),
        advice=(
            "Publish an app on the Play Store - it is the strongest signal.",
            "Learn offline-first data sync patterns.",
            "Cover accessibility and localization; Indian apps serve many languages.",
        ),
    ),
    "Product Manager": MarketSnapshot(
        demand_level="high",
        median_salary_range_inr="₹12-40 LPA (associate to senior)",
        growth_outlook="Strong demand in product-led companies; AI product management is the fastest-growing slice.",
        top_skills=("Communication", "Problem Solving", "Data Analysis", "Leadership"),
        trending_skills=("AI product strategy", "SQL", "Experimentation (A/B testing)"),
        typical_employers=(
            "Unicorn startups",
            "Big tech India campuses",
            "Fintech",
            "Enterprise SaaS",
        ),
        recommended_certifications=("Pragmatic Institute (PML1)", "Reforge programs"),
        advice=(
            "Write 2-3 public product teardowns showing structured thinking.",
            "Learn basic SQL to self-serve analytics.",
            "Practice writing crisp PRDs and metric trees.",
        ),
    ),
    "UI/UX Designer": MarketSnapshot(
        demand_level="moderate",
        median_salary_range_inr="₹5-18 LPA (fresher to senior)",
        growth_outlook="Healthy demand where design systems and accessibility compliance are scaling.",
        top_skills=("UI/UX Design", "Figma", "Communication"),
        trending_skills=("Design systems", "Accessibility (WCAG)", "AI-assisted prototyping"),
        typical_employers=("Design studios", "SaaS companies", "D2C brands", "BFSI digital teams"),
        recommended_certifications=("Google UX Design Certificate", "NN/g UX Certification"),
        advice=(
            "Curate 3 deep case studies over 10 screenshots.",
            "Learn WCAG basics - accessible design is now table stakes.",
            "Pair with developers to understand handoff realities.",
        ),
    ),
    "Digital Marketer": MarketSnapshot(
        demand_level="high",
        median_salary_range_inr="₹4-16 LPA (fresher to senior)",
        growth_outlook="Growing with D2C expansion; performance marketing and AI content workflows dominate hiring.",
        top_skills=("Digital Marketing", "Content Writing", "Data Analysis", "Communication"),
        trending_skills=(
            "Generative AI content workflows",
            "Marketing automation",
            "Analytics (GA4)",
        ),
        typical_employers=("D2C brands", "EdTech", "Agencies", "Marketplaces"),
        recommended_certifications=(
            "Google Ads Certification",
            "Meta Blueprint",
            "HubSpot Inbound Marketing",
        ),
        advice=(
            "Run one real campaign with a small budget and document ROI.",
            "Learn GA4 and spreadsheet modelling - attribution questions dominate interviews.",
            "Build a public portfolio: blog, socials, or ad creatives with metrics.",
        ),
    ),
}

_FALLBACK_MARKET = MarketSnapshot(
    demand_level="moderate",
    median_salary_range_inr="₹4-20 LPA depending on specialization and city",
    growth_outlook="India's digital economy continues to add roles; hybrid skill profiles (domain + AI tools) grow fastest.",
    top_skills=("Communication", "Problem Solving", "Excel", "Data Analysis"),
    trending_skills=("Generative AI", "Data Analysis", "Automation"),
    typical_employers=("IT services", "Startups", "Enterprises undergoing digital transformation"),
    recommended_certifications=("Google Career Certificates", "AI For Everyone (DeepLearning.AI)"),
    advice=(
        "Pair one domain skill with one AI tool to differentiate your profile.",
        "Build a verifiable portfolio (GitHub, Behance, blog, or campaigns).",
        "Practice structured interviews - clarity of thought is the universal screen.",
    ),
)


def market_snapshot(role: str | None) -> MarketSnapshot:
    """Return the market dataset entry for a role family."""
    return MARKET_DATA.get(role_profile(role).title, _FALLBACK_MARKET)
