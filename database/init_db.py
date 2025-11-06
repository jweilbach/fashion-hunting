"""
Database initialization script for ABMC Phase 1
Runs schema.sql to set up the PostgreSQL database
"""
import os
import sys
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load environment variables
load_dotenv()


def get_db_connection_string():
    """Get database connection string from environment variables"""
    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'database': os.getenv('POSTGRES_DB', 'abmc_reports'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
    }


def create_database_if_not_exists():
    """Create the database if it doesn't exist"""
    conn_params = get_db_connection_string()
    db_name = conn_params.pop('database')

    try:
        # Connect to postgres database
        conn = psycopg2.connect(**conn_params, database='postgres')
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s",
            (db_name,)
        )
        exists = cursor.fetchone()

        if not exists:
            print(f"Creating database '{db_name}'...")
            cursor.execute(f'CREATE DATABASE {db_name}')
            print(f"Database '{db_name}' created successfully")
        else:
            print(f"Database '{db_name}' already exists")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error creating database: {e}")
        raise


def run_schema():
    """Run the schema.sql file to initialize tables"""
    conn_params = get_db_connection_string()
    schema_path = Path(__file__).parent / "schema.sql"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()

        print(f"Running schema from {schema_path}...")
        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        cursor.execute(schema_sql)
        conn.commit()

        print("Schema executed successfully")

        # Verify tables were created
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()

        print(f"\nCreated {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error running schema: {e}")
        raise


def verify_installation():
    """Verify the database is properly set up"""
    conn_params = get_db_connection_string()

    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()

        # Check for sample tenant
        cursor.execute("SELECT count(*) FROM tenants")
        tenant_count = cursor.fetchone()[0]

        # Check for views
        cursor.execute("""
            SELECT count(*)
            FROM information_schema.views
            WHERE table_schema = 'public'
        """)
        view_count = cursor.fetchone()[0]

        # Check for extensions
        cursor.execute("SELECT extname FROM pg_extension WHERE extname IN ('uuid-ossp', 'pgcrypto')")
        extensions = [row[0] for row in cursor.fetchall()]

        print("\n" + "="*60)
        print("Database Verification")
        print("="*60)
        print(f"Tenants: {tenant_count}")
        print(f"Views: {view_count}")
        print(f"Extensions: {', '.join(extensions)}")
        print("="*60)

        if tenant_count > 0:
            cursor.execute("SELECT name, slug, email FROM tenants LIMIT 1")
            tenant = cursor.fetchone()
            print(f"\nSample tenant: {tenant[0]} ({tenant[1]}) - {tenant[2]}")

        cursor.close()
        conn.close()

        print("\n✓ Database initialization completed successfully!")

    except Exception as e:
        print(f"Error verifying database: {e}")
        raise


def main():
    """Main initialization flow"""
    print("="*60)
    print("ABMC Phase 1 - Database Initialization")
    print("="*60)

    try:
        # Step 1: Create database
        create_database_if_not_exists()

        # Step 2: Run schema
        run_schema()

        # Step 3: Verify
        verify_installation()

    except Exception as e:
        print(f"\n✗ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
