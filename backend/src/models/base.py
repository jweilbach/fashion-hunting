"""
Base SQLAlchemy configuration and session management
"""
import os
from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import create_engine, text
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
    Initialize database by running the full schema.sql file.
    This creates all tables, views, triggers, functions, and indexes.
    Only runs if the 'tenants' table doesn't exist (first-time setup).
    """
    # Check if database is already initialized by looking for the tenants table
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'tenants')"
        ))
        tables_exist = result.scalar()

    if tables_exist:
        print("✅ Database already initialized, skipping schema creation")
        return

    # Find schema.sql relative to this file
    # backend/src/models/base.py -> backend/../database/schema.sql
    schema_paths = [
        Path(__file__).parent.parent.parent.parent / "database" / "schema.sql",  # From backend/src/models
        Path("/app/database/schema.sql"),  # Docker path
    ]

    schema_path = None
    for path in schema_paths:
        if path.exists():
            schema_path = path
            break

    if schema_path is None:
        # Fallback to SQLAlchemy create_all if schema.sql not found
        print("⚠️ schema.sql not found, falling back to SQLAlchemy create_all")
        from . import tenant, report, feed, job, brand, user, analytics, audit
        Base.metadata.create_all(bind=engine)
        return

    # Read and execute the schema
    print(f"📄 Loading schema from {schema_path}")
    schema_sql = schema_path.read_text()

    # Execute the schema
    with engine.connect() as conn:
        # Execute the entire schema as one transaction
        # PostgreSQL can handle multiple statements in one execute
        conn.execute(text(schema_sql))
        conn.commit()

    print("✅ Schema executed successfully - all tables, views, triggers, and functions created")
