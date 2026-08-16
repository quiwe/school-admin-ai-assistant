from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .settings import settings


db_path = Path(settings.database_url.replace("sqlite:///", ""))
if settings.database_url.startswith("sqlite:///"):
    db_path.parent.mkdir(parents=True, exist_ok=True)

_is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if _is_sqlite else {}
engine = create_engine(settings.database_url, connect_args=connect_args)

if _is_sqlite:
    # WAL + busy_timeout 避免机器人线程与 API 线程并发写库时报 "database is locked"。
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _migrate():
    """Add missing columns for existing SQLite databases (create_all won't ALTER)."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.connect() as conn:
        if "reply_history" in tables:
            existing = {col["name"] for col in inspector.get_columns("reply_history")}
            if "cost_cny" not in existing:
                conn.execute(text("ALTER TABLE reply_history ADD COLUMN cost_cny FLOAT"))
            if "cost_usd" not in existing:
                conn.execute(text("ALTER TABLE reply_history ADD COLUMN cost_usd FLOAT"))
        if "knowledge_files" in tables:
            existing = {col["name"] for col in inspector.get_columns("knowledge_files")}
            if "stored_name" not in existing:
                conn.execute(text("ALTER TABLE knowledge_files ADD COLUMN stored_name VARCHAR(255)"))
        conn.commit()


_migrate()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
