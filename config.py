"""
config.py
---------
Central config. Reads .env file.
All agents import get_llm() from here — changing the model
in .env is all you need to switch between Groq models.

GROQ MODELS (free tier):
  llama3-8b-8192      fastest, good for dev/testing
  llama3-70b-8192     best quality, recommended for prod
  mixtral-8x7b-32768  32k context window, good for long resumes
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Groq ──────────────────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str   = os.getenv("GROQ_MODEL", "llama3-70b-8192")

# ── App ───────────────────────────────────────────────────────────────────────
APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
DEBUG: bool   = os.getenv("DEBUG", "true").lower() == "true"

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./jobs.db")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
RESUME_DIR       = os.path.join(BASE_DIR, "data", "sample_resumes")
FAISS_INDEX_PATH = os.path.join(BASE_DIR, "data", "resume_index")


def get_llm():
    """
    Returns a LangChain ChatGroq LLM.
    Import and call this in every agent.

    Example:
        from config import get_llm
        llm = get_llm()
        response = llm.invoke("Hello!")
    """
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY is not set.\n"
            "1. Get a free key at https://console.groq.com\n"
            "2. Add it to your .env file: GROQ_API_KEY=gsk_..."
        )
    from langchain_groq import ChatGroq
    return ChatGroq(
        model=GROQ_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.3,
        max_tokens=2048,
    )


if __name__ == "__main__":
    print(f"Model : {GROQ_MODEL}")
    print(f"Debug : {DEBUG}")
    print(f"DB    : {DATABASE_URL}")
    try:
        llm = get_llm()
        r   = llm.invoke("Say hello in one sentence.")
        print(f"Test  : {r.content}")
    except Exception as e:
        print(f"Error : {e}")
