# Testing Guide

This document describes the testing infrastructure for the ABMC Phase 1 application.

## Overview

The project uses:
- **Backend**: pytest with pytest-asyncio for Python/FastAPI tests
- **Frontend**: Vitest with React Testing Library for React/TypeScript tests
- **Mocking**: MSW (Mock Service Worker) for API mocking in frontend tests

## Quick Start

### Run All Tests

```bash
# Using the unified test script
./scripts/run-tests.sh

# With coverage
./scripts/run-tests.sh --coverage

# Backend only
./scripts/run-tests.sh backend

# Frontend only
./scripts/run-tests.sh frontend
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

### Directory Structure

```
backend/
├── tests/
│   ├── conftest.py           # Shared fixtures
│   ├── unit/
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
cd backend

# Run all tests
python -m pytest

# Run unit tests only
python -m pytest tests/unit -v

# Run integration tests only
python -m pytest tests/integration -v

# Run with coverage
python -m pytest --cov=src --cov=api --cov-report=html

# Run specific test file
python -m pytest tests/unit/services/test_analytics_service.py -v

# Run tests matching a pattern
python -m pytest -k "test_sentiment" -v
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
│       ├── handlers.ts       # MSW request handlers
│       └── server.ts         # MSW server setup
├── api/__tests__/            # API client tests
├── components/__tests__/     # Component tests
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

Add mock API responses in `src/test/mocks/handlers.ts`:

```tsx
import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/v1/my-endpoint/', () => {
    return HttpResponse.json({ data: 'mocked' })
  }),
]
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

### Backend: "Module not found"

Ensure PYTHONPATH includes backend directory:
```bash
export PYTHONPATH=$PYTHONPATH:/path/to/backend
```

### Frontend: "Cannot find module"

Install dependencies:
```bash
cd frontend && npm install
```

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
