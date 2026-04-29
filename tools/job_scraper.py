"""
tools/job_scraper.py
--------------------
Scrapes job listings from Indeed.
Returns mock data when DEBUG=true so you can build and test
without hitting rate limits or needing real job sites.

USAGE:
    from tools.job_scraper import search_jobs
    jobs = search_jobs("Python Developer", location="Remote", max_results=5)
"""

import re
import time
import random
import requests
from bs4 import BeautifulSoup
from typing import Optional
from config import DEBUG


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

# ── Mock data (used when DEBUG=true) ─────────────────────────────────────────
MOCK_JOBS = [
    {
        "title": "Senior Python Developer",
        "company": "TechCorp Inc.",
        "location": "Remote",
        "url": "https://example.com/jobs/1",
        "description": (
            "We are looking for a Senior Python Developer with 5+ years experience. "
            "Required: Python, FastAPI, PostgreSQL, Docker, AWS. "
            "Nice to have: Kubernetes, Redis, GraphQL. "
            "Build scalable microservices and mentor junior engineers."
        ),
    },
    {
        "title": "ML Engineer",
        "company": "AI Startup",
        "location": "San Francisco, CA",
        "url": "https://example.com/jobs/2",
        "description": (
            "Join our ML team! Required: Python, PyTorch, scikit-learn, "
            "experience deploying ML models to production. "
            "Familiarity with LLMs, RAG pipelines, and vector databases a big plus. "
            "3+ years of experience required."
        ),
    },
    {
        "title": "Backend Engineer",
        "company": "FinTech Co.",
        "location": "New York, NY",
        "url": "https://example.com/jobs/3",
        "description": (
            "Backend Engineer for our payments platform. "
            "Required: Python or Go, REST APIs, SQL, microservices. "
            "Experience with high-throughput systems preferred. "
            "2-4 years of experience."
        ),
    },
    {
        "title": "Data Engineer",
        "company": "DataFlow Inc.",
        "location": "Remote",
        "url": "https://example.com/jobs/4",
        "description": (
            "Data Engineer to build and maintain data pipelines. "
            "Required: Python, Apache Spark, SQL, Airflow, AWS S3. "
            "Nice to have: dbt, Snowflake, Kafka. "
            "4+ years experience in data engineering."
        ),
    },
    {
        "title": "DevOps Engineer",
        "company": "CloudSystems",
        "location": "Remote",
        "url": "https://example.com/jobs/5",
        "description": (
            "DevOps Engineer to manage our cloud infrastructure. "
            "Required: Kubernetes, Docker, Terraform, AWS, CI/CD. "
            "Python scripting skills a must. "
            "3+ years DevOps experience."
        ),
    },
]


# ── Indeed scraper ────────────────────────────────────────────────────────────

def scrape_indeed(query: str, location: str, max_results: int = 10) -> list[dict]:
    jobs  = []
    start = 0
    while len(jobs) < max_results:
        url = (
            f"https://www.indeed.com/jobs"
            f"?q={query.replace(' ', '+')}"
            f"&l={location.replace(' ', '+')}"
            f"&start={start}"
        )
        try:
            resp  = requests.get(url, headers=HEADERS, timeout=10)
            soup  = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_=re.compile("job_seen_beacon"))
            if not cards:
                break
            for card in cards:
                title_el   = card.find("h2", class_=re.compile("jobTitle"))
                company_el = card.find("span", {"data-testid": "company-name"})
                loc_el     = card.find("div",  {"data-testid": "text-location"})
                link_el    = card.find("a", href=True)
                if not title_el:
                    continue
                jobs.append({
                    "title":       title_el.get_text(strip=True),
                    "company":     company_el.get_text(strip=True) if company_el else "Unknown",
                    "location":    loc_el.get_text(strip=True) if loc_el else location,
                    "url":         "https://www.indeed.com" + link_el["href"] if link_el else "",
                    "description": "",
                })
                if len(jobs) >= max_results:
                    break
            start += 10
            time.sleep(random.uniform(1.5, 3.0))
        except Exception as e:
            print(f"[scraper] Error: {e}")
            break
    return jobs


def fetch_job_description(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        desc = soup.find("div", id="jobDescriptionText")
        if not desc:
            desc = soup.find("div", class_=re.compile("description"))
        if not desc:
            desc = soup.find("main")
        return desc.get_text(separator=" ", strip=True)[:3000] if desc else ""
    except Exception as e:
        print(f"[scraper] Could not fetch description: {e}")
        return ""


# ── Public API ─────────────────────────────────────────────────────────────────

def search_jobs(
    query: str,
    location: str = "Remote",
    max_results: int = 5,
    use_mock: Optional[bool] = None,
) -> list[dict]:
    """
    Search for job listings.

    Args:
        query:       Job title / keywords
        location:    Location string
        max_results: Max number of jobs
        use_mock:    Force mock data (defaults to DEBUG env var)

    Returns:
        List of job dicts: {title, company, location, url, description}
    """
    should_mock = use_mock if use_mock is not None else DEBUG

    if should_mock:
        print("[scraper] 🧪 Using mock job data (DEBUG=true)")
        return MOCK_JOBS[:max_results]

    print(f"[scraper] 🔍 Scraping Indeed for '{query}' in '{location}'...")
    jobs = scrape_indeed(query, location, max_results)

    for job in jobs:
        if job["url"] and not job["description"]:
            job["description"] = fetch_job_description(job["url"])
            time.sleep(random.uniform(1.0, 2.0))

    print(f"[scraper] Found {len(jobs)} jobs.")
    return jobs


if __name__ == "__main__":
    results = search_jobs("Python Developer", use_mock=True)
    for j in results:
        print(f"  • {j['title']} @ {j['company']}")
