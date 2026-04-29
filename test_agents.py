"""
test_agents.py
--------------
Test suite for all agents using mock LLM responses.
No API key or network connection needed.

RUN:
    python test_agents.py
"""

import json, sys, os

GREEN = "\033[92m"; RED = "\033[91m"; RESET = "\033[0m"; BOLD = "\033[1m"
passed = 0; failed = 0

def ok(name):
    global passed; passed += 1
    print(f"  {GREEN}✅ PASS{RESET}  {name}")

def fail(name, err):
    global failed; failed += 1
    print(f"  {RED}❌ FAIL{RESET}  {name}")
    print(f"         {RED}{err}{RESET}")

def section(title):
    print(f"\n{BOLD}{title}{RESET}")
    print("  " + "─" * 52)


# ── Mock LLM ──────────────────────────────────────────────────────────────────
# IMPORTANT: condition order matters — check most specific prompts first.
# The decision agent prompt includes job JSON with required_skills/experience_level,
# so we must match it BEFORE the researcher condition.

class MockLLM:
    """Returns valid JSON for any agent prompt. Order of conditions is critical."""
    def invoke(self, prompt):
        class R:
            def __init__(self, prompt):
                # ── Decision agent ──
                # Unique string that ONLY appears in decision_agent.py's prompt
                if "Score out of 10 using this rubric" in prompt:
                    self.content = json.dumps({
                        "relevance_score": 7.5,
                        "decision": "apply",
                        "decision_reason": "Strong Python and FastAPI match.",
                        "matching_skills": ["Python", "FastAPI"],
                        "missing_skills": ["Docker"]
                    })
                # ── Researcher agent ──
                # Unique string that ONLY appears in researcher.py's prompt
                elif "job analyst" in prompt.lower():
                    self.content = json.dumps({
                        "required_skills": ["Python", "FastAPI", "PostgreSQL"],
                        "nice_to_have": ["Docker", "Redis"],
                        "experience_years": 3,
                        "experience_level": "mid",
                        "key_responsibilities": ["Build REST APIs", "Design databases", "Write tests"]
                    })
                # ── Cover letter agent ──
                elif "cover letter" in prompt.lower():
                    self.content = (
                        "Dear Hiring Manager,\n\nYour work at AI Startup caught my attention. "
                        "With 3 years of Python and FastAPI experience, I built a RAG pipeline "
                        "serving 200 users at TechCorp.\n\n"
                        "I'd love to discuss this role.\n\nSincerely,\nJohn Doe"
                    )
                # ── Resume agent (default) ──
                else:
                    self.content = (
                        "# John Doe\njohn@example.com\n\n"
                        "## Skills\nPython, FastAPI, PostgreSQL\n\n"
                        "## Experience\nBackend Engineer — TechCorp (2021–2024)\n"
                        "- Built REST APIs with FastAPI serving 50k daily users\n\n"
                        "## Education\nB.Tech CS, 2021"
                    )
        return R(prompt)


MOCK = MockLLM()


# ══════════════════════════════════════════════════════════════════════════════
section("1. config.py")

try:
    import config
    assert hasattr(config, "get_llm"), "missing get_llm"
    assert hasattr(config, "GROQ_MODEL"), "missing GROQ_MODEL"
    assert hasattr(config, "DATABASE_URL"), "missing DATABASE_URL"
    ok("Config imports and has all required attributes")
except Exception as e:
    fail("config imports", e)


# ══════════════════════════════════════════════════════════════════════════════
section("2. database.py")

try:
    import database
    database.init_db()
    ok("database.init_db() runs without error")
except Exception as e:
    fail("init_db", e)

try:
    from database import JobApplication, SessionLocal
    db = SessionLocal()
    count = db.query(JobApplication).count()
    db.close()
    ok(f"DB query works — {count} existing records")
except Exception as e:
    fail("DB query", e)


# ══════════════════════════════════════════════════════════════════════════════
section("3. tools/job_scraper.py (mock mode)")

