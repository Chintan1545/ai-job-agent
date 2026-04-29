"""
crew.py
-------
Main pipeline orchestrator — runs all 5 agents in sequence.

PIPELINE:
  Research Agent  →  finds + enriches jobs
  Decision Agent  →  scores each job, apply/skip
  Resume Agent    →  tailors resume (apply jobs only)
  Cover Letter    →  writes personalised letter
  Application     →  saves to DB with next steps

USAGE:
    python crew.py

    or import and call:
    from crew import run_pipeline
    result = run_pipeline(
        job_query="Python Developer",
        candidate_profile="3 years Python...",
        resume_text="John Doe...",
    )
"""

from config import get_llm
from database import init_db

from agents.researcher         import run_research
from agents.decision_agent     import run_decision
from agents.resume_agent       import tailor_resume
from agents.cover_letter_agent import generate_cover_letter
from agents.application_agent  import save_application, get_all_applications


def run_pipeline(
    job_query: str,
    location: str = "Remote",
    max_results: int = 5,
    candidate_profile: str = "",
    resume_text: str = None,
    resume_path: str = None,
) -> dict:
    """
    Run the full 5-agent job application pipeline.

    Args:
        job_query:          What role to search for
        location:           Location preference
        max_results:        How many jobs to find and process
        candidate_profile:  Free text about the candidate's background and goals
        resume_text:        Resume as plain text (paste from UI)
        resume_path:        Path to PDF/DOCX file (alternative to resume_text)

    Returns:
        dict with: jobs_found, apply_jobs, skip_jobs, applications
    """
    init_db()
    llm = get_llm()

    print(f"\n{'='*60}")
    print(f"  🤖 AI JOB AGENT — Groq {__import__('config').GROQ_MODEL}")
    print(f"  Query:    {job_query}")
    print(f"  Location: {location}")
    print(f"  Max jobs: {max_results}")
    print(f"{'='*60}\n")

    # ── STEP 1: Research ──────────────────────────────────────────────────────
    enriched_jobs = run_research(job_query, location, max_results, llm=llm)

    # ── STEP 2: Decision ──────────────────────────────────────────────────────
    scored_jobs = run_decision(enriched_jobs, candidate_profile, llm=llm)
    apply_jobs  = [j for j in scored_jobs if j.get("decision") == "apply"]
    skip_jobs   = [j for j in scored_jobs if j.get("decision") == "skip"]

    # ── STEPS 3–5: Resume + Cover Letter + Save (apply jobs only) ─────────────
    applications = []

    for job in apply_jobs:
        title   = job.get("title") or job.get("job_title", "?")
        company = job.get("company", "?")

        print(f"📄 Resume Agent: tailoring for {title} @ {company}...")
        tailored = tailor_resume(job, resume_text=resume_text, resume_path=resume_path, llm=llm)
        job["tailored_resume"] = tailored

        print(f"✍️  Cover Letter Agent: writing letter...")
        cover = generate_cover_letter(job, candidate_profile, tailored_resume=tailored, llm=llm)
        job["cover_letter"] = cover

        print(f"💾 Application Agent: saving to database...")
        record = save_application(job, tailored_resume=tailored, cover_letter=cover)
        applications.append({
            "id":              record.id,
            "job_title":       record.job_title,
            "company":         record.company,
            "relevance_score": record.relevance_score,
            "status":          record.status,
            "next_steps":      record.next_steps,
        })
        print()

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"{'='*60}")
    print(f"  🎉 PIPELINE COMPLETE")
    print(f"  Jobs found : {len(enriched_jobs)}")
    print(f"  Apply      : {len(apply_jobs)}")
    print(f"  Skip       : {len(skip_jobs)}")
    print(f"  DB records : {len(applications)}")
    print(f"{'='*60}\n")

    return {
        "jobs_found":   enriched_jobs,
        "apply_jobs":   apply_jobs,
        "skip_jobs":    skip_jobs,
        "applications": applications,
    }


# ── Run directly for quick testing ───────────────────────────────────────────

if __name__ == "__main__":

    CANDIDATE_PROFILE = """
    I am a backend engineer with 3 years of Python experience.
    Strong in FastAPI, REST APIs, PostgreSQL, and Docker.
    I have built a RAG pipeline using LangChain and FAISS as a side project.
    Currently looking for mid-level backend or ML engineering roles. Remote preferred.
    My goal: move into ML/AI engineering.
    """

    SAMPLE_RESUME = """
    John Doe | john@example.com | github.com/johndoe | linkedin.com/in/johndoe

    SUMMARY
    Backend engineer with 3 years building scalable APIs. Moving into AI/ML engineering.

    SKILLS
    Python, FastAPI, PostgreSQL, Docker, LangChain, FAISS, basic PyTorch, Git, Linux, Redis

    EXPERIENCE
    Backend Engineer — TechCorp (Jan 2021 – Present)
    - Built REST APIs handling 50k daily requests with FastAPI and PostgreSQL
    - Reduced API latency by 35% via query optimisation and Redis caching
    - Built a document Q&A tool using LangChain + FAISS (200 internal users)
    - Mentored 2 junior engineers, reviewed PRs weekly

    PROJECTS
    AI Job Agent (2024) — Multi-agent system using LangChain, FAISS, Groq, FastAPI, Streamlit
    Resume RAG Tool (2023) — Semantic resume search with HuggingFace embeddings + FAISS

    EDUCATION
    B.Tech Computer Science — University of Mumbai (2021) | GPA: 8.5/10
    """

    results = run_pipeline(
        job_query         = "Python Developer",
        location          = "Remote",
        max_results       = 3,
        candidate_profile = CANDIDATE_PROFILE,
        resume_text       = SAMPLE_RESUME,
    )

    if results["applications"]:
        print("📋 Applications created:")
        for a in results["applications"]:
            print(f"  [{a['id']}] {a['job_title']} @ {a['company']} — {a['relevance_score']}/10")
