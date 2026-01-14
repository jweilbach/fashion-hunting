# Marketing Hunting

**A Lavacake Product**

Marketing Hunting is a comprehensive media tracking and brand monitoring platform designed for fashion industry professionals. Track brand mentions, analyze sentiment, and monitor industry trends across RSS feeds and Google Search.

---

## Features

- **Multi-Source Feed Monitoring**: RSS feeds and Google Custom Search integration
- **AI-Powered Analysis**: Automatic brand extraction, sentiment analysis, and topic classification
- **Real-Time Dashboard**: Live updates with auto-refresh during job execution
- **Scheduled Jobs**: Configure automated feed fetching with Celery task queue
- **Advanced Filtering**: Search and filter reports by brand, sentiment, topic, and date
- **Multi-Tenant Support**: Secure authentication with tenant isolation
- **Progress Tracking**: Real-time job execution progress with detailed metrics
- **Brand Analytics**: Track brand mentions, trends, and sentiment over time

---

## Architecture

**Backend**:
- FastAPI (Python 3.11+)
- PostgreSQL (multi-tenant database)
- Redis (Celery broker and result backend)
- Celery (distributed task queue with 2 concurrent workers)
- OpenAI API (GPT-4o-mini for content analysis)
- Google Custom Search API (web-wide brand tracking)

**Frontend**:
- React 19 with TypeScript
- Material-UI v7 (MUI)
- TanStack Query (React Query)
- Vite build tool
- Framer Motion (animations)
- Recharts (analytics visualizations)

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 14+
- Redis 6+
- OpenAI API key
- Google Custom Search API credentials (optional, for Google Search feeds)

### 1. Clone and Setup Environment

```bash
# Copy environment file
cp .env.example .env

# Edit .env with your credentials:
# - OPENAI_API_KEY
# - POSTGRES_* settings
# - REDIS_* settings
# - GOOGLE_API_KEY (optional)
# - SECRET_KEY for JWT tokens
```

### 2. Database Setup

```bash
# Create PostgreSQL database
createdb fashion_hunting

# Run migrations (from backend directory)
cd backend
source ../.venv/bin/activate
alembic upgrade head
```

See [DATABASE_SETUP.md](DATABASE_SETUP.md) for detailed database configuration.

### 3. Backend Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Start backend API
cd backend
./scripts/run_api.sh
```

The API will be available at `http://localhost:8000`

### 4. Start Celery Worker

```bash
# In a new terminal
source .venv/bin/activate
cd backend
./scripts/run_celery_worker.sh
```

Celery runs with:
- **Concurrency**: 2 workers (processes)
- **Task timeout**: 1 hour
- **Auto-refresh**: Worker restarts required for code changes

### 5. Frontend Setup

```bash
# Install Node dependencies
cd frontend
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

### 6. Create Your Account

1. Navigate to `http://localhost:5173/signup`
2. Create an organization and user account
3. Log in and start configuring feeds

---

## Using the Application

### Adding Feeds

Marketing Hunting supports two types of feed providers:

#### RSS Feeds
1. **RSS URL**: Direct RSS feed from a publication
   - Example: `https://www.vogue.com/feed/rss`
2. **Keyword (Google News)**: Auto-converts keywords to Google News RSS
   - Example: `Versace` → Google News RSS feed

#### Google Search Feeds
1. **Brand Search**: Track specific brand mentions across the web
   - Example: `"Louis Vuitton"`
2. **Keyword Search**: Monitor industry trends and topics
   - Example: `sustainable luxury fashion`

See [FEED_CONFIGURATION_GUIDE.md](FEED_CONFIGURATION_GUIDE.md) for detailed feed setup instructions.

### Creating Scheduled Jobs

1. Go to **Tasks** page
2. Click **Create New Task**
3. Configure:
   - **Name**: Descriptive job name
   - **Feeds**: Select one or more feeds
   - **Brands**: (Optional) Track specific brands
   - **Max Items**: Limit per job execution (default: 10)
   - **Schedule**: Cron expression for automation
4. Click **Run Now** to execute immediately or wait for scheduled time

### Viewing Reports

- **Dashboard**: Overview with recent reports, sentiment distribution, and top brands
- **Reports**: Searchable table with filtering by brand, sentiment, topic, and date
- **History**: Job execution history with success/failure tracking

---

## Configuration Files

### Environment Variables (.env)

Key configuration options:

