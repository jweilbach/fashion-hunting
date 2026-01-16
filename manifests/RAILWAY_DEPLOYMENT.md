# Railway Deployment Guide

This guide walks you through deploying ABMC to Railway.

## Architecture Overview

The application consists of 4 services:
1. **Backend API** - FastAPI application
2. **Frontend** - React/Vite static build served by nginx
3. **Celery Worker** - Background task processor
4. **Database & Redis** - Provided by Railway

---

## Step 1: Create a Railway Project

1. Go to [railway.app](https://railway.app) and sign in
2. Click **"New Project"**
3. Select **"Empty Project"**

---

## Step 2: Add PostgreSQL Database

1. In your project, click **"+ New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway will provision a PostgreSQL instance
3. Click on the PostgreSQL service to see connection details
4. Note the `DATABASE_URL` - you'll need this for other services

---

## Step 3: Add Redis

1. Click **"+ New"** → **"Database"** → **"Add Redis"**
2. Railway will provision a Redis instance
3. Note the `REDIS_URL` from the connection details

---

## Step 4: Deploy Backend API

1. Click **"+ New"** → **"GitHub Repo"**
2. Select your repository
3. Railway will detect the `railway.toml` - configure it as follows:

### Settings for Backend:
- **Root Directory**: `/` (leave empty or root)
- **Dockerfile Path**: `backend/Dockerfile`
- **Watch Paths**: `backend/**`, `requirements.txt`

### Environment Variables:
Click on the service → **Variables** → Add these:

```env
# Database (reference PostgreSQL service)
POSTGRES_HOST=${{Postgres.PGHOST}}
POSTGRES_PORT=${{Postgres.PGPORT}}
POSTGRES_DB=${{Postgres.PGDATABASE}}
POSTGRES_USER=${{Postgres.PGUSER}}
POSTGRES_PASSWORD=${{Postgres.PGPASSWORD}}

# Redis (reference Redis service)
REDIS_HOST=${{Redis.REDISHOST}}
REDIS_PORT=${{Redis.REDISPORT}}

# API Keys (add your own values)
OPENAI_API_KEY=sk-your-openai-key
GEMINI_API_KEY=your-gemini-api-key
GOOGLE_API_KEY=your-google-api-key
GOOGLE_SEARCH_ENGINE_ID=your-search-engine-id
APIFY_API_TOKEN=your-apify-token

# S3 Storage (for PDF summaries - Brand 360)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-2
S3_BUCKET_NAME=your-summaries-bucket

# Security
SECRET_KEY=generate-a-secure-random-string-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# App Settings
ENV=production
DEBUG=false
SQL_ECHO=false

# CORS (update with your frontend URL after deployment)
ALLOWED_ORIGINS=https://your-frontend.up.railway.app
```

### Networking:
- Railway automatically assigns a port via `$PORT`
- Generate a public domain: **Settings** → **Networking** → **Generate Domain**

---

## Step 5: Deploy Celery Worker

1. Click **"+ New"** → **"GitHub Repo"** (same repo)
2. This creates a second service from the same repo

### Settings for Worker:
- **Service Name**: `celery-worker`
- **Dockerfile Path**: `backend/Dockerfile.worker`
- **Watch Paths**: `backend/**`, `requirements.txt`

### Environment Variables:
Copy the same environment variables from the Backend, plus:

```env
# Celery Configuration
CELERY_BROKER_URL=redis://${{Redis.REDISHOST}}:${{Redis.REDISPORT}}
CELERY_RESULT_BACKEND=redis://${{Redis.REDISHOST}}:${{Redis.REDISPORT}}
```

**Note**: The worker does NOT need a public domain - it only processes background tasks.

---

## Step 6: Deploy Frontend

1. Click **"+ New"** → **"GitHub Repo"** (same repo)
2. Configure as a separate service

### Settings for Frontend:
- **Service Name**: `frontend`
- **Root Directory**: `frontend`
- **Dockerfile Path**: `frontend/Dockerfile`
- **Watch Paths**: `frontend/**`

### Build Arguments:
In **Settings** → **Build** → **Build Arguments**:

```
VITE_API_URL=https://your-backend.up.railway.app
```

Replace with your actual backend URL from Step 4.

### Networking:
- Generate a public domain for the frontend
- This is the URL users will access

---

## Step 7: Update CORS Settings

After deploying the frontend, update the backend's `ALLOWED_ORIGINS`:

```env
ALLOWED_ORIGINS=https://your-frontend.up.railway.app
```

---

## Step 8: Run Database Migrations

1. Go to your **Backend** service
2. Click **"Settings"** → **"Run Command"**
3. Run the migration command:

```bash
cd /app/backend && alembic upgrade head
```

Or set up the migration as a one-time job.

---

## Step 9: Initialize Database & Create Superuser

After migrations, run the database initialization script to create the schema, sample data, and superuser account:

**Option A**: Run via Railway shell (Recommended)
1. Backend service → **Connect** → **Shell**
2. Run the initialization script:
   ```bash
   cd /app && python database/init_db.py
   ```

This will automatically:
- Create all database tables (if not exists)
- Create the **Lavacake** tenant (enterprise plan)
- Create the superuser account:
  - **Email**: weilbach@gmail.com
  - **Password**: Welcome123
  - **Role**: admin with superuser privileges
- Create sample data (ABMC Demo tenant)

**Option B**: Use Railway's one-time job feature to run `python database/init_db.py`

**Note**: The init script is idempotent - safe to run multiple times. It skips existing resources.

---

## Environment Variables Summary

### Backend API & Worker (shared)
| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_HOST` | Database host | `${{Postgres.PGHOST}}` |
| `POSTGRES_PORT` | Database port | `${{Postgres.PGPORT}}` |
| `POSTGRES_DB` | Database name | `${{Postgres.PGDATABASE}}` |
| `POSTGRES_USER` | Database user | `${{Postgres.PGUSER}}` |
| `POSTGRES_PASSWORD` | Database password | `${{Postgres.PGPASSWORD}}` |
| `REDIS_HOST` | Redis host | `${{Redis.REDISHOST}}` |
| `REDIS_PORT` | Redis port | `${{Redis.REDISPORT}}` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `GEMINI_API_KEY` | Gemini API key (for summaries) | `AIza...` |
| `GOOGLE_API_KEY` | Google API key | `AIza...` |
| `GOOGLE_SEARCH_ENGINE_ID` | Google CSE ID | `665c...` |
| `APIFY_API_TOKEN` | Apify token | `apify_api_...` |
| `AWS_ACCESS_KEY_ID` | AWS access key (S3) | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key (S3) | `...` |
| `AWS_REGION` | AWS region | `us-east-2` |
| `S3_BUCKET_NAME` | S3 bucket for summaries | `your-bucket` |
| `SECRET_KEY` | JWT secret | Random 32+ char string |
| `ENV` | Environment | `production` |
| `DEBUG` | Debug mode | `false` |
| `ALLOWED_ORIGINS` | CORS origins | Frontend URL |

### Frontend (build args)
| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `https://backend.up.railway.app` |

---

## Monitoring

1. **Logs**: Each service has a **Logs** tab for real-time monitoring
2. **Metrics**: Railway provides CPU/Memory usage graphs
3. **Health Checks**: Backend has `/health` endpoint

---

## Estimated Costs

Railway pricing (as of 2024):
- **Hobby Plan**: $5/month includes:
  - 500 hours of usage
  - 100GB bandwidth
  - Databases included
- **Pro Plan**: $20/month for more resources

For a small-scale deployment:
- Backend + Worker + Frontend + PostgreSQL + Redis ≈ $5-20/month

---

## Troubleshooting

### "Cannot connect to database"
- Verify PostgreSQL is running
- Check environment variable references use `${{Postgres.PGHOST}}` syntax

### "CORS error"
- Ensure `ALLOWED_ORIGINS` includes your frontend URL exactly
- Include protocol (`https://`)

### "Worker not processing tasks"
- Verify Redis is running
- Check `CELERY_BROKER_URL` is correctly configured

### "Frontend shows blank page"
- Check browser console for errors
- Verify `VITE_API_URL` points to the correct backend

---

## Alternative: Single-Service Deployment

If you want a simpler setup, you can deploy just the backend API with the frontend served statically:

1. Build frontend locally: `cd frontend && npm run build`
2. Copy `dist/` to `backend/static/`
3. Configure FastAPI to serve static files
4. Deploy single Dockerfile

However, the multi-service approach is recommended for better scalability and separation of concerns.
