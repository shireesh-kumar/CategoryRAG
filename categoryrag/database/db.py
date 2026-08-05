from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from categoryrag.config import DATA_DIR, ensure_data_dirs

ensure_data_dirs()

DATABASE_URL = f"sqlite:///{DATA_DIR / 'categoryrag.db'}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

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
    _ensure_column("documents", "s3_key", "VARCHAR(512)")
    _ensure_column("categories", "s3_prefix", "VARCHAR(512)")


def _ensure_column(table: str, column: str, coltype: str) -> None:
    with engine.begin() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        columns = {row[1] for row in rows}
        if column not in columns:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))


def get_session():
    return SessionLocal()
