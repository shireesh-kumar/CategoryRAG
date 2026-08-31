from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from categoryrag.config import DATA_DIR, DATABASE_URL, ensure_data_dirs

ensure_data_dirs()

_engine_kwargs: dict = {"echo": False}
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_kwargs)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from categoryrag import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    if DATABASE_URL.startswith("sqlite"):
        _ensure_column_sqlite("documents", "s3_key", "VARCHAR(512)")
        _ensure_column_sqlite("categories", "s3_prefix", "VARCHAR(512)")


def _ensure_column_sqlite(table: str, column: str, coltype: str) -> None:
    with engine.begin() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        columns = {row[1] for row in rows}
        if column not in columns:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))


def get_session():
    return SessionLocal()
