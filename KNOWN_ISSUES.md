# Known Issues & Feature Backlog

This document tracks known issues, limitations, and planned features for the Marketing Hunting application.

## Known Issues

### 1. Duplicate Logging with Celery Multiprocessing
**Status**: Known Limitation
**Priority**: Medium
**Date Identified**: 2025-11-08

**Description**:
When running Celery workers with `concurrency=2` (or higher), all log entries appear duplicated in both console output and log files. This occurs because each worker process independently executes the `after_setup_logger` signal handler and adds handlers to its own root logger instance.

**Examples**:
```
2025-11-08 19:47:39 | INFO | celery.worker.consumer.connection | Connected to redis://localhost:6379/0
2025-11-08 19:47:39 | INFO | celery.worker.consumer.connection | Connected to redis://localhost:6379/0
2025-11-08 19:47:40 | INFO | celery_app.celery | ✅ Celery worker is ready and waiting for tasks
2025-11-08 19:47:40 | INFO | celery_app.celery | ✅ Celery worker is ready and waiting for tasks
```

**Impact**:
- Log files grow twice as fast as expected
- Console output is cluttered with duplicate entries
- Makes it harder to read logs during debugging
- Each worker legitimately logs its own startup/shutdown messages (which is technically correct but visually confusing)

**Root Cause**:
Celery's `prefork` pool creates separate worker processes via forking. Each process gets its own copy of the Python logging module state and independently logs to the same handlers (console and file).

**Workarounds Attempted**:
1. ❌ Using global flag to prevent duplicate handler setup - doesn't work across forked processes
2. ❌ Queue-based logging (QueueHandler/QueueListener) - caused `BrokenPipeError` due to multiprocessing.Queue created before fork

**Potential Solutions** (not yet implemented):
1. **Redis-based log aggregation** (Quick win - uses existing Redis infrastructure)
   - Each worker writes to Redis stream/list
   - Single process reads and writes to file
   - Natural deduplication
   - Pros: Fast to implement, scales to any concurrency
   - Cons: Adds Redis dependency for logging

2. **External logging service** (Production-ready)
   - CloudWatch, Datadog, New Relic (managed, costs money)
   - ELK Stack (self-hosted, free but requires infrastructure)
   - Pros: Full-featured, built-in deduplication, great for production
   - Cons: Requires setup and possibly costs

3. **Process ID filtering** (Simple fix)
   - Only log from main Celery process, filter out worker process logs
   - Pros: Simple to implement
   - Cons: Might miss important worker-specific errors

4. **Accept as known behavior**
   - Document that 2 workers = 2 "ready" messages (semantically correct)
   - Focus on feature development instead
   - Add proper logging infrastructure when scaling to production

**Recommendation**:
Implement Redis-based logging when ready to scale, or adopt a managed logging service (CloudWatch/Datadog) for production deployments.

**Related Files**:
- `backend/celery_app/celery.py` (lines 80-100)
- `backend/scripts/run_celery_worker.sh` (line 20)
- `backend/api/logging_config.py`

---

### 2. Stuck Job Executions After Server Shutdown
**Status**: Partially Fixed
**Priority**: Medium
**Date Identified**: 2025-11-08

**Description**:
When servers are stopped (especially Celery workers), job executions remain marked as "running" in the database indefinitely, causing the UI to show stale job states.

**Impact**:
- UI shows jobs as "running" when they're actually dead
- Users can't tell if a job is actually running or stuck
- Requires manual database cleanup

**Current Solution**:
Manual cleanup query:
```sql
UPDATE job_executions
SET status = 'failed',
    completed_at = NOW(),
    error_message = 'Job interrupted by server shutdown'
WHERE status = 'running' AND completed_at IS NULL;
```

**Future Enhancement Needed**:
- Add a periodic cleanup task that marks jobs as failed if their Celery task ID is not found in the active workers
- Implement heartbeat mechanism for running jobs
- Add job timeout detection
- Create a "cleanup stuck jobs" admin endpoint

**Related Files**:
- `backend/src/models/job_execution.py`
- `backend/celery_app/tasks/scheduled_tasks.py`

---

## Feature Backlog

### High Priority

#### 1. Centralized Logging System
**Description**: Implement production-ready logging with proper aggregation and deduplication
**Dependencies**: Fixes "Duplicate Logging" issue
**Estimate**: 2-3 days
**Options**:
- Redis-based logging (quick win)
- ELK Stack integration
- CloudWatch/Datadog integration

