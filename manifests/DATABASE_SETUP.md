# Database Setup Guide

This guide will help you set up PostgreSQL and test the database connection.

## Quick Start (Recommended)

### Option 1: Using Docker (Easiest)

1. **Start PostgreSQL and Redis with Docker Compose:**
   ```bash
   docker-compose up -d postgres redis
   ```

2. **Wait for services to be ready (about 10 seconds):**
   ```bash
   docker-compose ps
   ```

3. **Test the connection:**
   ```bash
   python test_db_connection.py
   ```

4. **Initialize the database:**
   ```bash
   python database/init_db.py
   ```

### Option 2: Local PostgreSQL Installation

#### macOS (Homebrew)
```bash
# Install PostgreSQL
brew install postgresql@15

# Start PostgreSQL
brew services start postgresql@15

# Create database user (if needed)
createuser -s postgres

# Test connection
python test_db_connection.py
```

#### Ubuntu/Debian
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'postgres';"
sudo -u postgres psql -c "ALTER USER postgres WITH SUPERUSER;"

# Test connection
python test_db_connection.py
```

#### Windows
1. Download PostgreSQL from: https://www.postgresql.org/download/windows/
2. Run the installer
3. Set password for postgres user
4. Update `.env` file with your password
5. Test connection: `python test_db_connection.py`

## Step-by-Step Setup

### 1. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and update the database credentials:
```bash
# For Docker (default):
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=abmc_reports
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# For local PostgreSQL, update password if different
```

### 2. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Test Database Connection

Run the connection test script:
```bash
python test_db_connection.py
```

Expected output:
```
============================================================
PostgreSQL Connection Test
============================================================

Connection parameters:
  Host: localhost
  Port: 5432
  User: postgres
  Password: ********

[1/3] Attempting to connect to PostgreSQL server...
✓ Connected to PostgreSQL server
  Version: PostgreSQL 15.x

[2/3] Existing databases:
  - postgres
  - template0
  - template1

⚠ Database 'abmc_reports' does not exist yet
  Run 'python database/init_db.py' to create it

============================================================
✓ Database connection test PASSED
============================================================
```

### 4. Initialize the Database

Run the initialization script:
```bash
python database/init_db.py
```

This will:
- Create the `abmc_reports` database
- Run the schema.sql file to create all tables
- Create indexes, triggers, and views
- Insert sample data

Expected output:
```
============================================================
ABMC Phase 1 - Database Initialization
============================================================
Creating database 'abmc_reports'...
Database 'abmc_reports' created successfully
Running schema from database/schema.sql...
Schema executed successfully

Created 12 tables:
  - tenants
  - provider_credentials
  - reports
  - feed_configs
  - scheduled_jobs
  - job_executions
  - brand_configs
  - users
  - analytics_cache
  - audit_logs
  - lists
  - list_items

============================================================
Database Verification
============================================================
Tenants: 1
Views: 4
Extensions: uuid-ossp, pgcrypto
============================================================

Sample tenant: ABMC Demo (abmc-demo) - demo@alisonbrod.com

✓ Database initialization completed successfully!
```

### 5. Running Migrations (Existing Databases)

If you have an existing database and need to apply schema updates, run the migration scripts:
```bash
# Connect to your database
psql -h localhost -U postgres -d abmc_reports

# Run a specific migration (example)
\i backend/migrations/split_full_name.sql

# Or run directly from command line
psql -h localhost -U postgres -d abmc_reports -f backend/migrations/split_full_name.sql
```

**Available Migrations:**
| Migration File | Description |
|----------------|-------------|
| `split_full_name.sql` | Adds first_name/last_name columns to users table |
| `add_source_type_to_reports.sql` | Adds source_type column to reports |
| `backfill_source_type.sql` | Backfills source_type data for existing reports |
| `add_brands_gin_index.sql` | Adds GIN index for brand array searches |

**For Railway deployments**, run migrations via Railway's database shell or connect remotely:
```bash
# Using Railway CLI
railway run psql -f backend/migrations/split_full_name.sql

