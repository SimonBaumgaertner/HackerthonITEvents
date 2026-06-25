"""Database engine, schema creation and the session dependency."""

from sqlmodel import Session, SQLModel, create_engine

DATABASE_URL = "sqlite:///events.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Create all tables. Safe to call on every startup."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency that yields a database session."""
    with Session(engine) as session:
        yield session
