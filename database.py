"""
database.py
-----------
SQLAlchemy models for storing job applications.
Run once to create tables: python database.py
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL

engine       = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()


class JobApplication(Base):
    __tablename__ = "job_applications"

    id               = Column(Integer, primary_key=True, index=True)
    job_title        = Column(String(200), nullable=False)
    company          = Column(String(200))
    job_url          = Column(String(500))
    job_description  = Column(Text)

    # Extracted by Research Agent
    required_skills  = Column(Text)       # JSON list stored as string
    experience_level = Column(String(50))

    # Set by Decision Agent
    relevance_score  = Column(Float, default=0.0)   # 0.0 – 10.0
    decision         = Column(String(10))            # "apply" | "skip"
    decision_reason  = Column(Text)

    # Generated documents
    tailored_resume  = Column(Text)
    cover_letter     = Column(Text)

    # Tracking
    status           = Column(String(50), default="pending")
    next_steps       = Column(Text)
    notes            = Column(Text)

    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Job {self.job_title} @ {self.company} [{self.status}]>"


def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created.")


def get_db():
    """FastAPI dependency — yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