try:
    from tools.job_scraper import search_jobs
    jobs = search_jobs("Python Developer", use_mock=True, max_results=3)
    assert isinstance(jobs, list), "not a list"
    assert len(jobs) > 0, "empty list"
    ok(f"search_jobs returns {len(jobs)} mock jobs")
except Exception as e:
    fail("search_jobs mock", e)

try:
    for j in jobs:
        assert "title" in j and "company" in j and "description" in j
    ok("All jobs have required keys (title, company, description)")
except Exception as e:
    fail("job structure", e)


# ══════════════════════════════════════════════════════════════════════════════
section("4. agents/researcher.py (mock LLM)")

try:
    from agents.researcher import extract_job_requirements
    result = extract_job_requirements("Need Python developer with FastAPI.", llm=MOCK)
    assert "required_skills" in result, f"missing required_skills, got: {result}"
    assert "experience_level" in result
    assert isinstance(result["required_skills"], list)
    ok(f"extract_job_requirements → skills: {result['required_skills']}")
except Exception as e:
    fail("extract_job_requirements", e)

try:
    from agents.researcher import run_research
    enriched = run_research("Python Developer", max_results=2, llm=MOCK)
    assert len(enriched) == 2
    assert "required_skills" in enriched[0]
    ok(f"run_research enriches {len(enriched)} jobs")
except Exception as e:
    fail("run_research", e)


# ══════════════════════════════════════════════════════════════════════════════
section("5. agents/decision_agent.py (mock LLM)")

try:
    from agents.decision_agent import score_job, APPLY_THRESHOLD
    sample_job = {
        "title": "Backend Engineer",
        "company": "TestCo",
        "required_skills": ["Python", "FastAPI", "Docker"],
        "experience_years": 3,
        "experience_level": "mid",
    }
    result = score_job(sample_job, "3 years Python, FastAPI.", llm=MOCK)
    assert "relevance_score" in result, f"missing relevance_score, got: {result}"
    assert result["decision"] in ("apply", "skip")
    assert 0 <= result["relevance_score"] <= 10
    ok(f"score_job: {result['relevance_score']}/10 → {result['decision']}")
except Exception as e:
    fail("score_job", e)

try:
    class LowScoreMock:
        def invoke(self, p):
            class R:
                content = json.dumps({"relevance_score": 3.0, "decision": "apply",
                                      "decision_reason": "test", "matching_skills": [], "missing_skills": []})
            return R()
    result = score_job(sample_job, "profile", llm=LowScoreMock())
    assert result["decision"] == "skip", "low score not overridden to skip"
    ok("Threshold enforcement: score=3.0 correctly forced to 'skip'")
except Exception as e:
    fail("threshold enforcement", e)

try:
    from agents.decision_agent import run_decision
    jobs_to_score = [
        {"title": "Python Dev", "company": "A", "required_skills": ["Python"], "experience_years": 3, "experience_level": "mid"},
        {"title": "Go Dev",     "company": "B", "required_skills": ["Go"],     "experience_years": 5, "experience_level": "senior"},
    ]
    scored = run_decision(jobs_to_score, "Python developer", llm=MOCK)
    assert len(scored) == 2
    assert scored[0]["relevance_score"] >= scored[1]["relevance_score"]
    ok(f"run_decision returns {len(scored)} scored jobs, sorted by score")
except Exception as e:
    fail("run_decision", e)


# ══════════════════════════════════════════════════════════════════════════════
section("6. agents/resume_agent.py (mock LLM)")

try:
    from agents.resume_agent import tailor_resume
    job = {
        "title": "ML Engineer", "company": "AI Startup",
        "required_skills": ["Python", "FastAPI", "LangChain"],
        "nice_to_have": ["Redis"],
        "key_responsibilities": ["Build ML APIs", "Deploy models", "Write tests"],
    }
    result = tailor_resume(job, resume_text="John Doe. Python dev. 3 years.", llm=MOCK)
    assert isinstance(result, str)
    assert len(result) > 50
    ok(f"tailor_resume returns {len(result)} char resume")
