import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./products.db")
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()

def get_session():
    """FastAPI-style dependency generator. In LangGraph nodes, use
    `with SessionLocal() as session:` directly instead."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """Creates all tables. Call once at startup / from ingest scripts."""
    Base.metadata.create_all(bind=engine)

    if DATABASE_URL.startswith("sqlite"):
      
        with engine.begin() as conn:
            cols = {
                row[1] for row in conn.exec_driver_sql("PRAGMA table_info(products)").fetchall()
            }
            if "reserved_qty" not in cols:
                conn.exec_driver_sql(
                    "ALTER TABLE products ADD COLUMN reserved_qty INTEGER DEFAULT 0"
                )
            if "lead_time_days" not in cols:
                conn.exec_driver_sql(
                    "ALTER TABLE products ADD COLUMN lead_time_days INTEGER"
                )
            if "stock_updated_at" not in cols:
                conn.exec_driver_sql(
                    "ALTER TABLE products ADD COLUMN stock_updated_at DATETIME"
                )
            if "price_updated_at" not in cols:
                conn.exec_driver_sql(
                    "ALTER TABLE products ADD COLUMN price_updated_at DATETIME"
                )