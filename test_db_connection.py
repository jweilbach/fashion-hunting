#!/usr/bin/env python3
"""
Test PostgreSQL database connection
Run this before initializing the database
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Load environment variables
load_dotenv()


def test_postgres_server():
    """Test connection to PostgreSQL server"""
    print("="*60)
    print("PostgreSQL Connection Test")
    print("="*60)

    # Get connection parameters
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = int(os.getenv('POSTGRES_PORT', '5432'))
    user = os.getenv('POSTGRES_USER', 'postgres')
    password = os.getenv('POSTGRES_PASSWORD', 'postgres')

    print(f"\nConnection parameters:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  User: {user}")
    print(f"  Password: {'*' * len(password) if password else '(not set)'}")

    try:
        # Try to connect to postgres database (default)
        print(f"\n[1/3] Attempting to connect to PostgreSQL server...")
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'  # Connect to default postgres database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Get PostgreSQL version
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✓ Connected to PostgreSQL server")
        print(f"  Version: {version.split(',')[0]}")

        # List existing databases
        cursor.execute("""
            SELECT datname FROM pg_database
            WHERE datistemplate = false
            ORDER BY datname
        """)
        databases = [row[0] for row in cursor.fetchall()]
        print(f"\n[2/3] Existing databases:")
        for db in databases:
            print(f"  - {db}")

        # Check if our target database exists
        db_name = os.getenv('POSTGRES_DB', 'abmc_reports')
        if db_name in databases:
            print(f"\n✓ Database '{db_name}' already exists")

            # Try to connect to it
            cursor.close()
            conn.close()

            print(f"\n[3/3] Testing connection to '{db_name}'...")
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=db_name
            )
            cursor = conn.cursor()

            # Count tables
            cursor.execute("""
                SELECT count(*) FROM information_schema.tables
                WHERE table_schema = 'public'
            """)
            table_count = cursor.fetchone()[0]
            print(f"✓ Connected to database '{db_name}'")
            print(f"  Tables: {table_count}")

            if table_count > 0:
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                tables = [row[0] for row in cursor.fetchall()]
                print(f"\n  Existing tables:")
                for table in tables:
                    print(f"    - {table}")
        else:
            print(f"\n⚠ Database '{db_name}' does not exist yet")
            print(f"  Run 'python database/init_db.py' to create it")

        cursor.close()
        conn.close()

        print("\n" + "="*60)
        print("✓ Database connection test PASSED")
        print("="*60)
        print("\nNext steps:")
        print("  1. If database doesn't exist: python database/init_db.py")
        print("  2. Run migration: python database/migrate_from_sheets.py")
        print("="*60)

        return True

    except psycopg2.OperationalError as e:
        print(f"\n✗ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Is PostgreSQL installed and running?")
        print("     - macOS: brew services start postgresql")
        print("     - Linux: sudo systemctl start postgresql")
        print("     - Windows: Check PostgreSQL service in Services")
        print("     - Docker: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15")
        print("\n  2. Are your credentials correct?")
        print("     - Check your .env file")
        print("     - Default user: postgres")
        print("     - Default password: postgres (or empty)")
        print("\n  3. Is PostgreSQL accepting connections?")
        print(f"     - Try: psql -h {host} -p {port} -U {user}")
        return False

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False


def check_dependencies():
    """Check if required packages are installed"""
    print("\nChecking dependencies...")

    required = {
        'psycopg2': 'psycopg2-binary',
        'dotenv': 'python-dotenv',
    }

    missing = []
    for module, package in required.items():
        try:
            __import__(module)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} (missing)")
            missing.append(package)

    if missing:
        print(f"\n⚠ Missing packages. Install with:")
        print(f"  pip install {' '.join(missing)}")
        return False

    print("  ✓ All dependencies installed")
    return True


def main():
    """Main test flow"""
    # Check dependencies first
    if not check_dependencies():
        print("\n✗ Please install missing dependencies first")
        sys.exit(1)

    # Test connection
    success = test_postgres_server()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
