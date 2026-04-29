"""
tools/resume_loader.py
----------------------
Loads your resume (PDF or DOCX), chunks it, and builds a FAISS
vector index for semantic search (RAG).

IMPORTANT — No OpenAI embeddings needed!
We use HuggingFace sentence-transformers (free, runs locally):
  all-MiniLM-L6-v2  — fast, 384-dim, excellent for resume/job matching

USAGE:
    # Build the index once (whenever you update your resume)
    python tools/resume_loader.py path/to/resume.pdf

    # Then in your code:
    from tools.resume_loader import query_resume
    chunks = query_resume("Python FastAPI microservices experience")
"""

import os
from pathlib import Path
from config import FAISS_INDEX_PATH


def _get_embeddings():
    """Free HuggingFace embeddings — no API key needed."""
    from langchain_community.embeddings import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def _load_document(file_path: str):
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(file_path)
    elif ext in (".docx", ".doc"):
        from langchain_community.document_loaders import Docx2txtLoader
        loader = Docx2txtLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Use PDF or DOCX.")
    docs = loader.load()
    print(f"[resume_loader] Loaded {len(docs)} page(s) from {file_path}")
    return docs


def build_resume_index(resume_path: str):
    """
    Parse the resume, chunk it, embed it with HuggingFace,
    and save the FAISS index to disk.

    Args:
        resume_path: Path to your resume PDF or DOCX
    """
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS

    docs = _load_document(resume_path)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=80,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks = splitter.split_documents(docs)
    print(f"[resume_loader] Split into {len(chunks)} chunks.")

    embeddings   = _get_embeddings()
    vectorstore  = FAISS.from_documents(chunks, embeddings)

    os.makedirs(FAISS_INDEX_PATH, exist_ok=True)
    vectorstore.save_local(FAISS_INDEX_PATH)
    print(f"[resume_loader] FAISS index saved → {FAISS_INDEX_PATH}")
    return vectorstore


def load_resume_index():
    """Load saved FAISS index from disk."""
    from langchain_community.vectorstores import FAISS
    if not os.path.exists(FAISS_INDEX_PATH):
        raise FileNotFoundError(
            f"No FAISS index at {FAISS_INDEX_PATH}. "
            "Run build_resume_index() first."
        )
    embeddings = _get_embeddings()
    vs = FAISS.load_local(
        FAISS_INDEX_PATH,
        embeddings,
        allow_dangerous_deserialization=True,
    )
    print("[resume_loader] FAISS index loaded.")
    return vs


def query_resume(query: str, k: int = 4) -> str:
    """
    Retrieve the most relevant resume chunks for a query.

    Args:
        query: Natural language query, e.g. "Python cloud experience"
        k:     Number of chunks to retrieve

    Returns:
        Top-k chunks joined as a single string
    """
    vs   = load_resume_index()
    docs = vs.similarity_search(query, k=k)
    return "\n\n---\n\n".join(d.page_content for d in docs)


def get_full_resume_text(resume_path: str) -> str:
    """Return full plain text of a resume file."""
    docs = _load_document(resume_path)
    return "\n\n".join(d.page_content for d in docs)


def build_index_from_text(resume_text: str):
    """
    Build a FAISS index directly from plain text (no file needed).
    Useful when the user pastes their resume into the UI.
    """
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    from langchain.schema import Document

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400, chunk_overlap=80
    )
    chunks = splitter.create_documents([resume_text])
    print(f"[resume_loader] Created {len(chunks)} chunks from text.")

    embeddings  = _get_embeddings()
    vectorstore = FAISS.from_documents(chunks, embeddings)
    os.makedirs(FAISS_INDEX_PATH, exist_ok=True)
    vectorstore.save_local(FAISS_INDEX_PATH)
    print(f"[resume_loader] Index saved → {FAISS_INDEX_PATH}")
    return vectorstore


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2:
        build_resume_index(sys.argv[1])
        print("\nTest query:")
        print(query_resume("Python and backend experience"))
    else:
        print("Building index from sample text...")
        sample = """
        John Doe | john@example.com | github.com/johndoe

        SKILLS
        Python, FastAPI, PostgreSQL, Docker, LangChain, FAISS, basic PyTorch

        EXPERIENCE
        Backend Engineer — TechCorp (2021–2024)
        - Built REST APIs serving 50k daily users with FastAPI + PostgreSQL
        - Built a RAG document assistant using LangChain + FAISS
        - Reduced query latency by 35% with Redis caching

        EDUCATION
        B.Tech Computer Science, 2021
        """
        build_index_from_text(sample)
        print("\nTest query result:")
        print(query_resume("Python FastAPI experience"))
