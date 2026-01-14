# Practical Testing Plan

> **Note:** This plan focuses on testing **stable, actively-used code** only.
> Given planned refactoring of frontend/backend logic, we prioritize:
> - Core functionality that must work regardless of refactoring
> - API contracts (inputs/outputs) rather than implementation details
> - Code that's unlikely to change significantly

## Current Coverage Status

| Area | File | Tests | Coverage |
|------|------|-------|----------|
| Backend Services | `test_analytics_service.py` | 16 tests | AnalyticsService only |
| Backend API | `test_lists_api.py` | 13 tests | Lists endpoints only |
| Backend DB | `test_database.py` | 8 tests | Model creation (skipped w/o PostgreSQL) |
| Frontend API | `lists.test.ts` | 13 tests | Lists API client only |
| Frontend Components | `ProtectedRoute.test.tsx` | 9 tests | Auth guard only |

**Total: 59 tests | Estimated Coverage: ~15-20%**

---

## Testing Philosophy

### Test Now (Stable Code)
1. **Authentication** - Security-critical, unlikely to change API
2. **API endpoint contracts** - Request/response shapes
3. **Core business logic** - Brand matching, sentiment scoring
4. **Data repositories** - Database queries (these patterns stay stable)

### Defer Until After Refactoring
1. **Page component rendering** - UI will change
2. **Frontend state management** - May restructure
3. **Processor implementations** - May consolidate
4. **Provider internals** - Just test interfaces

---

## Priority 1: Must Test Now

### Backend Auth Router
**File:** `backend/tests/unit/api/test_auth_router.py`

| Test | Why Critical |
|------|-------------|
| Login with valid credentials | Core user flow |
| Login with invalid credentials | Security |
| Token validation | Security |
| Get current user | Used everywhere |

---

### Backend API Routers (Contract Tests)
Test the **request/response contracts**, not implementation details.

**Files to create:**
- `backend/tests/unit/api/test_brands_router.py`
- `backend/tests/unit/api/test_reports_router.py`
- `backend/tests/unit/api/test_jobs_router.py`
- `backend/tests/unit/api/test_feeds_router.py`

For each router, test:
- Valid request → correct response shape
- Invalid request → proper error response
- Auth required → 401 without token
- Not found → 404 response

---

### Backend Job Execution Service
**File:** `backend/tests/unit/services/test_job_execution_service.py`

| Test | Why Critical |
|------|-------------|
| Source type classification | Drives entire processing flow |
| Job status transitions | State machine must work |
| Error handling | Jobs fail gracefully |

---

### Frontend API Clients
**Files to create:**
- `frontend/src/api/__tests__/auth.test.ts`
- `frontend/src/api/__tests__/brands.test.ts`
- `frontend/src/api/__tests__/reports.test.ts`
- `frontend/src/api/__tests__/analytics.test.ts`
- `frontend/src/api/__tests__/jobs.test.ts`
- `frontend/src/api/__tests__/feeds.test.ts`

Test each function:
- Calls correct endpoint
- Sends correct payload
- Returns transformed response
- Handles errors properly

---

### Frontend AuthContext
**File:** `frontend/src/context/__tests__/AuthContext.test.tsx`

| Test | Why Critical |
|------|-------------|
| Login stores token | Auth flow works |
| Logout clears token | Security |
| 401 triggers logout | Auto-logout on expiry |

---

## Priority 2: Test After Refactoring Stabilizes

### Backend Processors
Wait until you've consolidated processor logic, then test:
- Data transformation (input → output)
- Sentiment extraction accuracy
- Brand matching in text

### Backend Providers
Wait until provider interfaces stabilize, then test:
- API call mocking
- Response parsing
- Error handling

### Frontend Pages
Wait until UI refactoring completes, then test:
- Key user flows (not every button)
- Form submissions
- Error states

---

## Recommended Test Files to Create Now

### Backend (8 files)
```
backend/tests/unit/api/
├── test_auth_router.py      # Auth endpoints
├── test_brands_router.py    # Brand CRUD
├── test_reports_router.py   # Report queries
├── test_jobs_router.py      # Job management
└── test_feeds_router.py     # Feed CRUD

backend/tests/unit/services/
└── test_job_execution_service.py  # Job execution flow
```

### Frontend (7 files)
```
frontend/src/api/__tests__/
├── auth.test.ts
├── brands.test.ts
├── reports.test.ts
├── analytics.test.ts
├── jobs.test.ts
└── feeds.test.ts

frontend/src/context/__tests__/
└── AuthContext.test.tsx
```

---

## Estimated Outcome

| Phase | New Tests | Total | Coverage |
|-------|-----------|-------|----------|
| Current | - | 59 | ~15% |
| Priority 1 Complete | +80 | 139 | ~45% |
| Priority 2 (post-refactor) | +60 | 199 | ~65% |

---

## Commands

```bash
# Run all tests
./scripts/run-tests.sh

# Backend with coverage
./scripts/run-tests.sh backend --coverage

# Frontend with coverage
./scripts/run-tests.sh frontend --coverage

# Single backend test file
cd backend && python -m pytest tests/unit/api/test_auth_router.py -v

# Single frontend test file
cd frontend && npm test -- src/api/__tests__/auth.test.ts
```

---

## Next Steps

1. **Implement Priority 1 tests** (~80 tests)
2. **Complete frontend/backend refactoring**
3. **Implement Priority 2 tests** for stabilized code
4. **Add integration tests** for critical workflows
