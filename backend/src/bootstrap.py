"""
Server bootstrap module - runs on application startup.

Consolidates all initialization logic:
1. Database table creation
2. Superuser/tenant creation
3. Any other startup tasks
"""
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def run_bootstrap():
    """
    Main bootstrap function called on server startup.

    This runs:
    1. Database table initialization (from models/base.py)
    2. Superuser and Lavacake tenant creation (from database/init_db.py)
    """
    logger.info("=" * 50)
    logger.info("Starting server bootstrap...")
    logger.info("=" * 50)

    # Step 1: Initialize database tables
    logger.info("[Bootstrap 1/2] Initializing database tables...")
    try:
        from src.models.base import init_database
        init_database()
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        # Don't fail startup - tables might already exist

    # Step 2: Create superuser and Lavacake tenant if they don't exist
    logger.info("[Bootstrap 2/2] Checking superuser and tenant...")
    try:
        _ensure_superuser_exists()
        logger.info("Superuser check complete")
    except Exception as e:
        logger.warning(f"Could not verify superuser (non-fatal): {e}")
        # Don't fail startup - this is optional

    logger.info("=" * 50)
    logger.info("Server bootstrap complete")
    logger.info("=" * 50)


def _ensure_superuser_exists():
    """
    Ensure the Lavacake tenant and superuser account exist.

    This imports the logic from database/init_db.py to avoid duplication.
    """
    # Add database directory to path so we can import init_db
    database_dir = Path(__file__).parent.parent.parent / "database"

    if not database_dir.exists():
        # Try Docker path
        database_dir = Path("/app/database")

    if not database_dir.exists():
        logger.warning(f"Database directory not found, skipping superuser check")
        return

    # Add to path temporarily
    sys.path.insert(0, str(database_dir.parent))

    try:
        from database.init_db import create_superuser_if_not_exists
        create_superuser_if_not_exists()
    except ImportError as e:
        logger.warning(f"Could not import init_db module: {e}")
    except Exception as e:
        logger.warning(f"Superuser creation check failed: {e}")
    finally:
        # Remove from path
        if str(database_dir.parent) in sys.path:
            sys.path.remove(str(database_dir.parent))
