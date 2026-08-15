import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base



import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'products.db'}"
)
connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)


engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


Base = declarative_base()


def get_session():
    """
    FastAPI-style database dependency.

    In LangGraph tools/nodes, you can also use:

        with SessionLocal() as session:
            ...
    """
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """
    Create all database tables defined in the ORM models.
    """
    Base.metadata.create_all(bind=engine)