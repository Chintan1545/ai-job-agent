"""
app.py
------
Streamlit UI — works locally and on Hugging Face Spaces.

On HF Spaces:
  Streamlit runs on port 7860 (public-facing)
  FastAPI runs on port 8000 (internal, same container)
  Both started by supervisord

RUN LOCALLY:
  streamlit run app.py
  Then open: http://localhost:8501
"""

import os
import streamlit as st
import requests
import time

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title = "AI Job Agent",
    page_icon  = "🤖",
    layout     = "wide",
)

st.markdown("""
<style>
.block-container { padding-top: 1.5rem; }
.metric-label { font-size: 13px !important; }
div[data-testid="stExpander"] { border: 1px solid rgba(128,128,128,0.2); border-radius: 8px; margin-bottom: 8px; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def api_ok() -> bool:
    try:
        return requests.get(f"{API_BASE}/health", timeout=3).status_code == 200
    except Exception:
        return False


def get_model_name() -> str:
    try:
        return requests.get(f"{API_BASE}/health", timeout=3).json().get("model", "Groq")
    except Exception:
        return "Groq"


STATUS_ICON  = {"pending": "🟡", "applied": "🔵", "interview": "🟣", "offer": "🟢", "rejected": "🔴"}
STATUS_LIST  = ["pending", "applied", "interview", "offer", "rejected"]


# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.title("🤖 AI Job Agent")
st.sidebar.caption(f"Powered by {get_model_name()}")
st.sidebar.divider()

page = st.sidebar.radio(
    "Go to",
    ["🔍 Find Jobs", "📋 My Applications", "📖 How It Works"],
    label_visibility="collapsed",
)

st.sidebar.divider()
st.sidebar.markdown("**Stack**")
st.sidebar.markdown("Groq · LangChain · FAISS · FastAPI · Streamlit")
st.sidebar.markdown("**[GitHub](https://github.com/yourname/ai-job-agent)**")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — Find Jobs (Run Pipeline)
# ══════════════════════════════════════════════════════════════════════════════

if page == "🔍 Find Jobs":

    st.title("🔍 Find & Apply to Jobs")
    st.caption("5 AI agents will search, score, tailor, and track your applications automatically.")

    if not api_ok():
        st.warning(
            "⚠️ FastAPI backend not running. "
            "Start it with: `uvicorn main:app --reload --port 8000`"
        )

    col1, col2 = st.columns([3, 1])

    with col1:
        job_query = st.text_input(
            "What role are you looking for?",
            placeholder="e.g. Python Developer, ML Engineer, Backend Engineer",
        )
        candidate_profile = st.text_area(
            "Your profile (the agents use this to score jobs)",
            height=130,
            placeholder=(
                "e.g. 3 years Python experience, strong in FastAPI and PostgreSQL. "
                "Built a RAG chatbot using LangChain. "
                "Looking for mid-level backend or ML engineering roles. Remote preferred. "
                "Goal: move into ML/AI engineering."
            ),
        )
        resume_text = st.text_area(
            "Paste your resume (plain text)",
            height=200,
            placeholder=(
                "Paste your full resume here.\n\n"
                "The Resume Agent will use FAISS semantic search to find the most relevant "
                "sections and tailor them for each job with ATS keywords."
            ),
        )

    with col2:
        st.markdown("#### Settings")
        location    = st.text_input("Location", value="Remote")
        max_results = st.slider("Jobs to search", 1, 10, 5)
        st.divider()
        st.markdown("#### Pipeline")
        for s in ["🔍 Research", "🎯 Decision", "📄 Resume", "✍️ Cover Letter", "💾 Save"]:
            st.markdown(f"<small>{s}</small>", unsafe_allow_html=True)

    st.divider()

    if st.button("🚀 Run Agent Pipeline", type="primary", disabled=not job_query, use_container_width=True):

        if not candidate_profile.strip():
            st.warning("Please add your profile so agents can score jobs accurately.")
            st.stop()

        if not resume_text.strip():
            st.warning("Please paste your resume so the Resume Agent can tailor it.")
            st.stop()

        # Start pipeline
        try:
            resp   = requests.post(f"{API_BASE}/run-pipeline", json={
                "job_query":         job_query,
                "location":          location,
                "max_results":       max_results,
                "candidate_profile": candidate_profile,
                "resume_text":       resume_text,
            })
            job_id = resp.json().get("job_id")
        except Exception as e:
            st.error(f"Cannot connect to API: {e}")
            st.stop()

        # Progress display
        prog   = st.progress(0)
        status = st.empty()
        steps  = [
            "🔍 Research Agent: searching job listings...",
            "🎯 Decision Agent: scoring job relevance...",
            "📄 Resume Agent: tailoring your resume...",
            "✍️  Cover Letter Agent: writing personalised letters...",
            "💾 Application Agent: saving to database...",
        ]
        for i, txt in enumerate(steps):
            status.info(txt)
            prog.progress((i + 1) * 15)
            time.sleep(0.7)

        # Poll for completion
        done = False
        for _ in range(120):
            try:
                s = requests.get(f"{API_BASE}/pipeline-status/{job_id}").json()
                if s["status"] == "done":
                    r = s["result"]
                    prog.progress(100)
                    status.empty()
                    st.balloons()
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Jobs Found",  r["jobs_found"])
                    c2.metric("✅ Apply",     r["apply_count"])
                    c3.metric("❌ Skip",      r["skip_count"])
                    if r["apply_count"] > 0:
                        st.success(f"Done! Created {r['apply_count']} tailored application(s). Go to **My Applications** ↓")
                    else:
                        st.warning("All jobs scored below the apply threshold (5.0/10).")
                        st.markdown("""
**3 quick fixes:**

1. **Be specific in your profile** — list exact skills and years:
   > *3 years Python, FastAPI daily, PostgreSQL, Docker basics. Built a LangChain RAG chatbot.*

2. **Broaden your query** — try  instead of 

3. **Check terminal** — look for  to see what Groq returned
""")
                    done = True
                    break
                elif s["status"] == "error":
                    st.error(f"Pipeline error: {s.get('error')}")
                    done = True
                    break
            except Exception:
                pass
            time.sleep(2)

        if not done:
            st.warning("Pipeline is taking longer than expected. Check the terminal for errors.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — My Applications
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📋 My Applications":

    st.title("📋 My Applications")

    if not api_ok():
        st.error("API not reachable. Start the backend first.")
        st.stop()

    try:
        data = requests.get(f"{API_BASE}/applications").json()
        apps = data.get("applications", [])
    except Exception as e:
        st.error(f"API error: {e}")
        st.stop()

    if not apps:
        st.info("No applications yet. Run the pipeline first!")
        st.stop()

    # Summary bar
    statuses = [a["status"] for a in apps]
    cols = st.columns(6)
    cols[0].metric("Total",        len(apps))
    cols[1].metric("🟡 Pending",    statuses.count("pending"))
    cols[2].metric("🔵 Applied",    statuses.count("applied"))
    cols[3].metric("🟣 Interview",  statuses.count("interview"))
    cols[4].metric("🟢 Offer",      statuses.count("offer"))
    cols[5].metric("🔴 Rejected",   statuses.count("rejected"))

    st.divider()

    # Filter
    filt = st.selectbox("Filter by status", ["All"] + STATUS_LIST, index=0)
    apps = apps if filt == "All" else [a for a in apps if a["status"] == filt]
    st.caption(f"Showing {len(apps)} application(s)")

    for app in apps:
        icon  = STATUS_ICON.get(app["status"], "⚪")
        score = app.get("relevance_score", 0)
        title = f"{icon} **{app['job_title']}** at **{app['company']}** — {score}/10"

        with st.expander(title):
            left, right = st.columns([2, 1])

            with left:
                st.markdown(f"**Why this job?** {app.get('decision_reason', '—')}")
                skills = app.get("required_skills", [])
                if skills:
                    st.markdown("**Skills:** " + "  ".join(f"`{s}`" for s in skills))
                st.markdown(f"**Status:** `{app['status']}`")
                if app.get("next_steps"):
                    with st.container():
                        st.markdown("**Next steps:**")
                        st.markdown(app["next_steps"])

            with right:
                if app.get("job_url"):
                    st.link_button("🔗 Open Job Posting", app["job_url"])

                new_status = st.selectbox(
                    "Update status",
                    STATUS_LIST,
                    index=STATUS_LIST.index(app["status"]),
                    key=f"sel_{app['id']}",
                )
                if st.button("Save status", key=f"save_{app['id']}"):
                    try:
                        requests.put(
                            f"{API_BASE}/applications/{app['id']}/status",
                            json={"status": new_status},
                        )
                        st.success("Updated!")
                        st.rerun()
                    except Exception as ex:
                        st.error(str(ex))

                if st.button("🗑️ Delete", key=f"del_{app['id']}", type="secondary"):
                    try:
                        requests.delete(f"{API_BASE}/applications/{app['id']}")
                        st.rerun()
                    except Exception as ex:
                        st.error(str(ex))

            # View full documents
            if st.toggle("📄 View resume & cover letter", key=f"tog_{app['id']}"):
                try:
                    full = requests.get(f"{API_BASE}/applications/{app['id']}").json()
                    t1, t2 = st.tabs(["📄 Tailored Resume", "✍️ Cover Letter"])
                    with t1:
                        st.markdown(full.get("tailored_resume") or "_No resume generated._")
                    with t2:
                        st.text(full.get("cover_letter") or "_No cover letter generated._")
                except Exception as ex:
                    st.error(str(ex))


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — How It Works
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📖 How It Works":

    st.title("📖 How the Multi-Agent System Works")

    st.markdown("""
    This app runs **5 specialised AI agents** powered by **Groq LLaMA** — the fastest
    publicly available LLM inference engine. Each agent does one job and passes its
    output to the next, like a team of experts collaborating on your behalf.
    """)

    st.divider()

    agents = [
        ("🔍", "Research Agent", "researcher.py",
         "Searches Indeed for matching jobs and sends each description to Groq LLaMA "
         "to extract: required skills, nice-to-have skills, experience level, key responsibilities."),
        ("🎯", "Decision Agent", "decision_agent.py",
         "Scores each job 0–10 against your profile. Scoring rubric: skill match (0-4), "
         "experience fit (0-2), role relevance (0-2), growth potential + company signal (0-2). "
         "Jobs scoring ≥ 6.0 get 'apply', others get 'skip'."),
        ("📄", "Resume Agent", "resume_agent.py",
         "Uses FAISS RAG with free HuggingFace embeddings to retrieve the most relevant "
         "sections of your resume, then Groq LLaMA rewrites them with exact job keywords for ATS optimisation."),
        ("✍️", "Cover Letter Agent", "cover_letter_agent.py",
         "Generates a 250–320 word cover letter that references your specific matching skills "
         "and a concrete achievement. Confident, human tone — no buzzwords."),
        ("💾", "Application Agent", "application_agent.py",
         "Saves everything to SQLite and generates stage-specific next steps: "
         "pending → applied → interview → offer → rejected."),
    ]

    for icon, name, file, desc in agents:
        with st.expander(f"{icon} **{name}** — `{file}`"):
            st.markdown(desc)

    st.divider()
    st.markdown("### Tech Stack")

    cols = st.columns(4)
    stack = [
        ("🐍 Python 3.11", "Core language"),
        ("⚡ Groq", "LLM inference (free)"),
        ("🦙 LLaMA 3 70B", "Language model"),
        ("🔗 LangChain", "LLM framework"),
        ("📐 FAISS", "Resume vector search"),
        ("🤗 HuggingFace", "Free embeddings"),
        ("⚡ FastAPI", "REST backend"),
        ("🎈 Streamlit", "Frontend UI"),
    ]
    for i, (name, desc) in enumerate(stack):
        cols[i % 4].markdown(f"**{name}**  \n{desc}")

    st.divider()
    st.markdown("### Why Groq?")
    st.markdown("""
    - **Free tier** — generous free API with no credit card needed
    - **Blazing fast** — ~500 tokens/sec vs ~60 tokens/sec for OpenAI
    - **LLaMA 3 70B** — open-source model, competitive quality for structured output tasks
    - **Easy swap** — change `GROQ_MODEL` in `.env` to switch between models instantly
    """)