# Or connect directly to Railway PostgreSQL
psql $DATABASE_URL -f backend/migrations/split_full_name.sql
```

### 6. Verify Installation

Test the connection again:
```bash
python test_db_connection.py
```

You should now see the database and tables listed.

## Troubleshooting

### Connection Refused

**Error:** `connection refused` or `could not connect to server`

**Solutions:**
1. Check if PostgreSQL is running:
   ```bash
   # Docker
   docker-compose ps

   # macOS
   brew services list | grep postgresql

   # Linux
   sudo systemctl status postgresql

   # Windows
   # Check Services (Win + R -> services.msc)
   ```

2. Check if the port is correct:
   ```bash
   # Should see PostgreSQL listening on port 5432
   netstat -an | grep 5432
   ```

### Authentication Failed

**Error:** `password authentication failed`

**Solutions:**
1. Check your `.env` file credentials
2. For local PostgreSQL, reset the password:
   ```bash
   # macOS/Linux
   sudo -u postgres psql
   postgres=# ALTER USER postgres PASSWORD 'postgres';

   # Or create a new user
   postgres=# CREATE USER myuser WITH PASSWORD 'mypassword';
   postgres=# ALTER USER myuser WITH SUPERUSER;
   ```

### Database Already Exists

**Error:** `database "abmc_reports" already exists`

**Solution:**
This is fine! The script will skip creation and just verify the connection.

To start fresh:
```bash
# Docker
docker-compose down -v
docker-compose up -d postgres redis

# Local PostgreSQL
dropdb abmc_reports
python database/init_db.py
```

### Permission Denied

**Error:** `permission denied to create database`

**Solutions:**
1. Grant superuser privileges:
   ```bash
   sudo -u postgres psql
   postgres=# ALTER USER postgres WITH SUPERUSER;
   ```

2. Or use a different user:
   ```bash
   # Update .env file
   POSTGRES_USER=your_username
   POSTGRES_PASSWORD=your_password
   ```

## Docker Compose Services

The `docker-compose.yml` includes:

- **postgres**: PostgreSQL 15 database
- **redis**: Redis for Celery task queue
- **pgadmin**: Database management UI (optional)

### Start all services:
```bash
docker-compose up -d
```

### Start with pgAdmin (optional):
```bash
docker-compose --profile tools up -d
```

Access pgAdmin at: http://localhost:5050
- Email: admin@abmc.local
- Password: admin

### Stop services:
```bash
docker-compose down
```

### Remove all data (reset):
```bash
docker-compose down -v
```

## Next Steps

After successful database setup:

1. **Migrate existing Google Sheets data (optional):**
   ```bash
   # Update .env with your Google Sheet ID
   GOOGLE_SHEET_ID=your_sheet_id_here

   # Run migration
   python database/migrate_from_sheets.py
   ```

2. **Start the FastAPI backend:**
   ```bash
   cd backend
   python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Start the React frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Start Celery worker (for background jobs):**
   ```bash
   cd backend
   celery -A celery_app worker --loglevel=info
   ```

5. **Access the application:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Database Schema

The database includes the following tables:

| Table | Description |
|-------|-------------|
| **tenants** | Multi-tenant organization accounts with settings and subscription plans |
| **provider_credentials** | Encrypted API credentials per provider (OpenAI, TikTok, etc.) |
| **reports** | Fetched content and analysis results with deduplication |
| **feed_configs** | RSS/TikTok/Instagram feed configurations |
| **scheduled_jobs** | Automated task scheduling with cron expressions |
| **job_executions** | Job execution history and progress tracking |
| **brand_configs** | Brand tracking, aliases, and filtering rules |
| **users** | User accounts with RBAC (first_name, last_name, role) |
| **analytics_cache** | Cached dashboard metrics with TTL |
| **audit_logs** | Security and compliance audit trail |
| **lists** | User-created lists for organizing reports |
| **list_items** | Items within lists (report references) |

**Key Features:**
- UUID primary keys throughout
- Tenant isolation via `tenant_id` foreign keys
- GIN indexes for array searches (brands)
- Full-text search on report titles/summaries
- Automatic `updated_at` triggers
- Deduplication via SHA256 hash keys

See [database/schema.sql](../database/schema.sql) for full schema details.
