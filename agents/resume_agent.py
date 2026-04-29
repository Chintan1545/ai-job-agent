"""
agents/resume_agent.py
----------------------
Resume Agent — tailors your resume for a specific job using
RAG (FAISS + HuggingFace embeddings) + Groq LLaMA.

HOW IT WORKS:
  1. Takes the job's required skills as the RAG query
  2. FAISS retrieves the most relevant resume chunks
  3. Groq LLaMA rewrites those sections with job-specific keywords
  4. Returns a complete ATS-optimised resume in markdown

PIPELINE POSITION: Step 3 (only for "apply" jobs)
INPUT:  single job dict + resume text/path
OUTPUT: tailored resume as markdown string
"""

from config import get_llm

try:
    from tools.resume_loader import query_resume, get_full_resume_text, build_index_from_text
    FAISS_AVAILABLE = True
except Exception:
    FAISS_AVAILABLE = False


def tailor_resume(
    job: dict,
    resume_text: str = None,
    resume_path: str = None,
    llm=None,
) -> str:
    """
    Tailor a resume for a specific job posting.

    Args:
        job:         Job dict (with required_skills, key_responsibilities etc.)
        resume_text: Raw resume as plain text (use this OR resume_path)
        resume_path: Path to PDF/DOCX (FAISS RAG will be used)
        llm:         Optional Groq LLM

    Returns:
        Tailored resume as a markdown string
    """
    if llm is None:
        llm = get_llm()

    # ── Get resume content ────────────────────────────────────────────────────
    if resume_text and FAISS_AVAILABLE:
        # Build a fresh index from the pasted text, then query it
        try:
            build_index_from_text(resume_text)
            skill_query = ", ".join(job.get("required_skills", []))
            relevant    = query_resume(skill_query, k=4)
        except Exception:
            relevant    = resume_text[:1500]
        full_text = resume_text

    elif resume_path and FAISS_AVAILABLE:
        full_text   = get_full_resume_text(resume_path)
        skill_query = ", ".join(job.get("required_skills", []))
        relevant    = query_resume(skill_query, k=4)

    elif resume_text:
        full_text = resume_text
        relevant  = resume_text[:1500]

    else:
        return "❌ Error: provide either resume_text or resume_path."

    required_skills  = ", ".join(job.get("required_skills", []))
    nice_to_have     = ", ".join(job.get("nice_to_have", []))
    responsibilities = "\n".join(f"- {r}" for r in job.get("key_responsibilities", []))
    title            = job.get("title") or job.get("job_title", "")
    company          = job.get("company", "")

    prompt = f"""You are a professional resume writer specialising in ATS optimisation.
Tailor the resume below for this specific job posting.

JOB: {title} at {company}
REQUIRED SKILLS: {required_skills}
NICE TO HAVE: {nice_to_have}
KEY RESPONSIBILITIES:
{responsibilities}

MOST RELEVANT RESUME SECTIONS (retrieved by semantic search):
{relevant}

FULL RESUME:
{full_text[:2500]}

STRICT RULES:
1. Be 100% truthful — only reframe existing experience, never invent skills or jobs
2. Mirror the EXACT keywords from required skills in the skills section
3. Rewrite bullet points to use the job's language (e.g. if job says "microservices", use that word)
4. Add quantified metrics where the original is vague ("improved performance" → "improved API response time by 35%")
5. Put the most relevant skills FIRST in the skills section
6. Keep to approximately 600 words
7. Format in clean markdown with these sections in order:
   # [Full Name]
   Contact line
   ## Summary
   ## Skills
   ## Experience
   ## Projects
   ## Education

Return ONLY the tailored resume markdown. No preamble. No "Here is your resume:". Start directly with # [Name]."""

    response = llm.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)


if __name__ == "__main__":
    job = {
        "title": "ML Engineer",
        "company": "AI Startup",
        "required_skills": ["Python", "PyTorch", "LangChain", "FAISS", "FastAPI"],
        "nice_to_have": ["Kubernetes", "Redis"],
        "key_responsibilities": [
            "Build and deploy ML models to production",
            "Design RAG pipelines using LLMs",
            "Collaborate with product team on AI features",
        ],
    }
    resume = """
John Doe | john@example.com | github.com/johndoe

SKILLS
Python, FastAPI, PostgreSQL, Docker, LangChain, FAISS, basic PyTorch, Git, Linux

EXPERIENCE
Backend Engineer — TechCorp (2021–2024)
- Built REST APIs serving 50k daily users with FastAPI and PostgreSQL
- Reduced API latency by 35% via query optimisation and Redis caching
- Built a document Q&A tool using LangChain + FAISS (used by 200 internal users)
- Mentored 2 junior engineers

PROJECTS
AI Job Agent (2024) — Multi-agent system using CrewAI, LangChain, FAISS, Groq

EDUCATION
B.Tech Computer Science — University of Mumbai (2021) | GPA: 8.5/10
"""
    result = tailor_resume(job, resume_text=resume)
    print(result)
