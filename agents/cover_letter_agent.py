"""
agents/cover_letter_agent.py
-----------------------------
Cover Letter Agent — generates a personalised, compelling
cover letter using Groq LLaMA.

WHAT MAKES A GOOD COVER LETTER:
  - Opens with something specific about the company (not "I am writing to apply...")
  - Connects 2-3 of your skills directly to job requirements
  - Mentions one concrete achievement with a number
  - Strong closing with a call to action
  - 250–320 words — recruiters don't read longer ones

PIPELINE POSITION: Step 4 (only for "apply" jobs)
INPUT:  job dict + candidate profile + tailored resume
OUTPUT: cover letter as plain text string
"""

from config import get_llm


def generate_cover_letter(
    job: dict,
    candidate_profile: str,
    tailored_resume: str = "",
    llm=None,
) -> str:
    """
    Generate a personalised cover letter for a specific job.

    Args:
        job:               Job dict (with matching_skills, decision_reason etc.)
        candidate_profile: Free-text description of candidate's background
        tailored_resume:   Tailored resume text (first 500 chars used as context)
        llm:               Optional Groq LLM

    Returns:
        Cover letter as plain text (250–320 words)
    """
    if llm is None:
        llm = get_llm()

    title           = job.get("title") or job.get("job_title", "")
    company         = job.get("company", "")
    required_skills = ", ".join(job.get("required_skills", []))
    matching_skills = ", ".join(job.get("matching_skills", job.get("required_skills", []))[:4])
    reason          = job.get("decision_reason", "Good skill match.")
    resume_excerpt  = tailored_resume[:500] if tailored_resume else ""

    prompt = f"""You are an expert cover letter writer who has helped thousands of candidates land jobs.
Write a compelling, concise cover letter for this application.

JOB: {title} at {company}
REQUIRED SKILLS: {required_skills}
CANDIDATE'S MATCHING SKILLS: {matching_skills}
WHY THIS JOB IS A GOOD FIT: {reason}

CANDIDATE PROFILE:
{candidate_profile}

RESUME EXCERPT (for context):
{resume_excerpt}

COVER LETTER RULES — follow these exactly:
1. Opening line: Something specific about {company} or this role. NEVER start with "I am writing to apply for"
2. Paragraph 1 (2-3 sentences): Connect 2-3 matching skills to specific job requirements. Be concrete.
3. Paragraph 2 (2-3 sentences): One specific achievement or project that proves you can do this job. Include a number/metric.
4. Closing (2 sentences): Express genuine enthusiasm + clear call to action (e.g. "I'd love to discuss...")
5. Tone: Confident, direct, human. NO buzzwords: no "passionate", "synergy", "leverage", "dynamic team"
6. Length: 250-320 words EXACTLY — count them
7. Format:
   Dear Hiring Manager,

   [opening]

   [paragraph 1]

   [paragraph 2]

   [closing]

   Sincerely,
   [Your Name]

Return ONLY the cover letter text. No preamble. Start with "Dear Hiring Manager,"."""

    response = llm.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)


if __name__ == "__main__":
    job = {
        "title": "ML Engineer",
        "company": "AI Startup",
        "required_skills": ["Python", "LangChain", "FastAPI", "PyTorch"],
        "matching_skills": ["Python", "LangChain", "FastAPI"],
        "decision_reason": "Strong Python + LangChain match. RAG pipeline experience directly relevant.",
    }
    profile = """
    3 years backend engineering experience. Built a RAG-based document assistant
    using LangChain and FAISS at TechCorp, used by 200 internal users.
    Strong Python developer, some PyTorch experience.
    Looking for ML engineering roles where I can work on production AI systems.
    """
    result = generate_cover_letter(job, profile)
    print(result)
    print(f"\n📝 Word count: {len(result.split())}")
