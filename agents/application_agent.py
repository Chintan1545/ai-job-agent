"""
agents/application_agent.py
----------------------------
Application Agent — saves applications to the database,
tracks status, and generates next steps at each stage.

STATUS FLOW:
  pending → applied → interview → offer → rejected

PIPELINE POSITION: Step 5 (final agent)
INPUT:  job dict + tailored resume + cover letter
OUTPUT: saved DB record + next steps
"""

import json
from datetime import datetime
from sqlalchemy.orm import Session
from database import JobApplication, SessionLocal


# ── Next steps by status ──────────────────────────────────────────────────────

NEXT_STEPS = {
    "pending": (
        "1. Review your tailored resume and cover letter carefully.\n"
        "2. Apply via the company's careers portal or LinkedIn.\n"
        "3. Send a personalised connection request to the recruiter on LinkedIn.\n"
        "4. Update status to 'applied' once submitted."
    ),
    "applied": (
        "1. Connect with the recruiter or hiring manager on LinkedIn.\n"
        "2. Follow up via email in 5-7 business days if no response.\n"
        "3. Prepare 3-5 STAR method stories relevant to this role.\n"
        "4. Research the company: products, recent news, team structure."
    ),
    "interview": (
        "1. Deep dive: company website, Glassdoor, LinkedIn team pages.\n"
        "2. Prepare answers to: 'Tell me about yourself', 'Why this company?'.\n"
        "3. Prepare 5 STAR stories covering: leadership, conflict, impact, failure, teamwork.\n"
        "4. Prepare 3-5 thoughtful questions for the interviewer.\n"
        "5. Send a thank-you email within 24 hours of each round."
    ),
    "offer": (
        "1. Research market salary: Levels.fyi, Glassdoor, LinkedIn Salary Insights.\n"
        "2. Do NOT accept immediately — ask for 24-48 hours to review.\n"
        "3. Negotiate: base salary, equity, signing bonus, remote flexibility.\n"
        "4. Read the full offer letter carefully before signing."
    ),
    "rejected": (
        "1. Send a polite thank-you reply to the recruiter.\n"
        "2. Ask for specific feedback if possible — most will share.\n"
        "3. Note any skill gaps mentioned and add them to your learning plan.\n"
        "4. Mark this company to revisit in 6-12 months."
    ),
}


# ── Database operations ───────────────────────────────────────────────────────

def save_application(
    job: dict,
    tailored_resume: str = "",
    cover_letter: str = "",
    db: Session = None,
) -> JobApplication:
    """
    Save a job application to the SQLite database.

    Args:
        job:            Job dict (with score, decision, skills etc.)
        tailored_resume: Markdown resume string
        cover_letter:   Plain text cover letter
        db:             Optional DB session (created if not provided)

    Returns:
        The saved JobApplication ORM object
    """
    close_db = False
    if db is None:
        db       = SessionLocal()
        close_db = True

    try:
        app = JobApplication(
            job_title        = job.get("title") or job.get("job_title", ""),
            company          = job.get("company", ""),
            job_url          = job.get("url", ""),
            job_description  = job.get("description", "")[:2000],
            required_skills  = json.dumps(job.get("required_skills", [])),
            experience_level = job.get("experience_level", ""),
            relevance_score  = float(job.get("relevance_score", 0)),
            decision         = job.get("decision", "pending"),
            decision_reason  = job.get("decision_reason", ""),
            tailored_resume  = tailored_resume,
            cover_letter     = cover_letter,
            status           = "pending",
            next_steps       = NEXT_STEPS["pending"],
        )
        db.add(app)
        db.commit()
        db.refresh(app)
        print(f"   💾 Saved: {app.job_title} @ {app.company} (id={app.id})")
        return app
    finally:
        if close_db:
            db.close()


def update_status(
    app_id: int,
    new_status: str,
    notes: str = "",
    db: Session = None,
) -> JobApplication:
    """Update status of an application and regenerate next steps."""
    valid = ["pending", "applied", "interview", "offer", "rejected"]
    if new_status not in valid:
        raise ValueError(f"Invalid status '{new_status}'. Choose from {valid}")

    close_db = False
    if db is None:
        db       = SessionLocal()
        close_db = True

    try:
        app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
        if not app:
            raise ValueError(f"Application id={app_id} not found.")
        app.status     = new_status
        app.next_steps = NEXT_STEPS.get(new_status, "")
        app.updated_at = datetime.utcnow()
        if notes:
            app.notes  = notes
        db.commit()
        db.refresh(app)
        return app
    finally:
        if close_db:
            db.close()


def get_all_applications(db: Session = None) -> list[dict]:
    """Return all applications sorted by score descending."""
    close_db = False
    if db is None:
        db       = SessionLocal()
        close_db = True
    try:
        apps = db.query(JobApplication).order_by(
            JobApplication.relevance_score.desc()
        ).all()
        return [_to_dict(a) for a in apps]
    finally:
        if close_db:
            db.close()


def get_application(app_id: int, db: Session = None) -> dict:
    close_db = False
    if db is None:
        db       = SessionLocal()
        close_db = True
    try:
        app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
        return _to_dict(app) if app else {}
    finally:
        if close_db:
            db.close()


def delete_application(app_id: int, db: Session = None) -> bool:
    close_db = False
    if db is None:
        db       = SessionLocal()
        close_db = True
    try:
        app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
        if not app:
            return False
        db.delete(app)
        db.commit()
        return True
    finally:
        if close_db:
            db.close()


def _to_dict(app: JobApplication) -> dict:
    if not app:
        return {}
    return {
        "id":               app.id,
        "job_title":        app.job_title,
        "company":          app.company,
        "job_url":          app.job_url,
        "required_skills":  json.loads(app.required_skills or "[]"),
        "experience_level": app.experience_level,
        "relevance_score":  app.relevance_score,
        "decision":         app.decision,
        "decision_reason":  app.decision_reason,
        "tailored_resume":  app.tailored_resume,
        "cover_letter":     app.cover_letter,
        "status":           app.status,
        "next_steps":       app.next_steps,
        "notes":            app.notes,
        "created_at":       str(app.created_at),
        "updated_at":       str(app.updated_at),
    }


if __name__ == "__main__":
    from database import init_db
    init_db()

    test_job = {
        "title": "ML Engineer",
        "company": "AI Startup",
        "url": "https://example.com/jobs/2",
        "required_skills": ["Python", "PyTorch", "LangChain"],
        "experience_level": "mid",
        "relevance_score": 8.0,
        "decision": "apply",
        "decision_reason": "Strong Python + LangChain match.",
    }
    app = save_application(test_job, tailored_resume="# Resume...", cover_letter="Dear HM...")
    print(f"Saved id={app.id}")

    all_apps = get_all_applications()
    print(f"Total in DB: {len(all_apps)}")