**Acceptance Criteria**:
- [ ] No duplicate log entries
- [ ] Logs from all worker processes aggregated correctly
- [ ] Searchable log history
- [ ] Log rotation and retention policies
- [ ] Performance metrics and monitoring

---

#### 2. Job Execution Monitoring & Cleanup
**Description**: Automated detection and cleanup of stuck/orphaned jobs
**Dependencies**: None
**Estimate**: 1 day

**Acceptance Criteria**:
- [ ] Periodic task to detect stuck jobs (no heartbeat for > 5 minutes)
- [ ] Automatic marking of stuck jobs as failed
- [ ] Admin endpoint to manually cleanup stuck jobs
- [ ] Job timeout configuration per feed
- [ ] Notification when jobs are auto-failed

**Related Files**:
- `backend/celery_app/tasks/scheduled_tasks.py`
- `backend/api/routers/jobs.py`

---

#### 3. Improved Error Handling & Retry Logic
**Description**: Better error handling for API failures, network issues, and rate limits
**Dependencies**: None
**Estimate**: 2 days

**Acceptance Criteria**:
- [ ] Exponential backoff for retries
- [ ] Per-provider error handling (Google API quota, OpenAI rate limits)
- [ ] Detailed error logging with context
- [ ] Automatic retry with different strategies based on error type
- [ ] Circuit breaker pattern for external APIs

---

### Medium Priority

#### 4. Slide-out Panel for Jobs & Feeds Configuration
**Description**: Replace modal popups with slide-out panels for editing job and feed configurations
**Priority**: Medium
**Dependencies**: None
**Estimate**: 1-2 days
**Date Requested**: 2025-11-08

**Current Behavior**:
- Clicking "Edit" on a job or feed opens a modal popup
- Modal obscures the rest of the UI
- Can't see existing configuration while editing

**Desired Behavior**:
- Clicking "Edit" slides out a panel from the right side of the screen
- Panel shows the current configuration in an editable form
- Can see the list of jobs/feeds in the background while editing
- Panel slides closed on save or cancel

**User Benefits**:
- Better UX - can reference other items while editing
- More screen space for configuration fields
- Smoother interaction flow
- Consistent with modern UI patterns (like Gmail, Notion, etc.)

**Acceptance Criteria**:
- [ ] Replace modal with slide-out panel for job configuration editing
- [ ] Replace modal with slide-out panel for feed configuration editing
- [ ] Panel animates in from the right side
- [ ] Panel overlays content but doesn't fully block the view
- [ ] ESC key and click-outside-panel closes the panel
- [ ] Save/Cancel buttons at bottom of panel
- [ ] Panel width responsive (e.g., 40-50% of screen on desktop, 80-90% on tablet, 100% on mobile)
- [ ] Form validation works the same as current modal

**Related Files**:
- `frontend/src/pages/Jobs.tsx`
- `frontend/src/pages/Feeds.tsx`
- `frontend/src/components/` (may need new SlideOutPanel component)

**Design Reference**:
- Similar to Gmail's compose panel
- Similar to Notion's page properties panel
- Material-UI Drawer component with permanent=false and anchor="right"

---

#### 5. Real-time Job Progress Updates
**Description**: WebSocket/SSE support for live job progress in UI
**Dependencies**: None
**Estimate**: 2-3 days

**Acceptance Criteria**:
- [ ] WebSocket endpoint for job progress
- [ ] Frontend subscribes to job updates
- [ ] Real-time progress bar updates
- [ ] Live log streaming to UI
- [ ] Completion notifications

---

#### 6. Brand Extraction Improvements
**Description**: Enhanced brand detection with better accuracy
**Dependencies**: None
**Estimate**: 3-4 days

**Acceptance Criteria**:
- [ ] Brand entity resolution (dedupe similar names)
- [ ] Confidence scores for extracted brands
- [ ] User feedback mechanism to improve extraction
- [ ] Support for brand aliases and variations
- [ ] Industry/category classification for brands

---

#### 7. Performance Optimization
**Description**: Optimize database queries and API calls for faster job execution
**Dependencies**: None
**Estimate**: 2-3 days

**Acceptance Criteria**:
- [ ] Database query optimization with proper indexes
- [ ] Batch processing for database writes
- [ ] Caching for frequently accessed data
- [ ] Parallel processing for independent tasks
- [ ] Memory usage optimization for large HTML processing

