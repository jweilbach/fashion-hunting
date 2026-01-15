# Testing Guide

This document describes the testing infrastructure for the ABMC Phase 1 application.

## Overview

The project uses:
- **Backend**: pytest with pytest-asyncio for Python/FastAPI tests
- **Frontend**: Vitest with React Testing Library for React/TypeScript tests
- **Mocking**: MSW (Mock Service Worker) for API mocking in frontend tests

## Test Counts (as of Jan 2025)

| Suite | Tests | Description |
|-------|-------|-------------|
| Backend Unit (API) | 84 | Auth, brands, reports, jobs, feeds routers |
| Frontend API | 87 | API client tests (auth, brands, reports, analytics, jobs, feeds, lists) |
| Frontend Context | 10 | AuthContext tests |
| Frontend Components | 9 | ProtectedRoute tests |
| **Total** | **190** | |

## Quick Start

### Run All Tests Locally

**IMPORTANT: The Python virtual environment is at the project root (`.venv/`), not in the backend folder.**

```bash
# Backend tests (must activate venv first!)
cd backend
source ../.venv/bin/activate
python -m pytest tests/unit/api/ -v

# Frontend tests
cd frontend
npm test -- --run
```

### Run Tests with Docker

```bash
# Run all tests in Docker
docker-compose -f docker-compose.test.yml up --build

# Backend tests only
docker-compose -f docker-compose.test.yml up --build backend-tests

# Frontend tests only
docker-compose -f docker-compose.test.yml up --build frontend-tests
```

## Backend Testing

### Virtual Environment Setup

**The virtual environment is located at the project root: `.venv/`**

```bash
# From anywhere in the project
source /path/to/abmc_phase1/.venv/bin/activate

# Or from the backend directory
cd backend
source ../.venv/bin/activate

# Verify you're using the correct Python
which python  # Should show: .../abmc_phase1/.venv/bin/python
```

### Directory Structure

```
backend/
├── tests/
│   ├── conftest.py           # Shared fixtures (auto-loaded by pytest)
│   ├── unit/
│   │   ├── api/              # API router tests (84 tests)
│   │   │   ├── test_auth_router.py      # 18 tests
│   │   │   ├── test_brands_router.py    # 14 tests
│   │   │   ├── test_reports_router.py   # 15 tests
│   │   │   ├── test_jobs_router.py      # 21 tests
│   │   │   └── test_feeds_router.py     # 16 tests
│   │   ├── services/         # Service layer tests
│   │   ├── repositories/     # Repository layer tests
│   │   └── providers/        # Provider tests
│   ├── integration/
│   │   ├── api/              # API endpoint tests
│   │   └── test_database.py  # Database integration tests
│   └── fixtures/             # Test data fixtures
└── pytest.ini                # Pytest configuration
```

### Running Backend Tests

```bash
# IMPORTANT: Always activate venv first!
cd backend
source ../.venv/bin/activate

# Run all unit API tests
python -m pytest tests/unit/api/ -v

# Run all tests
python -m pytest

# Run unit tests only
python -m pytest tests/unit -v

# Run integration tests only
python -m pytest tests/integration -v

# Run with coverage
python -m pytest --cov=src --cov=api --cov-report=html

# Run specific test file
python -m pytest tests/unit/api/test_auth_router.py -v

# Run tests matching a pattern
python -m pytest -k "test_login" -v
```

### Test Markers

Tests can be marked with:
- `@pytest.mark.unit` - Unit tests (fast, no external dependencies)
- `@pytest.mark.integration` - Integration tests (may require database)
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.slow` - Slow tests (heavy processing)

```bash
# Run only unit tests
python -m pytest -m unit

# Run only integration tests
python -m pytest -m integration

# Skip slow tests
python -m pytest -m "not slow"
```

### Writing Backend Tests

```python
# tests/unit/services/test_my_service.py
import pytest
from unittest.mock import MagicMock

class TestMyService:
    @pytest.fixture
    def service(self):
        """Create service with mocked dependencies."""
        mock_db = MagicMock()
        return MyService(db=mock_db)

    @pytest.mark.unit
    def test_some_functionality(self, service):
        """Test description here."""
        result = service.do_something()
        assert result == expected_value
```

### Available Fixtures

From `conftest.py`:
- `test_db_engine` - In-memory SQLite engine
- `test_db_session` - Database session for testing
- `client` - FastAPI TestClient
- `mock_openai` - Mocked OpenAI client
- `mock_apify_client` - Mocked Apify client
- `sample_*_data` - Sample data for various entities

## Frontend Testing

### Directory Structure

```
frontend/src/
├── test/
│   ├── setup.ts              # Test setup (runs before each test)
│   ├── test-utils.tsx        # Custom render functions
│   └── mocks/
│       ├── handlers.ts       # MSW request handlers (environment-aware)
│       └── server.ts         # MSW server setup
├── api/__tests__/            # API client tests (87 tests)
│   ├── auth.test.ts          # 7 tests
│   ├── brands.test.ts        # 11 tests
│   ├── reports.test.ts       # 17 tests
│   ├── analytics.test.ts     # 7 tests
│   ├── jobs.test.ts          # 16 tests
│   ├── feeds.test.ts         # 16 tests
│   └── lists.test.ts         # 13 tests
├── context/__tests__/        # Context tests (10 tests)
│   └── AuthContext.test.tsx  # Auth provider tests
├── components/__tests__/     # Component tests (9 tests)
│   └── ProtectedRoute.test.tsx
└── pages/__tests__/          # Page-level tests
```

### Running Frontend Tests

```bash
cd frontend

# Install dependencies first
npm install

# Run tests in watch mode
npm test

