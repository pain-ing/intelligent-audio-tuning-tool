from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

# Prefer DATABASE_URL for consistency; fallback to DB_URL for backward compatibility
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DB_URL", "postgresql://user:pass@localhost:5432/audio")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
