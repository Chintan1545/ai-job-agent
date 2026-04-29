"""
agents/researcher.py
--------------------
Research Agent — finds jobs and extracts structured requirements
from each job description using Groq LLaMA.

PIPELINE POSITION: Step 1
INPUT:  job query string + location
OUTPUT: list of enriched job dicts with extracted skills/requirements
"""

import json
from config import get_llm
from tools.job_scraper import search_jobs


def extract_job_requirements(job_description: str, llm=None) -> dict:
    """
    Use Groq LLaMA to extract structured requirements from a job description.

    Returns a dict with:
        required_skills, nice_to_have, experience_years,
        experience_level, key_responsibilities
    """
    if llm is None:
        llm = get_llm()

    prompt = f"""You are a job analyst. Extract structured data from this job description.

Job Description:
{job_description[:2000]}

Return ONLY a valid JSON object with these exact keys (no explanation, no markdown):
{{
  "required_skills": ["skill1", "skill2"],
  "nice_to_have": ["skill3"],
  "experience_years": 3,
  "experience_level": "mid",
  "key_responsibilities": ["responsibility 1", "responsibility 2", "responsibility 3"]
}}

Rules:
- experience_level must be one of: junior, mid, senior
- required_skills: only hard technical requirements
- nice_to_have: optional/bonus skills mentioned
- key_responsibilities: exactly 3 bullet points, short"""

    try:
        response = llm.invoke(prompt)
        content  = response.content.strip()

        # Strip markdown code fences if Groq adds them
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        # Find JSON object in response
        start = content.find("{")
        end   = content.rfind("}") + 1
        if start >= 0 and end > start:
            content = content[start:end]

        return json.loads(content)

    except Exception as e:
        print(f"[researcher] Parse error: {e}")
        return {
            "required_skills": [],
            "nice_to_have": [],
            "experience_years": 0,
            "experience_level": "unknown",
            "key_responsibilities": [],
        }


def run_research(
    job_query: str,
    location: str = "Remote",
    max_results: int = 5,
    llm=None,
) -> list[dict]:
    """
    Find jobs and enrich each one with extracted requirements.

    Args:
        job_query:   Search query, e.g. "Python Developer"
        location:    Location string
        max_results: Number of jobs to find
        llm:         Optional Groq LLM instance

    Returns:
        List of enriched job dicts
    """
    if llm is None:
        llm = get_llm()

    print(f"\n🔍 Research Agent: searching for '{job_query}' in '{location}'...")
    raw_jobs = search_jobs(job_query, location=location, max_results=max_results)

    enriched = []
    for job in raw_jobs:
        print(f"   Extracting requirements: {job['title']} @ {job['company']}")
        requirements = extract_job_requirements(job.get("description", ""), llm=llm)
        job.update(requirements)
        enriched.append(job)

    print(f"   ✅ Enriched {len(enriched)} jobs.\n")
    return enriched


if __name__ == "__main__":
    sample_desc = """
    We need a Python Developer with 3+ years experience.
    Required: Python, FastAPI, PostgreSQL, Docker.
    Nice to have: Kubernetes, Redis.
    You'll build microservices for our fintech platform.
    """
    result = extract_job_requirements(sample_desc)
    print(json.dumps(result, indent=2))
