"""
Base SQLAlchemy configuration and session management
"""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

load_dotenv()

# Database URL from environment
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'postgres')}@"
    f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
    f"{os.getenv('POSTGRES_PORT', '5432')}/"
    f"{os.getenv('POSTGRES_DB', 'abmc_reports')}"
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before using
    echo=os.getenv('SQL_ECHO', 'false').lower() == 'true'
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


def get_session() -> Session:
    """
    Get a new database session

    Usage:
        with get_session() as session:
            # Use session
            pass
    """
    return SessionLocal()


@contextmanager
def get_db():
    """
    Context manager for database sessions
    Automatically commits on success and rolls back on error

    Usage:
        with get_db() as db:
            db.query(Model).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize database (create all tables)
    Note: Use migrations in production, this is for development only
    """
    Base.metadata.create_all(bind=engine)