# Run tests once (CI mode)
npm run test:run

# Run with coverage
npm run test:coverage

# Run with UI
npm run test:ui
```

### Writing Frontend Tests

#### Component Tests

```tsx
// src/components/__tests__/MyComponent.test.tsx
import { describe, it, expect } from 'vitest'
import { renderWithProviders, screen } from '../../test/test-utils'
import MyComponent from '../MyComponent'

describe('MyComponent', () => {
  it('renders correctly', () => {
    renderWithProviders(<MyComponent />)
    expect(screen.getByText('Expected Text')).toBeInTheDocument()
  })
})
```

#### API Client Tests

```tsx
// src/api/__tests__/myApi.test.ts
import { describe, it, expect, vi } from 'vitest'
import { myApi } from '../myApi'
import apiClient from '../client'

vi.mock('../client')

describe('myApi', () => {
  it('fetches data correctly', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { items: [] } })

    const result = await myApi.getItems()

    expect(apiClient.get).toHaveBeenCalledWith('/api/v1/items/')
  })
})
```

### Custom Render Functions

The `test-utils.tsx` provides wrapped render functions:

```tsx
import {
  renderWithProviders,  // Full providers (Router, Query, Theme, Auth)
  renderWithTheme,      // Theme only
  renderWithQuery,      // QueryClient only
  createMockUser,       // Mock user data
  createMockReport,     // Mock report data
  createMockList,       // Mock list data
} from '@/test/test-utils'
```

### MSW Handlers

MSW handlers are in `src/test/mocks/handlers.ts`. The handlers are **environment-aware** and work across local development, staging, and production environments.

#### How Environment-Aware Handlers Work

The handlers read `VITE_API_URL` from the environment and create handlers that match both relative and absolute URLs:

```tsx
// handlers.ts reads the API URL from environment
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const API_BASE = '/api/v1'

// createHandler utility creates handlers for BOTH URL patterns
export const createHandler = (method, path, handler) => {
  // Returns handlers for both:
  // - /api/v1/auth/me (relative)
  // - http://localhost:8000/api/v1/auth/me (absolute)
}
```

#### Adding New Handlers

Use the `createHandler` utility to ensure your handlers work in all environments:

```tsx
import { http, HttpResponse } from 'msw'
import { createHandler } from './handlers'

export const handlers = [
  // Environment-aware handler (recommended)
  ...createHandler('get', '/my-endpoint/', () =>
    HttpResponse.json({ data: 'mocked' })
  ),

  // Or manually for non-API routes
  http.get('/health', () => HttpResponse.json({ status: 'ok' })),
]
```

#### Overriding Handlers in Tests

Use `createHandler` when overriding handlers in individual tests:

```tsx
import { server } from '../../test/mocks/server'
import { createHandler } from '../../test/mocks/handlers'
import { HttpResponse } from 'msw'

it('handles error response', async () => {
  // Override for this test only
  server.use(
    ...createHandler('get', '/auth/me', () =>
      HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 })
    )
  )

  // ... test code
})
```

## CI/CD Integration

### GitHub Actions

Tests run automatically on:
- Push to `main`, `develop`, or `justin-dev` branches
- Pull requests to `main` or `develop`

The workflow:
1. Runs backend unit tests
2. Runs frontend lint and tests
3. Builds frontend to verify build success
4. Uploads coverage reports to Codecov

### Railway Deployment

Tests should pass before deploying. The Railway build uses the standard Dockerfiles.

## Coverage Reports

### Backend Coverage

```bash
cd backend
python -m pytest --cov=src --cov=api --cov-report=html
# Open coverage_html/index.html
```

### Frontend Coverage

```bash
cd frontend
npm run test:coverage
# Open coverage/index.html
```

## Best Practices

1. **Unit tests should be fast** - Mock external dependencies
2. **Integration tests test real interactions** - Use test database when needed
3. **Name tests descriptively** - `test_creates_report_with_valid_data`
4. **One assertion per test when possible** - Easier to debug failures
5. **Use fixtures for setup** - Don't repeat setup code
6. **Test edge cases** - Empty lists, null values, error conditions

## Troubleshooting

### Backend: "No module named pytest" or other import errors

**Most common cause**: Virtual environment not activated.

```bash
# The venv is at the PROJECT ROOT, not in backend/
cd backend
source ../.venv/bin/activate  # Note the ../

# Verify correct Python
which python
# Should show: /path/to/abmc_phase1/.venv/bin/python

# NOT: /opt/homebrew/bin/python3 or similar
```

### Backend: "ModuleNotFoundError: No module named 'psycopg2'"

This happens when running tests outside Docker without the venv. The venv has all dependencies installed. If you must run without venv:

```bash
pip install psycopg2-binary  # For PostgreSQL driver
```

### Backend: PYTHONPATH issues

Ensure PYTHONPATH includes backend directory:
```bash
export PYTHONPATH=$PYTHONPATH:/path/to/backend
```

### Frontend: "Cannot find module"

Install dependencies:
```bash
cd frontend && npm install
```

### Frontend: MSW not intercepting requests

If API calls aren't being mocked, check:
1. Handler uses correct URL pattern (use `createHandler` for environment-aware handlers)
2. Server is started in setup.ts
3. Handler is exported in handlers.ts

### Tests timing out

For slow tests, increase timeout:
```python
@pytest.mark.timeout(60)
def test_slow_operation():
    ...
```

```tsx
// vitest
it('slow test', async () => {
  ...
}, { timeout: 10000 })
```

### Docker Compose tests failing

The docker-compose.test.yml requires the images to be built. Run:
```bash
docker-compose -f docker-compose.test.yml build
docker-compose -f docker-compose.test.yml up
```
