"""
agents/decision_agent.py
------------------------
Decision Agent — scores each job against your profile
and recommends apply or skip.

SCORING (0–10):
  Skill match       0–4 pts
  Experience fit    0–2 pts
  Role relevance    0–2 pts
  Growth potential  0–1 pt
  Company signal    0–1 pt

RULE: score >= 6.0 → apply, else skip

PIPELINE POSITION: Step 2
INPUT:  enriched job list from Research Agent
OUTPUT: same list with score + decision added to each job
"""

import json
from config import get_llm

APPLY_THRESHOLD = 5.0   # Lowered from 6.0 — LLMs tend to score conservatively


def score_job(job: dict, candidate_profile: str, llm=None) -> dict:
    """
    Score a single job against the candidate profile.

    Returns a dict with:
        relevance_score, decision, decision_reason,
        matching_skills, missing_skills
    """
    if llm is None:
        llm = get_llm()

    required_skills  = job.get("required_skills", [])
    nice_to_have     = job.get("nice_to_have", [])
    exp_years        = job.get("experience_years", 0)
    exp_level        = job.get("experience_level", "unknown")
    title            = job.get("title") or job.get("job_title", "")
    company          = job.get("company", "")

    prompt = f"""You are a helpful career coach. Your job is to find good matches between candidates and jobs.
Be GENEROUS and ENCOURAGING in your scoring — if someone has most of the skills, that is a good match.

CANDIDATE PROFILE:
{candidate_profile}

JOB TO EVALUATE:
- Title: {title}
- Company: {company}
- Required skills: {required_skills}
- Nice to have: {nice_to_have}
- Experience needed: {exp_years} years ({exp_level} level)

SCORING GUIDE (be generous — partial matches count!):
- Skill match (0-4 pts): Give 4 if they have 80%+ of skills, 3 if 60%+, 2 if 40%+, 1 if 20%+
- Experience fit (0-2 pts): Give 2 if close to required years, 1 if within 1-2 years
- Role relevance (0-2 pts): Give 2 if role aligns with their background, 1 if somewhat related
- Growth potential (0-1 pt): Give 1 if this is a realistic career step
- Company signal (0-1 pt): Give 1 if company sounds legitimate

IMPORTANT: A score of 5 or above means APPLY. Most candidates with relevant experience should score 5+.

Return ONLY this JSON object, nothing else, no markdown fences:
{{"relevance_score": 7.0, "decision": "apply", "decision_reason": "Candidate has strong Python and FastAPI skills matching the role.", "matching_skills": ["Python", "FastAPI"], "missing_skills": ["Kubernetes"]}}

Now score the job above for the candidate. Return only the JSON:"""

    try:
        response = llm.invoke(prompt)

        # Handle both string and object responses
        if hasattr(response, "content"):
            content = response.content
        else:
            content = str(response)
        content = content.strip()

        print(f"   [debug] Raw LLM response: {content[:120]}")

        # Strip markdown fences if present
        if "```" in content:
            parts   = content.split("```")
            content = parts[1] if len(parts) > 1 else parts[0]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        # Extract JSON object
        start = content.find("{")
        end   = content.rfind("}") + 1
        if start >= 0 and end > start:
            content = content[start:end]
        else:
            raise ValueError(f"No JSON object in response: {content[:200]}")

        result = json.loads(content)

        # Always enforce threshold — LLM sometimes contradicts itself
        score = float(result.get("relevance_score", 0))
        result["decision"] = "apply" if score >= APPLY_THRESHOLD else "skip"
        return result

    except Exception as e:
        print(f"   [decision_agent] ⚠️ Parse error: {e}")
        # Instead of silently returning 0, do a simple keyword-based fallback
        return _keyword_fallback(job, candidate_profile)


def _keyword_fallback(job: dict, candidate_profile: str) -> dict:
    """
    Simple keyword-match fallback when LLM response can't be parsed.
    Counts how many required skills appear in the candidate profile.
    """
    required = [s.lower() for s in job.get("required_skills", [])]
    profile_lower = candidate_profile.lower()

    matching = [s for s in required if s in profile_lower]
    missing  = [s for s in required if s not in profile_lower]

    if not required:
        score = 5.0
    else:
        ratio = len(matching) / len(required)
        score = round(ratio * 8, 1)   # max 8 from keyword match

    decision = "apply" if score >= APPLY_THRESHOLD else "skip"
    print(f"   [decision_agent] Fallback score: {score}/10 ({len(matching)}/{len(required)} skills matched)")

    return {
        "relevance_score":  score,
        "decision":         decision,
        "decision_reason":  f"Keyword match: {len(matching)}/{len(required)} required skills found in profile.",
        "matching_skills":  [s for s in job.get("required_skills", []) if s.lower() in profile_lower],
        "missing_skills":   missing,
    }


def run_decision(jobs: list[dict], candidate_profile: str, llm=None) -> list[dict]:
    """
    Score all jobs and sort by relevance score descending.

    Args:
        jobs:              Enriched jobs from Research Agent
        candidate_profile: Free-text description of the candidate
        llm:               Optional Groq LLM

    Returns:
        Same jobs list with score+decision added, sorted best first
    """
    if llm is None:
        llm = get_llm()

    print("🎯 Decision Agent: scoring jobs...")
    for job in jobs:
        title = job.get("title") or job.get("job_title", "?")
        print(f"   Scoring: {title} @ {job.get('company', '?')}")
        result = score_job(job, candidate_profile, llm)
        job.update(result)

    jobs.sort(key=lambda j: j.get("relevance_score", 0), reverse=True)

    print("\n   📊 Scores:")
    for j in jobs:
        icon = "✅" if j["decision"] == "apply" else "❌"
        print(f"   {icon} {j.get('title','?')} — {j.get('relevance_score', 0)}/10 → {j['decision']}")
    print()

    return jobs


if __name__ == "__main__":
    profile = "3 years Python, FastAPI, PostgreSQL. Built a RAG chatbot with LangChain. Remote preferred."
    job = {
        "title": "Senior Python Developer",
        "company": "TechCorp",
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes"],
        "nice_to_have": ["Redis"],
        "experience_years": 5,
        "experience_level": "senior",
    }
    result = score_job(job, profile)
    print(json.dumps(result, indent=2))