```bash
# OpenAI API
OPENAI_API_KEY=sk-proj-...

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=fashion_hunting
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# Redis (Celery)
REDIS_HOST=localhost
REDIS_PORT=6379
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google Custom Search (optional)
GOOGLE_API_KEY=AIza...
GOOGLE_SEARCH_ENGINE_ID=665c214f...

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### Job Configuration Options

When creating a job, you can configure:

```python
{
  "name": "Daily Brand Monitoring",
  "feed_ids": ["uuid1", "uuid2"],
  "brand_ids": ["uuid3", "uuid4"],
  "max_items_per_run": 20,  # Total items to process
  "enable_html_brand_extraction": true,  # Fetch full article HTML
  "max_html_size_bytes": 500000,  # Limit HTML fetch size
  "ignore_brand_exact": ["Sale", "New"],  # Exclude false positives
  "ignore_brand_patterns": ["^[0-9]+$"],  # Regex exclusions
  "google_search": {
    "results_per_query": 10,  # Results per feed
    "date_restrict": "d7"  # Last 7 days
  }
}
```

---

## Running in Production

### Using Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Production Setup

1. **Set environment to production**:
   ```bash
   ENV=production
   DEBUG=false
   ```

2. **Use process manager** (e.g., systemd, supervisor):
   ```bash
   # Example systemd service for FastAPI
   [Unit]
   Description=Marketing Hunting API
   After=postgresql.service redis.service

   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/opt/marketing_hunting
   Environment="PATH=/opt/marketing_hunting/.venv/bin"
   ExecStart=/opt/marketing_hunting/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000

   [Install]
   WantedBy=multi-user.target
   ```

3. **Configure reverse proxy** (nginx):
   ```nginx
   server {
       listen 80;
       server_name marketing-hunting.example.com;

       location / {
           proxy_pass http://localhost:5173;
       }

       location /api {
           proxy_pass http://localhost:8000;
       }
   }
   ```

---

## Utility Scripts

### Start All Services
```bash
./start_all.sh
```
Starts PostgreSQL, Redis, FastAPI, Celery worker, and React frontend.

### Stop All Services
```bash
./stop_all.sh
```
Gracefully stops all running services.

### Monitor Logs
```bash
./monitor_logs.sh
```
Tail all application logs in real-time.

---

## API Documentation

Once the backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

- `POST /api/v1/auth/login` - User authentication
- `POST /api/v1/auth/signup` - Create account
- `GET /api/v1/reports` - List reports with filtering
- `GET /api/v1/brands` - List tracked brands
- `GET /api/v1/feeds` - List configured feeds
- `GET /api/v1/jobs` - List scheduled jobs
- `POST /api/v1/jobs/{id}/run` - Execute job immediately
- `GET /api/v1/analytics/overview` - Dashboard analytics

---

## Development

### Project Structure

```
abmc_phase1/
├── backend/
│   ├── src/
│   │   ├── models/          # SQLAlchemy models
│   │   ├── repositories/    # Data access layer
│   │   ├── services/        # Business logic
│   │   ├── providers/       # Feed providers (RSS, Google)
│   │   ├── processors/      # Content processors
│   │   └── api/             # FastAPI routes
│   ├── celery_app/          # Celery configuration
│   ├── scripts/             # Helper scripts
│   └── alembic/             # Database migrations
├── frontend/
│   ├── src/
│   │   ├── pages/           # React pages
│   │   ├── components/      # Reusable components
│   │   ├── api/             # API client
│   │   └── types/           # TypeScript types
│   └── public/
├── database/                # PostgreSQL data
└── .venv/                   # Python virtual environment
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Code Style

**Backend**:
- Black (code formatting)
- Flake8 (linting)
- Type hints with mypy

**Frontend**:
- ESLint (linting)
- Prettier (formatting)
- TypeScript strict mode

---

## Troubleshooting

### Celery Workers Not Updating Code

**Issue**: Progress tracking or new features not working in Celery tasks.

**Solution**: Restart Celery workers to reload Python modules:
```bash
pkill -f "celery.*worker"
cd backend
./scripts/run_celery_worker.sh
```

### Dashboard Not Auto-Refreshing

**Issue**: Dashboard doesn't update when jobs are running.

**Solution**: Check that job executions are being created:
```bash
psql -d fashion_hunting -c "SELECT * FROM job_executions ORDER BY started_at DESC LIMIT 5;"
```

### Google Search API Quota Exceeded

**Issue**: Google Search feeds returning errors.

**Solution**:
- Free tier: 100 queries/day
- Use RSS feeds for high-frequency monitoring
- Upgrade to paid tier: $5/1,000 queries

### Database Connection Errors

**Issue**: Cannot connect to PostgreSQL.

**Solution**:
```bash
# Check PostgreSQL is running
pg_isready

# Verify credentials in .env
psql -U postgres -d fashion_hunting -c "SELECT 1;"
```

---

## Additional Documentation

- [DATABASE_SETUP.md](DATABASE_SETUP.md) - Database configuration and migrations
- [FEED_CONFIGURATION_GUIDE.md](FEED_CONFIGURATION_GUIDE.md) - Feed types and examples
- [GOOGLE_SEARCH_SETUP.md](GOOGLE_SEARCH_SETUP.md) - Google API configuration
- [OPTIMIZATION_AUDIT.md](OPTIMIZATION_AUDIT.md) - Performance tuning guide

---

## API Costs

### OpenAI API (GPT-4o-mini)
- **Cost**: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- **Typical usage**: ~1,000 tokens per article
- **Estimate**: $0.0005-0.001 per article processed

### Google Custom Search API
- **Free tier**: 100 queries/day
- **Paid tier**: $5 per 1,000 queries
- **Estimate**: Use RSS feeds to minimize costs

---

## License

Proprietary - Lavacake © 2025

---

## Support

For issues, questions, or feature requests, contact the Lavacake team.