---

### Low Priority

#### 8. Admin Dashboard Enhancements
**Description**: Better admin tools for monitoring and management
**Dependencies**: None
**Estimate**: 3-5 days

**Acceptance Criteria**:
- [ ] System health dashboard
- [ ] Celery worker monitoring
- [ ] Database statistics and health
- [ ] Manual job control (pause, resume, cancel)
- [ ] Bulk operations for jobs and reports

---

#### 9. Export & Reporting Features
**Description**: Enhanced export capabilities and custom reports
**Dependencies**: None
**Estimate**: 2-3 days

**Acceptance Criteria**:
- [ ] PDF export for reports
- [ ] Custom date range exports
- [ ] Scheduled report delivery via email
- [ ] Custom report templates
- [ ] Data visualization and charts

---

#### 10. Brand Contact Management & Outreach System
**Description**: Contact database for brand editors/reps with LinkedIn integration and AI-powered email drafting
**Priority**: High (Business Critical)
**Dependencies**: None
**Estimate**: 5-7 days
**Date Requested**: 2025-11-08

**Business Value**:
This feature transforms the app from a passive monitoring tool into an active relationship-building platform, enabling users to immediately act on brand mentions by contacting the right people.

**Current Gap**:
- No way to track brand contacts (editors, PR reps, marketing managers)
- Manual research required to find contact information
- No quick way to reach out when a brand mention appears

**Desired Features**:

**Phase 1: Contact Database (3 days)**
- Database schema for brand contacts (name, title, email, phone, LinkedIn URL, brand association)
- UI to view/add/edit contacts for each brand
- "View Contacts" button on each report showing brand mentions
- Contact detail modal/panel showing full contact info
- Manual contact entry form

**Phase 2: LinkedIn Scraping (2 days)**
- LinkedIn profile scraper to find people working at brands
- Search for specific roles (Editor, PR Manager, Marketing Director, etc.)
- Extract: name, title, current company, LinkedIn URL, email (if available)
- Store scraped contacts in database with "unverified" flag
- Background job to periodically refresh contact data
- Compliance: Rate limiting, respect LinkedIn ToS, user consent

**Phase 3: AI Email Drafting (2 days)**
- "Draft Email" button next to each contact
- AI generates personalized email based on:
  - The specific brand mention/report
  - Contact's role and company
  - Report context (sentiment, topic, brands mentioned)
  - User's tone preference (casual, professional, etc.)
- Email template variables (user can customize)
- Copy-to-clipboard functionality
- Integration with email client (mailto: link with pre-filled content)

**Acceptance Criteria**:

**Contact Management**:
- [ ] Database schema for contacts with brand relationships
- [ ] API endpoints for CRUD operations on contacts
- [ ] UI to view contacts associated with each brand
- [ ] "View Contacts" button on report cards/list items
- [ ] Contact list panel/modal showing all contacts for a brand
- [ ] Add/edit contact form with validation
- [ ] Contact search and filtering

**LinkedIn Integration**:
- [ ] LinkedIn scraper service (respects ToS and rate limits)
- [ ] Search LinkedIn by brand name + role keywords
- [ ] Extract profile data: name, title, company, LinkedIn URL
- [ ] Store scraped contacts with metadata (source, scraped_at, verified status)
- [ ] Background job to refresh stale contact data
- [ ] UI to view "suggested contacts" from LinkedIn
- [ ] "Import Contact" button to promote suggested contacts to verified
- [ ] Legal compliance check: consent, privacy policy update, ToS compliance

**AI Email Drafting**:
- [ ] "Draft Email" button on contact cards
- [ ] AI prompt that generates email based on report + contact context
- [ ] Email preview modal with editable text
- [ ] Template selection (pitch, follow-up, introduction, thank you)
- [ ] Tone selector (professional, casual, friendly, formal)
- [ ] Copy to clipboard functionality
- [ ] "Open in Email Client" button (mailto: link)
- [ ] Save drafted emails for later reference
- [ ] Track sent emails (manual logging)

