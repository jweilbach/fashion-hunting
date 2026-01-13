# Logging Guide

## Overview

The application uses a centralized logging configuration that includes the module/class name in every log entry for easier debugging and tracing.

## Log Format

```
YYYY-MM-DD HH:MM:SS | LEVEL    | module.name.here                      | Your message
2025-11-08 19:30:15 | INFO     | services.job_execution_service        | Starting execution of scheduled job abc123
```

## How to Use Logging in Your Code

### Step 1: Import the logger

At the top of your Python file, import `get_logger`:

```python
from api.logging_config import get_logger

# Create logger for this module
logger = get_logger(__name__)
```

The `__name__` variable automatically provides the full module path (e.g., `services.job_execution_service`).

### Step 2: Use the logger

Replace all `print()` statements with logger calls:

```python
# ❌ Don't do this
print("Processing item 5")

# ✅ Do this instead
logger.info("Processing item 5")
```

### Log Levels

Use appropriate log levels for different types of messages:

```python
# DEBUG: Detailed information for diagnosing problems
logger.debug(f"Item data: {item}")

# INFO: General informational messages
logger.info(f"Processing item {idx+1}/{total}")

# WARNING: Warning messages for potentially harmful situations
logger.warning(f"Item missing optional field: {field_name}")

# ERROR: Error messages for failures that don't stop execution
logger.error(f"Failed to process item: {error}", exc_info=True)

# CRITICAL: Critical messages for serious failures
logger.critical(f"Database connection lost!")
```

### Including Exception Information

When logging exceptions, use `exc_info=True` to include the full traceback:

```python
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
```

## Examples by Module Type

### In a Service Class

```python
# backend/src/services/job_execution_service.py
from api.logging_config import get_logger

logger = get_logger(__name__)  # Will show as "services.job_execution_service"

class JobExecutionService:
    def execute_job(self, job_id):
        logger.info(f"Starting execution of scheduled job {job_id}")

        try:
            # ... processing ...
            logger.info(f"Job execution completed: {items_processed} processed")
        except Exception as e:
            logger.error(f"Error executing job {job_id}: {e}", exc_info=True)
```

### In a Provider

```python
# backend/src/providers/rss_provider.py
from api.logging_config import get_logger

logger = get_logger(__name__)  # Will show as "providers.rss_provider"

class RSSProvider:
    def fetch_items(self):
        logger.info(f"Fetching items from {len(self.rss_urls)} RSS feeds")

        for url in self.rss_urls:
            logger.debug(f"Processing RSS feed: {url}")
```

### In a Celery Task

```python
# backend/celery_app/tasks/scheduled_tasks.py
from api.logging_config import get_logger

logger = get_logger(__name__)  # Will show as "celery_app.tasks.scheduled_tasks"

@app.task
def run_scheduled_job(job_id: str):
    logger.info(f"Celery task started for job {job_id}")
    # ... task logic ...
    logger.info(f"Celery task completed for job {job_id}")
```

### In an API Router

```python
# backend/api/routers/jobs.py
from api.logging_config import get_logger

logger = get_logger(__name__)  # Will show as "api.routers.jobs"

@router.post("/{job_id}/run")
def run_job(job_id: str):
    logger.info(f"API request to run job {job_id}")
    # ... handler logic ...
```

## Configuration

### Environment Variables

Set the log level in your `.env` file:

```bash
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO
```

### Log Files

- **FastAPI logs**: Console only (stdout)
- **Celery logs**: Both console and `backend/logs/celery_worker.log`

### Reducing Library Noise

The logging config automatically reduces verbosity from noisy libraries:

- `uvicorn.access` → WARNING
- `sqlalchemy.engine` → WARNING
- `celery` → INFO
- `kombu` → WARNING
- `amqp` → WARNING

## Benefits

### Before (without module names):
```
2025-11-08 19:30:15 | INFO     | Starting execution of scheduled job abc123
2025-11-08 19:30:16 | INFO     | Fetching items from 2 RSS feeds
2025-11-08 19:30:17 | INFO     | Processing item 1/10
```
**Problem**: Can't tell which module/class generated each log!

### After (with module names):
```
2025-11-08 19:30:15 | INFO     | services.job_execution_service        | Starting execution of scheduled job abc123
2025-11-08 19:30:16 | INFO     | providers.rss_provider                | Fetching items from 2 RSS feeds
2025-11-08 19:30:17 | INFO     | processors.rss_processor              | Processing item 1/10
```
**Solution**: Easy to trace the flow of execution through different modules!

## Migration Checklist

To update existing code to use the new logging system:

- [ ] Add `from api.logging_config import get_logger` at top of file
- [ ] Add `logger = get_logger(__name__)` after imports
- [ ] Replace all `print()` statements with `logger.info()` or appropriate level
- [ ] Add `exc_info=True` to error logs that catch exceptions
- [ ] Test that logs show the correct module name

## Example Log Output

With the new logging system, you'll see output like this:

```
2025-11-08 19:30:15 | INFO     | celery_app.celery                     | ✅ Celery worker is ready and waiting for tasks
2025-11-08 19:30:15 | INFO     | celery_app.celery                     | Worker concurrency: 2 processes
2025-11-08 19:30:20 | INFO     | celery_app.tasks.scheduled_tasks      | Executing job: Daily Brand Monitoring
2025-11-08 19:30:20 | INFO     | services.job_execution_service        | Starting execution of scheduled job abc123
2025-11-08 19:30:21 | INFO     | services.job_execution_service        | Loading 2 feeds
2025-11-08 19:30:21 | INFO     | providers.rss_provider                | Processing 2 RSS feeds
2025-11-08 19:30:22 | INFO     | providers.rss_provider                | Fetched 15 items from RSS feeds
2025-11-08 19:30:22 | INFO     | processors.rss_processor              | Processing item 1/10: Article Title Here
2025-11-08 19:30:26 | INFO     | processors.rss_processor              | Successfully processed item 1
2025-11-08 19:30:31 | INFO     | services.job_execution_service        | Job execution completed: 10 processed, 0 failed
```

Notice how each log clearly shows which module it came from!
