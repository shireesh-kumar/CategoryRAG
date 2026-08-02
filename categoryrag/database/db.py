from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from categoryrag.config import DATA_DIR, ensure_data_dirs
from categoryrag import models 


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
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()