**Database Schema**:
```sql
-- Brand Contacts table
CREATE TABLE brand_contacts (
    id UUID PRIMARY KEY,
    brand_name VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    linkedin_url TEXT,
    company VARCHAR(255),
    notes TEXT,
    source VARCHAR(50), -- 'manual', 'linkedin', 'import'
    verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_contacted_at TIMESTAMP
);

-- Email Drafts table
CREATE TABLE email_drafts (
    id UUID PRIMARY KEY,
    contact_id UUID REFERENCES brand_contacts(id),
    report_id UUID REFERENCES reports(id),
    subject TEXT,
    body TEXT,
    template_used VARCHAR(100),
    tone VARCHAR(50),
    generated_at TIMESTAMP,
    sent_at TIMESTAMP,
    sent BOOLEAN DEFAULT false
);
```

**Related Files**:
- `backend/src/models/brand_contact.py` (new)
- `backend/src/models/email_draft.py` (new)
- `backend/src/services/linkedin_scraper.py` (new)
- `backend/src/services/email_draft_service.py` (new)
- `backend/api/routers/contacts.py` (new)
- `frontend/src/pages/Contacts.tsx` (new)
- `frontend/src/components/ContactList.tsx` (new)
- `frontend/src/components/EmailDraftModal.tsx` (new)

**Legal & Compliance Considerations**:
- [ ] Update Privacy Policy to cover contact data storage
- [ ] Add user consent for LinkedIn scraping
- [ ] Implement data retention policies for contacts
- [ ] Add GDPR-compliant data export/deletion for contacts
- [ ] Rate limiting for LinkedIn scraping (avoid ban)
- [ ] Respect LinkedIn ToS and robots.txt

**Future Enhancements**:
- Email tracking (open rates, click rates) via tracking pixels
- CRM integration (Salesforce, HubSpot)
- Bulk email campaigns
- Email sequence automation (drip campaigns)
- Contact relationship scoring (engagement level)
- Calendar integration for meeting scheduling

---

#### 11. Multi-tenant Improvements
**Description**: Better isolation and management for multi-tenant features
**Dependencies**: None
**Estimate**: 2-3 days

**Acceptance Criteria**:
- [ ] Tenant-specific configuration
- [ ] Resource quotas per tenant
- [ ] Tenant usage analytics
- [ ] Billing integration hooks
- [ ] Tenant admin portal

---

## Infrastructure & DevOps

### 1. Deployment Automation
**Priority**: High
**Estimate**: 2-3 days

**Tasks**:
- [ ] Docker containerization
- [ ] Docker Compose for local development
- [ ] CI/CD pipeline setup
- [ ] Automated testing integration
- [ ] Production deployment scripts

---

### 2. Monitoring & Alerting
**Priority**: High
**Estimate**: 2-3 days

**Tasks**:
- [ ] Application performance monitoring (APM)
- [ ] Error tracking (Sentry or similar)
- [ ] Uptime monitoring
- [ ] Alert configuration for critical errors
- [ ] Performance metrics dashboard

---

### 3. Security Enhancements
**Priority**: High
**Estimate**: 2-3 days

**Tasks**:
- [ ] Security audit
- [ ] Rate limiting for API endpoints
- [ ] Input validation and sanitization review
- [ ] Secrets management (AWS Secrets Manager, Vault)
- [ ] HTTPS enforcement
- [ ] CORS policy review

---

## Documentation Needed

- [ ] API documentation (OpenAPI/Swagger improvements)
- [ ] Deployment guide
- [ ] Architecture documentation
- [ ] Database schema documentation
- [ ] Troubleshooting guide
- [ ] Contributing guidelines
- [ ] Security best practices

---

## Notes

### Decision Log

**2025-11-08**: Decided to defer duplicate logging fix until we implement centralized logging for production. The current behavior is acceptable for development and doesn't block feature work.

**2025-11-08**: Implemented manual cleanup for stuck jobs. Automated cleanup will be added as part of Job Execution Monitoring feature.

**2025-11-08**: Disabled legacy `fetch_all_enabled_feeds` hourly Celery Beat task. This task used hardcoded RSS feeds from `feeds.yaml` and the legacy `FeedProcessor` class. All feed processing is now managed through the UI-driven job system (`execute_scheduled_job` task) which uses the database for configuration. The legacy task can be re-enabled by uncommenting the beat schedule in `celery.py` if needed.

### Technical Debt

1. **Legacy code in fetch_and_report_db.py**: This file has grown large and should be refactored into smaller, focused modules
2. **Missing unit tests**: Need comprehensive test coverage for providers, services, and API endpoints
3. **Database migrations**: Need proper migration system (Alembic) for schema changes
4. **Configuration management**: Move hardcoded values to environment variables or config files

---

*Last Updated: 2025-11-08*
