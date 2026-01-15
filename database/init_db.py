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
import bcrypt

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load environment variables
load_dotenv()

# Default superuser credentials
SUPERUSER_EMAIL = "weilbach@gmail.com"
SUPERUSER_FIRST_NAME = "Justin"
SUPERUSER_LAST_NAME = "Weilbach"
SUPERUSER_PASSWORD = "Welcome123"
SUPERUSER_TENANT_NAME = "Lavacake"
SUPERUSER_TENANT_SLUG = "lavacake"


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


def check_tables_exist():
    """Check if the core tables already exist in the database"""
    conn_params = get_db_connection_string()

    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()

        # Check for core tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('tenants', 'users', 'reports', 'feed_configs')
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return len(existing_tables) >= 4  # All core tables exist

    except Exception as e:
        print(f"Error checking tables: {e}")
        return False


def run_schema():
    """Run the schema.sql file to initialize tables (only if not already initialized)"""
    conn_params = get_db_connection_string()
    schema_path = Path(__file__).parent / "schema.sql"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    # Check if tables already exist
    if check_tables_exist():
        print("Core tables already exist, skipping schema initialization")
        print("(Run migrations to apply incremental changes)")
        return

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


def create_migrations_table():
    """Create the migrations tracking table if it doesn't exist"""
    conn_params = get_db_connection_string()

    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        conn.commit()

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error creating migrations table: {e}")
        raise


