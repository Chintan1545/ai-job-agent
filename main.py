"""
main.py
-------
FastAPI backend — REST API for the AI Job Agent.

ENDPOINTS:
  POST /run-pipeline              Trigger the full 5-agent pipeline
  GET  /pipeline-status/{job_id}  Poll pipeline progress
  GET  /applications              List all saved applications
  GET  /applications/{id}         Get full application details
  PUT  /applications/{id}/status  Update application status
  DELETE /applications/{id}       Delete an application
  GET  /health                    Health check

RUN:
  uvicorn main:app --reload --port 8000
  Open: http://localhost:8000/docs
"""

import uuid
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from database import init_db, get_db, JobApplication
from crew     import run_pipeline
from agents.application_agent import (
    get_all_applications,
    get_application,
    update_status,
    delete_application,
)
from config import APP_HOST, APP_PORT, DEBUG, GROQ_MODEL


# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "AI Job Application Agent",
    description = f"Multi-agent system powered by Groq ({GROQ_MODEL})",
    version     = "1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline_jobs: dict = {}   # in-memory job tracker


@app.on_event("startup")
def startup():
    init_db()
    print(f"✅ DB ready | Model: {GROQ_MODEL}")


# ── Request / Response schemas ────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    job_query:         str
    location:          str          = "Remote"
    max_results:       int          = 5
    candidate_profile: str          = ""
    resume_text:       Optional[str] = None


class StatusRequest(BaseModel):
    status: str
    notes:  Optional[str] = None


# ── Pipeline endpoints ────────────────────────────────────────────────────────

@app.post("/run-pipeline")
async def start_pipeline(req: PipelineRequest, bg: BackgroundTasks):
    """
    Start the 5-agent pipeline as a background task.
    Returns a job_id immediately — poll /pipeline-status/{job_id} for progress.
    """
    job_id = str(uuid.uuid4())[:8]
    pipeline_jobs[job_id] = {"status": "running", "result": None}

    def _run():
        try:
            result = run_pipeline(
                job_query         = req.job_query,
                location          = req.location,
                max_results       = req.max_results,
                candidate_profile = req.candidate_profile,
                resume_text       = req.resume_text,
            )
            pipeline_jobs[job_id] = {
                "status": "done",
                "result": {
                    "jobs_found":   len(result["jobs_found"]),
                    "apply_count":  len(result["apply_jobs"]),
                    "skip_count":   len(result["skip_jobs"]),
                    "applications": result["applications"],
                },
            }
        except Exception as e:
            pipeline_jobs[job_id] = {"status": "error", "error": str(e)}

    bg.add_task(_run)
    return {
        "job_id":  job_id,
        "message": f"Pipeline started. Poll /pipeline-status/{job_id}",
    }


@app.get("/pipeline-status/{job_id}")
def pipeline_status(job_id: str):
    if job_id not in pipeline_jobs:
        raise HTTPException(404, detail="Job ID not found.")
    return pipeline_jobs[job_id]


# ── Application CRUD ──────────────────────────────────────────────────────────

@app.get("/applications")
def list_applications(db: Session = Depends(get_db)):
    apps = get_all_applications(db=db)
    # Truncate heavy fields for list view
    for a in apps:
        if a.get("tailored_resume"):
            a["tailored_resume"] = a["tailored_resume"][:200] + "..."
        if a.get("cover_letter"):
            a["cover_letter"] = a["cover_letter"][:200] + "..."
    return {"count": len(apps), "applications": apps}


@app.get("/applications/{app_id}")
def get_one_application(app_id: int, db: Session = Depends(get_db)):
    app = get_application(app_id, db=db)
    if not app:
        raise HTTPException(404, detail=f"Application {app_id} not found.")
    return app


@app.put("/applications/{app_id}/status")
def update_application_status(
    app_id: int,
    req: StatusRequest,
    db: Session = Depends(get_db),
):
    try:
        updated = update_status(app_id, req.status, notes=req.notes or "", db=db)
        return {
            "id":         updated.id,
            "status":     updated.status,
            "next_steps": updated.next_steps,
        }
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


@app.delete("/applications/{app_id}")
def remove_application(app_id: int, db: Session = Depends(get_db)):
    success = delete_application(app_id, db=db)
    if not success:
        raise HTTPException(404, detail="Not found.")
    return {"message": f"Application {app_id} deleted."}


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "model":  GROQ_MODEL,
        "debug":  DEBUG,
    }


# ── Run directly ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=APP_HOST, port=APP_PORT, reload=DEBUG)