except Exception as e:
    fail("tailor_resume", e)


# ══════════════════════════════════════════════════════════════════════════════
section("7. agents/cover_letter_agent.py (mock LLM)")

try:
    from agents.cover_letter_agent import generate_cover_letter
    job = {
        "title": "ML Engineer", "company": "AI Startup",
        "required_skills": ["Python", "LangChain"],
        "matching_skills": ["Python", "LangChain"],
        "decision_reason": "Strong match.",
    }
    result = generate_cover_letter(job, "3 years Python. Built RAG systems.", llm=MOCK)
    assert "Dear Hiring Manager" in result
    assert "Sincerely" in result
    assert len(result.split()) > 20
    ok(f"generate_cover_letter returns {len(result.split())} word letter")
except Exception as e:
    fail("generate_cover_letter", e)


# ══════════════════════════════════════════════════════════════════════════════
section("8. agents/application_agent.py (database ops)")

try:
    from agents.application_agent import save_application
    test_job = {
        "title": "Test Role", "company": "TestCorp",
        "url": "https://example.com",
        "description": "A test job.",
        "required_skills": ["Python"],
        "experience_level": "mid",
        "relevance_score": 7.5,
        "decision": "apply",
        "decision_reason": "Good match.",
    }
    saved = save_application(test_job, tailored_resume="# CV", cover_letter="Dear HM,")
    assert saved.id is not None
    assert saved.job_title == "Test Role"
    ok(f"save_application creates record id={saved.id}")
except Exception as e:
    fail("save_application", e)

try:
    from agents.application_agent import get_all_applications
    all_apps = get_all_applications()
    assert len(all_apps) > 0
    ok(f"get_all_applications returns {len(all_apps)} record(s)")
except Exception as e:
    fail("get_all_applications", e)

try:
    from agents.application_agent import update_status
    updated = update_status(saved.id, "applied", notes="Submitted via portal")
    assert updated.status == "applied"
    ok("update_status changes status to 'applied'")
except Exception as e:
    fail("update_status", e)

try:
    from agents.application_agent import NEXT_STEPS
    for status in ["pending", "applied", "interview", "offer", "rejected"]:
        assert status in NEXT_STEPS, f"Missing next steps for {status}"
    ok("NEXT_STEPS defined for all 5 statuses")
except Exception as e:
    fail("NEXT_STEPS completeness", e)


# ══════════════════════════════════════════════════════════════════════════════
section("9. Full pipeline end-to-end (all mocked)")

try:
    import config
    original = config.get_llm
    config.get_llm = lambda: MOCK

    from crew import run_pipeline
    result = run_pipeline(
        job_query         = "Python Developer",
        location          = "Remote",
        max_results       = 2,
        candidate_profile = "3 years Python, FastAPI. Looking for backend roles.",
        resume_text       = "John Doe. Python, FastAPI. 3 years experience.",
    )
    assert "jobs_found"   in result
    assert "apply_jobs"   in result
    assert "skip_jobs"    in result
    assert "applications" in result
    assert len(result["jobs_found"]) == 2
    ok(f"Full pipeline: {len(result['jobs_found'])} found, "
       f"{len(result['apply_jobs'])} apply, "
       f"{len(result['applications'])} saved")

    config.get_llm = original
except Exception as e:
    fail("Full pipeline", e)
    try: config.get_llm = original
    except: pass


# ══════════════════════════════════════════════════════════════════════════════
total = passed + failed
print(f"\n{'═'*56}")
print(f"{BOLD}  Results: {GREEN}{passed} passed{RESET}{BOLD}  {RED}{failed} failed{RESET}{BOLD}  {total} total{RESET}")
print(f"{'═'*56}\n")

if failed:
    print(f"  Fix the failing tests before deploying.\n")
    sys.exit(1)
else:
    print(f"  {GREEN}All tests passed! Ready to deploy.{RESET}\n")
    sys.exit(0)
