from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from categoryrag.config import DATABASE_URL, ensure_data_dirs

ensure_data_dirs()

engine = create_engine(DATABASE_URL, echo=False)

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


def get_session():
    return SessionLocal()