def get_applied_migrations():
    """Get list of already applied migrations"""
    conn_params = get_db_connection_string()

    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()

        cursor.execute("SELECT migration_name FROM schema_migrations ORDER BY id")
        applied = [row[0] for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return set(applied)

    except Exception as e:
        print(f"Error getting applied migrations: {e}")
        return set()


def run_migrations():
    """Run any pending migrations from backend/migrations/"""
    migrations_dir = Path(__file__).parent.parent / "backend" / "migrations"

    if not migrations_dir.exists():
        print(f"Migrations directory not found: {migrations_dir}")
        return

    # Create migrations table if needed
    create_migrations_table()

    # Get list of migration files (sorted alphabetically)
    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        print("No migration files found")
        return

    # Get already applied migrations
    applied = get_applied_migrations()

    # Find pending migrations
    pending = []
    for mf in migration_files:
        if mf.name not in applied:
            pending.append(mf)

    if not pending:
        print("All migrations already applied")
        return

    print(f"\nFound {len(pending)} pending migration(s):")
    for mf in pending:
        print(f"  - {mf.name}")

    # Apply each pending migration
    conn_params = get_db_connection_string()
    conn = psycopg2.connect(**conn_params)

    for mf in pending:
        print(f"\nApplying migration: {mf.name}...")
        try:
            cursor = conn.cursor()

            with open(mf, 'r') as f:
                migration_sql = f.read()

            # Execute the migration
            cursor.execute(migration_sql)

            # Record the migration
            cursor.execute(
                "INSERT INTO schema_migrations (migration_name) VALUES (%s)",
                (mf.name,)
            )

            conn.commit()
            print(f"  ✓ {mf.name} applied successfully")

        except Exception as e:
            conn.rollback()
            print(f"  ✗ Error applying {mf.name}: {e}")
            # Continue with other migrations or stop?
            # For safety, let's stop on first error
            raise

    conn.close()
    print(f"\n✓ Applied {len(pending)} migration(s)")


def create_superuser_if_not_exists():
    """Create the Lavacake tenant and superuser if they don't exist"""
    conn_params = get_db_connection_string()

    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()

        # Check if Lavacake tenant exists
        cursor.execute(
            "SELECT id FROM tenants WHERE slug = %s OR name ILIKE %s",
            (SUPERUSER_TENANT_SLUG, f'%{SUPERUSER_TENANT_NAME}%')
        )
        tenant_row = cursor.fetchone()

        if tenant_row:
            tenant_id = tenant_row[0]
            print(f"Tenant '{SUPERUSER_TENANT_NAME}' already exists (id: {tenant_id})")
        else:
            # Create the Lavacake tenant
            cursor.execute("""
                INSERT INTO tenants (name, slug, email, plan, status)
                VALUES (%s, %s, %s, 'enterprise', 'active')
                RETURNING id
            """, (SUPERUSER_TENANT_NAME, SUPERUSER_TENANT_SLUG, SUPERUSER_EMAIL))
            tenant_id = cursor.fetchone()[0]
            conn.commit()
            print(f"Created tenant '{SUPERUSER_TENANT_NAME}' (id: {tenant_id})")

        # Check if superuser exists
        cursor.execute(
            "SELECT id, is_superuser FROM users WHERE email = %s AND tenant_id = %s",
            (SUPERUSER_EMAIL, tenant_id)
        )
        user_row = cursor.fetchone()

        if user_row:
            user_id, is_superuser = user_row
            if is_superuser:
                print(f"Superuser '{SUPERUSER_EMAIL}' already exists and has superuser privileges")
            else:
                # Update existing user to be superuser
                cursor.execute("""
                    UPDATE users
                    SET is_superuser = TRUE,
                        first_name = %s,
                        last_name = %s,
                        role = 'admin'
                    WHERE id = %s
                """, (SUPERUSER_FIRST_NAME, SUPERUSER_LAST_NAME, user_id))
                conn.commit()
                print(f"Updated existing user '{SUPERUSER_EMAIL}' to superuser")
        else:
            # Create the superuser
            password_hash = bcrypt.hashpw(
                SUPERUSER_PASSWORD.encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')

            cursor.execute("""
                INSERT INTO users (
                    tenant_id, email, password_hash, first_name, last_name,
                    full_name, role, is_active, is_superuser
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'admin', TRUE, TRUE)
            """, (
                tenant_id, SUPERUSER_EMAIL, password_hash,
                SUPERUSER_FIRST_NAME, SUPERUSER_LAST_NAME,
                f"{SUPERUSER_FIRST_NAME} {SUPERUSER_LAST_NAME}"
            ))
            conn.commit()
            print(f"Created superuser '{SUPERUSER_EMAIL}' with password '{SUPERUSER_PASSWORD}'")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error creating superuser: {e}")
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

        # Check for superuser
        cursor.execute("""
            SELECT u.email, u.first_name, u.last_name, t.name as tenant_name
            FROM users u
            JOIN tenants t ON u.tenant_id = t.id
            WHERE u.is_superuser = TRUE
        """)
        superusers = cursor.fetchall()

        print("\n" + "="*60)
        print("Database Verification")
        print("="*60)
        print(f"Tenants: {tenant_count}")
        print(f"Views: {view_count}")
        print(f"Extensions: {', '.join(extensions)}")
        print(f"Superusers: {len(superusers)}")
        print("="*60)

        if tenant_count > 0:
            cursor.execute("SELECT name, slug, email FROM tenants LIMIT 1")
            tenant = cursor.fetchone()
            print(f"\nSample tenant: {tenant[0]} ({tenant[1]}) - {tenant[2]}")

        if superusers:
            print("\nSuperuser accounts:")
            for su in superusers:
                print(f"  - {su[0]} ({su[1]} {su[2]}) - {su[3]}")

        cursor.close()
        conn.close()

        print("\n✓ Database initialization completed successfully!")

    except Exception as e:
        print(f"Error verifying database: {e}")
        raise


def main():
    """Main initialization flow"""
    print("="*60)
    print("Phase 1 - Database Initialization")
    print("="*60)

    try:
        # Step 1: Create database
        print("\n[Step 1/4] Checking/creating database...")
        create_database_if_not_exists()

        # Step 2: Run schema (skipped if tables already exist)
        print("\n[Step 2/4] Running schema (if needed)...")
        run_schema()

        # Step 3: Create superuser (Lavacake tenant + weilbach@gmail.com)
        print("\n[Step 3/4] Creating superuser (Lavacake tenant + weilbach@gmail.com)...")
        create_superuser_if_not_exists()

        # Step 4: Verify
        print("\n[Step 4/4] Verifying installation...")
        verify_installation()

    except Exception as e:
        print(f"\n✗ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
