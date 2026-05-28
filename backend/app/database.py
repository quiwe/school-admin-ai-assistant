from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .settings import settings


db_path = Path(settings.database_url.replace("sqlite:///", ""))
if settings.database_url.startswith("sqlite:///"):
    db_path.parent.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _migrate():
    """Add missing columns for existing SQLite databases (create_all won't ALTER)."""
    inspector = inspect(engine)
    if "reply_history" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("reply_history")}
    with engine.connect() as conn:
        if "cost_cny" not in existing:
            conn.execute(text("ALTER TABLE reply_history ADD COLUMN cost_cny FLOAT"))
        if "cost_usd" not in existing:
            conn.execute(text("ALTER TABLE reply_history ADD COLUMN cost_usd FLOAT"))
        conn.commit()


_migrate()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
