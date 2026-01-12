# Known Issues & Feature Backlog

This document tracks known issues, limitations, and planned features for the Marketing Hunting application.

## Known Issues

### 1. Selenium Timeout Blocking Job Execution
**Status**: Fixed
**Priority**: High
**Date Identified**: 2025-11-08
**Date Fixed**: 2025-11-08

**Description**:
When Selenium attempts to resolve Google News redirect URLs, it can timeout for up to 6 minutes per article (120 seconds × 3 retries), completely blocking job execution. This happens when Google News provides redirect URLs that are slow or broken.

**Examples**:
```
2025-11-08 20:51:40 | INFO  | Resolving link https://news.google.com/rss/articles/CBMi-wFBVV95cUxPMWVNVS1iOTJV...
2025-11-08 20:52:59 | WARNING | Retrying (Retry(total=2...)) after connection broken by 'ReadTimeoutError(...Read timed out. (read timeout=120)')
2025-11-08 20:54:59 | WARNING | Retrying (Retry(total=1...)) after connection broken by 'ReadTimeoutError(...Read timed out. (read timeout=120)')
2025-11-08 20:56:59 | WARNING | Retrying (Retry(total=0...)) after connection broken by 'ReadTimeoutError(...Read timed out. (read timeout=120)')
2025-11-08 20:57:00 | INFO  | Selenium resolver error: HTTPConnectionPool(host='localhost'...): Max retries exceeded
```

**Impact**:
- Jobs can take 6+ minutes per problematic article instead of seconds
- Blocks both Celery workers when 2 jobs hit bad URLs simultaneously
- No progress updates during timeout (appears frozen to user)
- Affects multiple different articles from different publishers (Refinery29, Page Six, etc.)
- Problem is intermittent - depends on which articles Google News returns

**Root Cause**:
1. Selenium's underlying urllib3 HTTP client has a default 120-second read timeout
2. Selenium automatically retries 3 times on timeout (3 × 120s = 360s = 6 minutes max)
3. The `driver.set_page_load_timeout(25)` only controls page load events, not HTTP connection timeouts
4. Google News redirects are unreliable - some redirect URLs hang indefinitely
5. No way to configure urllib3 timeout directly through Selenium's API

**Observed Pattern**:
- Earlier jobs (before 20:21) completed successfully in 1-2 minutes
- Problem started when specific articles appeared in Google News RSS feed
- Different articles cause timeouts at different times
- Same article URL can timeout repeatedly across multiple job runs

**Potential Solutions**:

1. **Reduce Selenium HTTP timeout** (Quick fix - High priority)
   - Monkey-patch urllib3 adapter to reduce timeout from 120s to 10-15s
   - Add custom HTTP adapter with shorter timeout to Selenium driver
   - Pros: Fast to implement, solves immediate problem
   - Cons: Hacky, might break with Selenium updates
   - **Code location**: `backend/src/fetch_and_report_db.py:280-343` (Selenium resolver function)

2. **Skip Selenium for slow URLs** (Medium-term fix)
   - Attempt HTTP resolution first with short timeout (5s)
   - Only use Selenium as last resort
   - Add timeout wrapper around Selenium call
   - Pros: Cleaner, faster for most URLs
   - Cons: Requires refactoring URL resolution logic

3. **Async/concurrent URL resolution** (Long-term fix)
   - Use asyncio to resolve URLs concurrently with timeout
   - Process multiple articles simultaneously within single worker
   - Pros: Much faster overall, better resource utilization
   - Cons: Major refactoring required

4. **Circuit breaker pattern** (Production-ready)
   - Track failed URLs and skip Selenium after N failures
   - Cache known-bad redirect URLs temporarily
   - Pros: Prevents repeated timeouts on same URLs
   - Cons: Requires state management

**Fix Applied**:
Implemented dual timeout configuration to prevent 6-minute hangs:

```python
# Lines 317-324 in backend/src/fetch_and_report_db.py

# Set page load timeout to 30 seconds
# This controls how long Selenium waits for the page to load
driver.set_page_load_timeout(30)

# Configure HTTP timeout for the underlying urllib3 connection
# This prevents 120-second HTTP timeouts that cause 6-minute hangs
if hasattr(driver, 'command_executor') and hasattr(driver.command_executor, '_client_config'):
    driver.command_executor._client_config.timeout = 30
```

**Result**:
- Page load timeouts now occur at 30 seconds instead of hanging indefinitely
- HTTP connection timeouts reduced from 120 seconds to 30 seconds
- Maximum timeout per article: ~30 seconds (vs 6 minutes before)
- Jobs complete much faster, no more multi-minute hangs

**Testing**:
Logs show successful 30-second timeout:
```
Selenium resolver error: Message: timeout: Timed out receiving message from renderer: 30.000
```

**Related Files**:
- `backend/src/fetch_and_report_db.py:317-324` (Selenium resolver with timeout config)
- `backend/src/services/article_processor.py` (calls URL resolution)

---

### 2. Duplicate Logging with Celery Multiprocessing
**Status**: Fixed
**Priority**: Medium
**Date Identified**: 2025-11-08
**Date Fixed**: 2025-11-08

**Description**:
When running Celery workers with `concurrency=2` (or higher), all log entries appeared duplicated in both console output and log files. This occurred because each worker process independently executed the `after_setup_logger` signal handler and added handlers to its own root logger instance.

**Examples**:
```
2025-11-08 19:47:39 | INFO | celery.worker.consumer.connection | Connected to redis://localhost:6379/0
2025-11-08 19:47:39 | INFO | celery.worker.consumer.connection | Connected to redis://localhost:6379/0
2025-11-08 19:47:40 | INFO | celery_app.celery | ✅ Celery worker is ready and waiting for tasks
2025-11-08 19:47:40 | INFO | celery_app.celery | ✅ Celery worker is ready and waiting for tasks
```

**Impact**:
- Log files grew twice as fast as expected
- Console output was cluttered with duplicate entries
- Made it harder to read logs during debugging
- Each worker legitimately logged its own startup/shutdown messages (which was technically correct but visually confusing)

**Root Cause**:
Celery's `prefork` pool creates separate worker processes via forking. Each process gets its own copy of the Python logging module state and independently logs to the same handlers (console and file).

**Fix Applied**:
Configured the Celery logger using the `after_setup_logger` signal to properly clear and set up handlers:

```python
# Lines 83-105 in backend/celery_app/celery.py
@after_setup_logger.connect
def setup_celery_logger(**kwargs):
    """Configure Celery logger with our custom format"""
    from api.logging_config import LOG_FORMAT, DATE_FORMAT
    import sys

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)

    # File handler for persistent logs
    log_file = Path(__file__).parent.parent / "logs" / "celery_worker.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root_logger.addHandler(file_handler)

    # Console handler for real-time output
    console_handler = logging.StreamHandler(sys.__stdout__)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    root_logger.addHandler(console_handler)
```

**Result**:
- Log entries no longer duplicated
- Clean console output
- Consistent logging format across all workers

**Related Files**:
- `backend/celery_app/celery.py` (lines 80-100)
- `backend/scripts/run_celery_worker.sh` (line 20)
- `backend/api/logging_config.py`

---

### 3. No Visual Confirmation After Job Settings Update
**Status**: UX Issue
**Priority**: Low
**Date Identified**: 2025-11-08

**Description**:
When a user updates job settings (configuration, feed selection, brand selection, etc.) and clicks "Save", there is no visual confirmation that the settings were successfully saved. The modal/dialog simply closes without feedback, leaving users uncertain whether the changes were applied.

**Impact**:
- Users unsure if their changes were saved
- No distinction between "Save" and "Cancel" actions from a UX perspective
- Users may try to save multiple times out of uncertainty
- Poor user experience, especially for critical configuration changes

**Current Behavior**:
1. User clicks "Edit" on a job
2. User modifies settings (feeds, brands, schedule, etc.)
3. User clicks "Save"
4. Modal closes immediately with no feedback

**Desired Behavior**:
1. User clicks "Save"
2. Show visual feedback:
   - Success toast/snackbar: "Job settings updated successfully"
   - Brief loading indicator during save operation
   - Optionally show what was changed (e.g., "Updated 3 feeds and 5 brands")
3. Modal closes after confirmation is shown
4. Updated job reflects changes in the UI immediately

**Acceptance Criteria**:
- [ ] Show success toast/snackbar after successful job update
- [ ] Show error toast if update fails with specific error message
- [ ] Add loading state to "Save" button during API call
- [ ] Disable "Save" button while request is in progress
- [ ] Auto-dismiss success message after 3-5 seconds
- [ ] Keep error messages visible until user dismisses them
- [ ] Apply same pattern to Feed settings updates
- [ ] Apply same pattern to Brand settings updates

**Implementation Options**:
1. **Material-UI Snackbar** (Recommended)
   - Non-intrusive notification at bottom of screen
   - Auto-dismisses after timeout
   - Consistent with Material Design patterns

2. **Inline success message**
   - Show checkmark icon with "Saved!" text in modal before closing
   - Delay modal close by 1-2 seconds to show confirmation

3. **Toast notification library**
   - Use react-toastify or similar for richer notifications
   - Supports success/error/warning states

**Related Files**:
- `frontend/src/pages/Jobs.tsx` (job editing modal)
- `frontend/src/pages/Feeds.tsx` (feed editing modal)
- `frontend/src/pages/Tasks.tsx` (task/job management)
- May need to add notification component/context

**Example Code**:
```typescript
// Using Material-UI Snackbar
const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' });

const handleSaveJob = async () => {
  try {
    setLoading(true);
    await updateJob(jobId, jobData);
    setSnackbar({ open: true, message: 'Job settings updated successfully', severity: 'success' });
    handleClose();
  } catch (error) {
    setSnackbar({ open: true, message: `Failed to update job: ${error.message}`, severity: 'error' });
  } finally {
    setLoading(false);
  }
};
```

---

### 4. No Visual Indicator for Failed URL Resolution
**Status**: UX/Data Quality Issue
**Priority**: Medium
**Date Identified**: 2025-11-08

**Description**:
When Selenium fails to resolve a Google News redirect URL (timeout, error, etc.), the article is still saved to the reports table but with the unresolved Google News redirect URL instead of the final destination URL. There is no visual indicator in the UI to show that the URL resolution failed, making it difficult for users to identify which articles have incomplete/broken URLs.

**Impact**:
- Articles with unresolved Google News URLs are not clickable/useful
- Users can't easily identify which articles failed URL resolution
- No way to distinguish between successful and failed URL resolutions in the UI
- Reduces data quality - reports contain redirect URLs instead of actual article URLs
- Users may waste time trying to access articles with broken URLs

**Current Behavior**:
1. Job processes article from Google News RSS feed
2. Selenium attempts to resolve redirect URL
3. Selenium fails (timeout, error, broken redirect)
4. Article is saved to reports table with Google News redirect URL (e.g., `https://news.google.com/rss/articles/CBMi...`)
5. Report appears normal in UI with no indication of failure
6. User clicks link and gets Google News redirect error or timeout

**Desired Behavior**:
1. Job processes article from Google News RSS feed
2. Selenium fails to resolve redirect URL
3. Article is saved with unresolved URL AND marked with resolution_failed flag
4. UI displays visual indicator for failed resolution:
   - Asterisk (*) or warning icon next to title
   - Different styling (grayed out, warning color)
   - Tooltip explaining "URL resolution failed - showing Google News redirect"
   - Badge showing "Unresolved URL"
5. User can easily filter/sort by resolution status
6. Option to "Retry URL Resolution" for failed articles

**Acceptance Criteria**:
- [ ] Add `url_resolution_status` field to reports table ('success', 'failed', 'skipped')
- [ ] Update article processor to track URL resolution success/failure
- [ ] Add visual indicator in Reports UI for failed URL resolution:
  - [ ] Asterisk (*) or warning icon next to title
  - [ ] Tooltip with explanation
  - [ ] Different text color or badge
- [ ] Add filter option to show only articles with failed URL resolution
- [ ] Add "Retry Resolution" button/action for failed articles
- [ ] Show count of failed resolutions in job summary
- [ ] Log URL resolution failures separately for monitoring

**Database Schema Change**:
```sql
ALTER TABLE reports ADD COLUMN url_resolution_status VARCHAR(20) DEFAULT 'success';
ALTER TABLE reports ADD COLUMN url_resolution_error TEXT;

-- Index for filtering
CREATE INDEX idx_reports_url_resolution_status ON reports(url_resolution_status);
```

**Implementation Notes**:
- Modify `article_processor.py` to catch URL resolution errors and set status
- Store original Google News URL and resolution error message
- Update Reports.tsx to show visual indicators based on resolution status
- Add background job to periodically retry failed URL resolutions

**Related Files**:
- `backend/src/services/article_processor.py` (URL resolution logic)
- `backend/src/fetch_and_report_db.py` (Selenium resolver)
- `backend/src/models/report.py` (add new fields)
- `frontend/src/pages/Reports.tsx` (display indicators)
- Database migration script (new)

**Example UI Indicators**:
```tsx
// In report card/list item
{report.url_resolution_status === 'failed' && (
  <Tooltip title="URL resolution failed - showing Google News redirect">
    <WarningIcon color="warning" fontSize="small" />
  </Tooltip>
)}

// Or with asterisk
<Typography>
  {report.title}
  {report.url_resolution_status === 'failed' && ' *'}
</Typography>
```

---

### 5. Stuck Job Executions After Server Shutdown
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

### 6. No Job Execution History View
**Status**: PARTIALLY COMPLETED (2026-01-09)
**Priority**: High
**Date Identified**: 2025-11-08

**What Was Implemented**:
- ✅ Created dedicated "History" page showing all job executions
- ✅ Grouped executions by job with expandable previous runs
- ✅ Shows key metrics: status, duration, items processed/failed
- ✅ Real-time progress bar for running jobs
- ✅ Execution details dialog with full logs and error messages
- ✅ Auto-refresh while jobs are running
- ✅ Renamed old "Reports" page to "History" for clarity

**Still Needed**:
- [ ] Aggregated statistics (success rate over time, avg duration)
- [ ] Trend charts for success/failure rates
- [ ] Filter by status and date range
- [ ] Export execution history to CSV
- [ ] Link from execution to reports created during that execution

**Description**:
~~There is no UI to view the execution history for scheduled jobs.~~ Basic execution history view is now available. Users can see job executions grouped by job, with expandable previous runs and detailed execution info. Advanced analytics and filtering features are still needed.

**Current Limitation**:
- Job executions are stored in the `job_executions` table
- No UI to display this data
- Users cannot see:
  - Historical success/failure rates for a specific job
  - Execution timeline (when jobs ran)
  - Performance metrics (items processed, duration)
  - Failure patterns or error messages
  - Comparison between different job runs

**Impact**:
- Cannot diagnose why jobs are failing without direct database access
- No visibility into job performance trends
- Cannot compare success rates before/after configuration changes
- Difficult to identify which feeds or articles are causing failures
- No audit trail for job executions

**Desired Features**:

**1. Job Execution History Page**
- Dedicated page or tab showing all executions for a selected job
- Table/list view with key metrics per execution:
  - Start time, end time, duration
  - Status (success, failed, partial, running)
  - Items processed / items failed / total items
  - Error message (if failed)
  - Link to view detailed execution log

**2. Aggregated Statistics**
- Success rate over time (last 7 days, 30 days, all time)
- Average items processed per execution
- Average execution duration
- Total articles collected by this job
- Trend charts showing:
  - Success/failure rate over time
  - Processing speed trends
  - Items processed per day

**3. Execution Detail View**
- Click on an execution to see:
  - Full execution log
  - List of articles processed in that execution
  - Error messages and stack traces
  - Configuration used for that execution
  - Which feeds/brands were active
  - Progress timeline (which articles succeeded/failed)

**4. Filtering and Search**
- Filter by status (success, failed, partial, running)
- Filter by date range
- Search by error message
- Sort by duration, items processed, date

**Acceptance Criteria**:
- [x] Add "Execution History" tab/page for each job ✅ (History page with grouped executions)
- [x] Display table of recent executions (last 50-100) ✅ (All executions shown, grouped by job)
- [ ] Show aggregated statistics (success rate, avg duration, total items)
- [x] Implement execution detail view with full logs ✅ (Details dialog with logs)
- [ ] Add charts for success rate trends over time
- [ ] Filter executions by status and date range
- [ ] Link from execution to reports created during that execution
- [x] Show currently running execution with live progress ✅ (Progress bar with current item)
- [ ] Export execution history to CSV for analysis

**API Endpoints Needed**:
```typescript
GET /api/jobs/{job_id}/executions?limit=50&offset=0&status=failed
GET /api/jobs/{job_id}/executions/{execution_id}
GET /api/jobs/{job_id}/stats?period=30d
```

**Database Queries**:
```sql
-- Get execution history for a job
SELECT
  id,
  started_at,
  completed_at,
  EXTRACT(EPOCH FROM (completed_at - started_at)) as duration_seconds,
  status,
  items_processed,
  items_failed,
  total_items,
  error_message
FROM job_executions
WHERE job_id = $1
ORDER BY started_at DESC
LIMIT 50;

-- Get aggregated stats for a job
SELECT
  COUNT(*) as total_executions,
  COUNT(*) FILTER (WHERE status = 'success') as successful_executions,
  COUNT(*) FILTER (WHERE status = 'failed') as failed_executions,
  SUM(items_processed) as total_items_processed,
  AVG(items_processed) as avg_items_per_run,
  AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds
FROM job_executions
WHERE job_id = $1
  AND started_at > NOW() - INTERVAL '30 days';

-- Get success rate trend by day
SELECT
  DATE(started_at) as execution_date,
  COUNT(*) as total_runs,
  COUNT(*) FILTER (WHERE status = 'success') as successful_runs,
  ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'success') / COUNT(*), 2) as success_rate
FROM job_executions
WHERE job_id = $1
  AND started_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(started_at)
ORDER BY execution_date DESC;
```

**UI Mockup**:
```tsx
// Job Execution History Component
<Box>
  <Typography variant="h5">Execution History - {jobName}</Typography>

  {/* Stats Cards */}
  <Grid container spacing={2}>
    <Grid item xs={3}>
      <Card>
        <CardContent>
          <Typography color="textSecondary">Success Rate (30d)</Typography>
          <Typography variant="h4">73.7%</Typography>
        </CardContent>
      </Card>
    </Grid>
    <Grid item xs={3}>
      <Card>
        <CardContent>
          <Typography color="textSecondary">Total Executions</Typography>
          <Typography variant="h4">81</Typography>
        </CardContent>
      </Card>
    </Grid>
    <Grid item xs={3}>
      <Card>
        <CardContent>
          <Typography color="textSecondary">Avg Duration</Typography>
          <Typography variant="h4">4.2 min</Typography>
        </CardContent>
      </Card>
    </Grid>
    <Grid item xs={3}>
      <Card>
        <CardContent>
          <Typography color="textSecondary">Articles Collected</Typography>
          <Typography variant="h4">547</Typography>
        </CardContent>
      </Card>
    </Grid>
  </Grid>

  {/* Trend Chart */}
  <LineChart data={successRateByDay} />

  {/* Execution Table */}
  <TableContainer>
    <Table>
      <TableHead>
        <TableRow>
          <TableCell>Started</TableCell>
          <TableCell>Duration</TableCell>
          <TableCell>Status</TableCell>
          <TableCell>Items Processed</TableCell>
          <TableCell>Items Failed</TableCell>
          <TableCell>Actions</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {executions.map(exec => (
          <TableRow key={exec.id}>
            <TableCell>{formatDateTime(exec.started_at)}</TableCell>
            <TableCell>{formatDuration(exec.duration)}</TableCell>
            <TableCell>
              <Chip
                label={exec.status}
                color={exec.status === 'success' ? 'success' : 'error'}
              />
            </TableCell>
            <TableCell>{exec.items_processed} / {exec.total_items}</TableCell>
            <TableCell>{exec.items_failed}</TableCell>
            <TableCell>
              <Button onClick={() => viewDetails(exec.id)}>View Details</Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </TableContainer>
</Box>
```

**Related Files**:
- `frontend/src/pages/Tasks.tsx` (add execution history tab)
- `frontend/src/components/ExecutionHistory.tsx` (new component)
- `backend/api/routes/jobs.py` (add execution history endpoints)
- `backend/src/repositories/job_repository.py` (add execution query methods)

**Implementation Priority**:
This is a high-priority UX enhancement that will significantly improve:
- Troubleshooting capabilities
- Job performance monitoring
- User confidence in the system
- Ability to optimize job configurations based on historical data

**Estimated Effort**: 2-3 days
- Backend API endpoints: 4-6 hours
- Frontend UI components: 8-12 hours
- Charts and visualizations: 4-6 hours
- Testing and polish: 2-4 hours

---

### 7. Google News URL Resolver Extracting Image URLs
**Status**: Fixed
**Priority**: High
**Date Identified**: 2025-11-08
**Date Fixed**: 2025-11-08

**Description**:
The Google News URL resolver (in `fetch_and_report_db.py`) was extracting Google CDN image URLs (`lh3.googleusercontent.com`) instead of actual article URLs. This occurred in the fallback regex pattern that searches for any external URL in the HTML source.

**Example of Bad URL**:
```
https://lh3.googleusercontent.com/-DR60l-K8vnyi99NZovm9HlXyZwQ85GMDxiwJWzoasZYCUrPuUM_P_4Rb7ei03j-0nRs0c4F=w16
```

**Log Evidence**:
```
2025-11-08 21:56:24 | INFO | fetch_and_report_db | GN resolver: script external url -> https://lh3.googleusercontent.com/-DR60l-K8vnyi99NZovm9HlXyZwQ85GMDxiwJWzoasZYCUrPuUM_P_4Rb7ei03j-0nRs0c4F=w16
2025-11-08 21:56:24 | INFO | fetch_and_report_db | Final URL resolved: https://lh3.googleusercontent.com/-DR60l-K8vnyi99NZovm9HlXyZwQ85GMDxiwJWzoasZYCUrPuUM_P_4Rb7ei03j-0nRs0c4F=w16
2025-11-08 21:56:25 | INFO | fetch_and_report_db | Fetching full text from URL https://lh3.googleusercontent.com/-DR60l-K8vnyi99NZovm9HlXyZwQ85GMDxiwJWzoasZYCUrPuUM_P_4Rb7ei03j-0nRs0c4F=w16
```

**Impact**:
- Jobs attempted to fetch article content from image URLs
- Resulted in no meaningful content being extracted
- Caused processing failures for affected articles
- Led to poor quality reports with no text content

**Root Cause**:
The regex pattern `'"(https?://[^"]+)"'` at line 253 was too broad and matched ANY external URL found in the Google News HTML source, including:
- Image URLs from `googleusercontent.com`
- Favicon URLs
- CSS/font URLs
- Other Google CDN assets

**Fix Applied**:
Added filtering logic to skip image URLs and Google CDN URLs:

```python
# Lines 253-264 in backend/src/fetch_and_report_db.py
for m in re.finditer(r'"(https?://[^"]+)"', raw):
    url = m.group(1)
    # Skip image URLs and Google CDN URLs
    if url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico')):
        continue
    if 'googleusercontent.com' in url.lower():
        continue
    if '=w16' in url or '=h16' in url:  # Google image size parameters
        continue
    if is_external(url):
        logger.info("GN resolver: script external url -> %s", url)
        return url
```

**Files Changed**:
- `backend/src/fetch_and_report_db.py:253-264` (URL extraction filtering)

**Testing**:
After fix, the resolver correctly skips image URLs and continues searching for valid article URLs.

---

### 8. Process Leak Causes Performance Degradation
**Status**: Fixed
**Priority**: High
**Date Identified**: 2025-11-08
**Date Fixed**: 2026-01-12

**Fix Applied**:
Updated both `stop_all.sh` and `start_all.sh` to prevent and clean up process leaks:

1. **stop_all.sh improvements**:
   - Escalating signal approach: SIGTERM → SIGINT → SIGKILL
   - Verification after each attempt to confirm processes are dead
   - Clear feedback showing how many processes were found and stopped
   - Returns error code if processes can't be killed

2. **start_all.sh improvements**:
   - Pre-flight checks detect process leaks (>4 Celery processes)
   - Automatically runs stop_all.sh if existing services are found
   - Checks all ports before starting new services
   - Prevents duplicate process accumulation

**Description**:
~~When start scripts are run multiple times without properly stopping previous instances (especially after failures or errors), duplicate Celery worker processes accumulate, causing severe performance degradation.~~ This issue is now fixed. The scripts automatically detect and clean up leaked processes.

**Observed Symptoms**:
- UI becomes extremely slow and unresponsive
- Multiple duplicate Celery worker processes running simultaneously (25+ processes instead of 4)
- Database connection pool exhaustion
- Increased memory usage (multiple Python processes competing for resources)
- Duplicate log entries appearing in logs
- System appears "sluggish" overall

**Evidence**:
```bash
# Before cleanup - process leak
$ ps aux | grep -E "(celery|python|node)" | grep -v grep | wc -l
25

# After proper cleanup
$ ps aux | grep -E "(celery|python|node)" | grep -v grep | wc -l
4
```

**Root Causes**:

1. **Incomplete stop_all.sh cleanup**:
   - `pkill -f "celery"` command in stop_all.sh fails to kill stubborn processes
   - No verification that processes were actually killed
   - Workers may ignore SIGTERM signal

2. **Start script doesn't check for existing processes**:
   - `start_all.sh` doesn't verify services are stopped before starting
   - No pre-flight check for conflicting processes
   - Users may run start script multiple times when things appear broken

3. **Background process management**:
   - Celery workers spawned with `&` in background
   - No PID file tracking to identify processes later
   - Parent shell exits but child processes remain

4. **User workflow patterns**:
   - Error occurs → User runs stop script
   - Stop script fails silently → User runs start script again
   - New processes start while old ones still running
   - Cycle repeats with each troubleshooting attempt

**Impact**:
- **Severe**: UI completely unusable due to performance degradation
- Users unable to diagnose the issue (processes hidden in background)
- Requires manual intervention with `pkill -9` to recover
- Can happen gradually over multiple restart attempts
- Wastes development time troubleshooting "slow UI" instead of actual bugs

**Immediate Workaround**:
```bash
# Force kill all Celery processes and restart cleanly
pkill -9 -f "celery"
cd /path/to/abmc_phase1
./stop_all.sh
./start_all.sh
```

**Proposed Solutions**:

**1. Improve stop_all.sh reliability** (High Priority)
- Use `pkill -9` (SIGKILL) instead of `pkill -15` (SIGTERM) for Celery
- Add verification loop to ensure processes are dead
- Return error code if processes can't be killed
- Add retry logic with escalating signals (TERM → INT → KILL)

```bash
# Enhanced kill_by_name function
kill_by_name() {
    local pattern=$1
    local service=$2

    echo -e "${YELLOW}Stopping $service...${NC}"

    # Try SIGTERM first
    pgrep -f "$pattern" | xargs kill -15 2>/dev/null
    sleep 2

    # Verify and escalate to SIGKILL if needed
    if pgrep -f "$pattern" > /dev/null 2>&1; then
        echo -e "${YELLOW}Processes still running, forcing SIGKILL...${NC}"
        pgrep -f "$pattern" | xargs kill -9 2>/dev/null
        sleep 1
    fi

    # Final verification
    if pgrep -f "$pattern" > /dev/null 2>&1; then
        echo -e "${RED}✗ Failed to stop $service${NC}"
        return 1
    else
        echo -e "${GREEN}✓ $service stopped${NC}"
        return 0
    fi
}
```

**2. Add pre-flight checks to start_all.sh** (High Priority)
- Check for existing processes before starting
- Automatically run stop_all.sh if conflicts detected
- Fail fast with clear error message if processes won't die

```bash
# Add to start_all.sh before starting services
echo "Checking for existing processes..."

if lsof -ti :8000 > /dev/null 2>&1; then
    echo "⚠️  Backend already running on port 8000"
    echo "Running ./stop_all.sh to clean up..."
    ./stop_all.sh
    sleep 2
fi

if pgrep -f "celery.*worker" > /dev/null 2>&1; then
    echo "⚠️  Celery workers already running"
    echo "Running ./stop_all.sh to clean up..."
    ./stop_all.sh
    sleep 2
fi
```

**3. Implement PID file tracking** (Medium Priority)
- Write PID files when starting services
- Use PID files for targeted killing in stop script
- Clean up stale PID files on start

```bash
# In start script
celery -A celery_app.celery worker & echo $! > /tmp/celery_worker.pid

# In stop script
if [ -f /tmp/celery_worker.pid ]; then
    kill -9 $(cat /tmp/celery_worker.pid) 2>/dev/null
    rm /tmp/celery_worker.pid
fi
```

**4. Add process monitoring endpoint** (Low Priority)
- Create admin endpoint `/api/admin/health/processes`
- Show count of running workers and their PIDs
- Expose in UI with warning if count is abnormal
- Allow manual cleanup via API

**5. Implement systemd/supervisord** (Production Solution)
- Replace bash scripts with proper process manager
- Automatic restart on failure
- Better logging and monitoring
- Clean shutdown guarantees
- Prevents process leaks by design

**Acceptance Criteria**:
- [ ] stop_all.sh reliably kills all processes (100% success rate)
- [ ] start_all.sh detects and resolves existing process conflicts
- [ ] Scripts provide clear feedback about what they're doing
- [ ] No zombie processes left after stop_all.sh
- [ ] System remains responsive after multiple restart cycles
- [ ] Add tests to verify cleanup works correctly

**Testing Procedure**:
1. Start services normally with `./start_all.sh`
2. Verify clean process count (4 processes)
3. Run `./start_all.sh` again without stopping
4. Verify it detects conflict and auto-cleans
5. Stop with `./stop_all.sh`
6. Verify all processes are dead (0 processes)
7. Repeat cycle 5 times - verify no leaks

**Related Files**:
- [stop_all.sh](stop_all.sh) (needs enhanced kill logic)
- [start_all.sh](start_all.sh) (needs pre-flight checks)
- [backend/scripts/run_celery_worker.sh](backend/scripts/run_celery_worker.sh) (needs PID tracking)

**Estimated Effort**: 4-6 hours
- Enhanced stop script: 2 hours
- Pre-flight checks in start script: 1 hour
- PID file tracking: 2 hours
- Testing and validation: 1 hour

**Priority Justification**:
This is a **high-priority** issue because:
- Causes complete system failure (unusable UI)
- Difficult to diagnose for users
- Happens frequently during development
- Easy to fix with proper cleanup logic
- Prevents productive development work

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

### 9. Instagram & TikTok Rate Limiting (429 Errors)
**Status**: Open
**Priority**: Medium
**Date Identified**: 2026-01-07

**Description**:
Instagram and TikTok actively block web scraping attempts with 429 "Too Many Requests" errors. This is normal anti-scraping behavior from social media platforms protecting their APIs and data.

**Symptoms**:
```
[apify.instagram-scraper] -> backing off {"statusCode":429,"waitBeforeRetryMS":1001}
[apify.instagram-scraper] -> backing off {"statusCode":429,"waitBeforeRetryMS":2075}
[apify.instagram-scraper] -> backing off {"statusCode":429,"waitBeforeRetryMS":4142}
[apify.instagram-scraper] -> NO RESULTS: is private or has no posts matching the query
```

**Impact**:
- Instagram searches may return 0 results even for valid hashtags
- TikTok searches may fail after multiple requests
- Rate limits are IP-based and affect all searches from same server
- Users can see content in mobile apps but scraping fails
- Affects both Quick Search and scheduled jobs

**Root Cause**:
1. Instagram/TikTok detect automated scraping and return 429 errors
2. Apify correctly backs off with exponential delays (1s, 2s, 4s...)
3. After multiple retries, scraper gives up and returns 0 results
4. Official mobile apps use authenticated APIs with higher rate limits
5. Web scraping hits public endpoints with strict limits

**Why It Happens**:
- **Not an Apify issue** - Apify is working correctly
- **Not a bug** - This is expected anti-scraping behavior
- **Platform limitation** - Instagram/TikTok actively block scrapers
- **Temporary** - Rate limits reset after time (minutes to hours)

**Workarounds**:

1. **Space out requests** (Free)
   - Wait 5-10 minutes between Instagram/TikTok searches
   - Use Quick Search sparingly for testing
   - Schedule jobs with longer intervals (hourly vs every 15 min)

2. **Use different search terms** (Free)
   - Avoid searching same hashtag repeatedly
   - Vary search patterns to distribute load

3. **Residential proxies** (Paid - Apify feature)
   - Rotate IP addresses to avoid rate limits
   - Costs extra money on Apify platform
   - More reliable for production use

4. **Official APIs** (Limited data)
   - Instagram Graph API requires business accounts
   - TikTok API has strict approval process
   - Much more limited data than scraping

**Alternative Providers**:
- **YouTube** - Uses official YouTube Data API v3, no rate limit issues
- **Google Search** - More generous rate limits
- **RSS Feeds** - No rate limiting

**Recommendation**:
Accept rate limiting as inherent limitation of social media scraping. Educate users that:
- Instagram/TikTok searches may fail occasionally
- This is expected behavior, not a bug
- YouTube and Google Search are more reliable alternatives
- For production use, consider paid proxy services

**Related**:
- Quick Search feature (implemented 2026-01-07)
- Social media providers (Instagram, TikTok)

---

### 10. Instagram Keyword Search Not Supported
**Status**: Open
**Priority**: Low
**Date Identified**: 2026-01-07

**Description**:
Instagram provider only supports hashtag, profile, and mentions search types. Keyword search is not available, unlike TikTok which supports keyword searches.

**Current Support**:
- **Instagram**: hashtag, profile, mentions
- **TikTok**: hashtag, keyword, user
- **YouTube**: search, channel, video

**Why**:
The underlying Apify Instagram scraper doesn't provide a keyword search endpoint. Instagram's API and web interface are primarily hashtag-based.

**Workaround**:
- Use hashtags instead of keywords (e.g., #skincare instead of "skincare")
- Use profile searches to get content from specific accounts
- Use TikTok or YouTube for keyword-based searches

**Future Enhancement**:
Could potentially add keyword search by:
1. Using Instagram Graph API (requires business account approval)
2. Using a different scraping provider that supports keywords
3. Converting keywords to hashtags automatically (e.g., "skin care" → #skincare)

**Related**:
- Quick Search feature
- Provider-specific search types

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

**2026-01-09**: Implemented expandable Reports navigation in sidebar with provider-specific reports pages. Key changes:
- Renamed old "Reports" page to "History" (shows job execution history)
- Created new expandable "Reports" section in sidebar with Social Media (Instagram, TikTok, YouTube) and Digital Media (Google News, RSS) categories
- Created provider configuration system (`frontend/src/config/providers.ts`) for easy maintainability - new providers can be added by updating a single config
- New Reports page (`frontend/src/pages/Reports.tsx`) with filtering by provider, sentiment, brand, and search
- Backend updated to support sentiment and brand filtering in reports API
- Fixed provider name mismatch: frontend sends uppercase IDs (TIKTOK, YOUTUBE) but backend stores mixed case (TikTok, YouTube) - added mapping in frontend API

**2025-11-08**: Decided to defer duplicate logging fix until we implement centralized logging for production. The current behavior is acceptable for development and doesn't block feature work.

**2025-11-08**: Implemented manual cleanup for stuck jobs. Automated cleanup will be added as part of Job Execution Monitoring feature.

**2025-11-08**: Disabled legacy `fetch_all_enabled_feeds` hourly Celery Beat task. This task used hardcoded RSS feeds from `feeds.yaml` and the legacy `FeedProcessor` class. All feed processing is now managed through the UI-driven job system (`execute_scheduled_job` task) which uses the database for configuration. The legacy task can be re-enabled by uncommenting the beat schedule in `celery.py` if needed.

### Technical Debt

1. **Legacy code in fetch_and_report_db.py**: This file has grown large and should be refactored into smaller, focused modules
2. **Missing unit tests**: Need comprehensive test coverage for providers, services, and API endpoints
3. **Database migrations**: Need proper migration system (Alembic) for schema changes
4. **Configuration management**: Move hardcoded values to environment variables or config files
5. **Reorganize backend directory structure**: Currently providers and services are mixed in same directories causing confusion. Should separate into clearer structure: `backend/src/providers/` (content providers like InstagramProvider, YouTubeProvider), `backend/src/processors/` (data processors like InstagramProcessor, YouTubeProcessor), `backend/src/services/` (business logic services like QuickSearchService, JobExecutionService), `backend/src/factories/` (factory classes like ProviderFactory, ProcessorFactory). Benefits: Clearer separation of concerns, easier to navigate codebase, follows standard project organization patterns, easier onboarding for new developers. Current issue: provider_factory.py and processor_factory.py are in services directory when they should be in factories directory, processors are in services directory when they should have their own directory. Estimated effort: 2-3 hours (move files, update imports across codebase, test to ensure no breakage). Related files: All files in `backend/src/services/`, `backend/src/providers/`
6. ~~**Job Execution Service needs Provider Factory pattern**~~: **COMPLETED 2025-12-09** - Implemented Provider Factory pattern, deleted 209 lines of duplicate code. All providers now instantiated dynamically through factory. Related files: `backend/src/services/provider_factory.py`, `backend/src/services/job_execution_service.py`
7. ~~**Duplicate brand extraction logic across social media processors**~~: **COMPLETED 2025-12-09** - Created shared `BrandMatcher` utility class, deleted 68 lines of duplicate code across 3 processors. All processors now use centralized brand matching with methods `match_in_hashtags()`, `match_in_text()`, `match_in_mentions()`. Single source of truth for brand matching logic, consistent behavior across platforms, easier to add new strategies. Related files: `backend/src/utils/brand_matcher.py`, `backend/src/services/instagram_processor.py`, `backend/src/services/tiktok_processor.py`, `backend/src/services/youtube_processor.py`. **UPDATE 2025-12-09**: Added AI brand extraction to all social media processors with configurable `enable_ai_brand_extraction` option (default: True). Processors now extract ALL brands from captions/descriptions using AI, then combine with hashtag/mention matching. This finds brands like "Alivelab", "Medicube", "Chanel" mentioned in text that hashtags miss.
8. **Migrate YouTube from Apify to official YouTube Data API v3**: Currently using Apify actor which returns truncated descriptions (~500 chars), preventing AI from extracting brands from product lists mentioned later in descriptions. Need to complete migration to YouTube Data API v3 which returns full descriptions. **Status: COMPLETED (2025-12-22)** - YouTubeAPIProvider created, factory updated, and YouTube API key configured. YouTube jobs now fetch full descriptions with complete product lists. Benefits: Full descriptions with complete product lists, free tier (10,000 quota units/day = ~83 jobs with 20 videos each), more reliable than web scraping, official Google API. Related files: `backend/src/providers/youtube_api_provider.py`, `backend/src/services/provider_factory.py`, `.env`
9. **Separate report pages for Digital Media and Social Media**: Currently all reports (digital media articles, social media posts) are mixed together in a single Reports page. Need dedicated browsing experiences for each content type. Should add navigation tabs under "History" section: "Digital Media" tab showing list/grid of articles with thumbnail images, publication names, headlines, publish dates, and brand mentions; "Social Media" tab showing list/grid of social posts with platform icons (Instagram/TikTok/YouTube), thumbnails, engagement metrics, creators, and brand mentions. Clicking any item should navigate to a dedicated detail page with full content display: For digital media - full article text, all images, publication metadata, all brands mentioned (tracked + untracked); For social media - post content, video player (if applicable), all engagement metrics, creator profile, platform-specific metadata, all brands mentioned. Benefits: Better content discovery, easier to browse by content type, dedicated detail pages allow richer content display, better user experience for PR teams reviewing mentions. Design considerations: Maintain consistent look/feel with current dashboard, use Material-UI components, responsive design for mobile browsing. Estimated effort: 8-10 hours (2-3 hours frontend routing/navigation, 3-4 hours list/grid views, 3-4 hours detail pages). Related files: `frontend/src/pages/DigitalMediaHistory.tsx` (new), `frontend/src/pages/SocialMediaHistory.tsx` (new), `frontend/src/pages/DigitalMediaDetail.tsx` (new), `frontend/src/pages/SocialMediaDetail.tsx` (new), `frontend/src/components/Layout.tsx` (update navigation)
9. **Quick Search mode embedded in Dashboard**: Currently users must go through full feed creation process (Feeds page → create feed → configure → save → Tasks page → run task) just to do a one-time exploratory search. Need a "Quick Search" widget embedded in Dashboard between the Reports section and Analytics section above it. Widget should allow instant one-off searches without creating persistent feeds: Select provider type (Instagram hashtag, TikTok keyword, YouTube search, Google News, RSS), enter search term/URL, optionally set result count (default 10, max 50), click "Search Now" button to execute immediately. Results appear inline below the search widget showing preview cards with key info (thumbnail, title, source, brands mentioned, engagement metrics for social). Each result card has "View Details" and "Save to Reports" buttons. Search doesn't create feed or task in database - it's ephemeral/transient. Benefits: Faster ad-hoc research workflow, test searches before committing to scheduled feeds, explore trending topics/hashtags quickly, better user experience for exploratory tasks, reduces clutter in Feeds/Tasks from one-off searches. Technical considerations: Execute search via background Celery task (don't block UI), stream results as they arrive (use WebSocket or polling), cache results client-side for session (don't persist to DB unless user clicks "Save"), rate limit to prevent abuse (max 5 quick searches per 10 minutes), reuse existing provider/processor infrastructure. UI/UX: Collapsible widget (expanded by default), loading state with progress indicator, error handling for failed searches, clear button to reset form. Estimated effort: 6-8 hours (2-3 hours backend API endpoint for transient search, 2-3 hours frontend widget UI, 2 hours results display and caching). Related files: `frontend/src/pages/Dashboard.tsx`, `frontend/src/components/QuickSearchWidget.tsx` (new), `backend/src/api/quick_search.py` (new), `backend/src/services/quick_search_service.py` (new)
10. **Job execution reporting lacks detail**: Job executions currently only show basic counts like "Processing 5 entries" without information about duplicates detected, failures encountered, or items skipped. This makes troubleshooting difficult and provides no visibility into job health. Should add detailed execution reporting that tracks: duplicate detection (how many items were skipped as duplicates), failure details (which specific items failed and why), success breakdown by provider, processing time per item, memory/resource usage. Should also surface this information in the UI job execution history. Benefits: easier troubleshooting, better visibility into job health, identify problematic feeds/providers, track performance trends. Estimated effort: 4-6 hours. Related files: `backend/src/services/job_execution_service.py`, `backend/src/models/job_execution.py`, `frontend/src/pages/Tasks.tsx`
11. **Expand AI brand extraction to hashtags and comments**: Currently AI brand extraction only analyzes main content (captions, descriptions, titles). Could extend to also analyze hashtags with AI (to catch complex/misspelled brand mentions) and post comments (where users often mention additional brands in replies). This would provide more comprehensive brand coverage but increase AI costs significantly due to volume of comments. Should add configuration options: `enable_ai_hashtag_extraction` and `enable_ai_comment_extraction` (both default: False). Benefits: catch edge cases like "#chanelinspired" or comment threads discussing competing brands. Trade-offs: Higher AI costs (especially for viral posts with thousands of comments), slower processing. Estimated effort: 3-4 hours. Related files: `backend/src/services/tiktok_processor.py`, `backend/src/services/instagram_processor.py`, `backend/src/services/youtube_processor.py`
12. **AI-powered conversational search/assistant**: Add an AI assistant mode where users can ask natural language questions and get insights extracted from reports database. Users type questions like "Which influencers mentioned Color Wow in the last 7 days?" or "Show me trending beauty brands on TikTok this month" and AI queries the database, analyzes reports, and returns structured answers with supporting evidence (links to specific reports). Implementation: LLM with function calling to query reports database (filter by date range, brands, platforms, sentiment), AI analyzes aggregated results and formats response, returns answer with citations (report links, timestamps, metrics), optionally save useful queries as "saved searches" for reuse. Benefits: Natural language interface lowers barrier to data exploration, faster insights without manual filtering/sorting, discover patterns AI notices that humans might miss, competitive intelligence through AI-powered trend analysis. Technical considerations: Use GPT-4 with function calling for database queries, implement query cost controls (limit results per query, rate limiting), cache common queries, ensure AI doesn't hallucinate data (always cite source reports), consider using embeddings for semantic search across report content. UI/UX: Chat-like interface (similar to ChatGPT), collapsible panel on Dashboard or dedicated "AI Assistant" page, show typing indicator while AI processes, display results as cards with expand/collapse, allow follow-up questions in conversation thread. Estimated effort: 10-12 hours (3-4 hours LLM integration with function calling, 3-4 hours database query functions, 2-3 hours frontend chat UI, 2 hours testing and refinement). Related files: `backend/src/services/ai_assistant_service.py` (new), `backend/src/api/ai_assistant.py` (new), `frontend/src/components/AIAssistant.tsx` (new), `frontend/src/pages/Dashboard.tsx` or dedicated page
13. **YouTube transcript extraction for enhanced brand detection**: Currently only analyzing title and description for brand extraction. Many YouTube videos (especially product reviews, tutorials, tutorials, vlogs) mention brands verbally throughout the video that aren't in the description. YouTube provides transcripts/captions (both auto-generated and manual) that could be analyzed for additional brand mentions. Implementation: Use `youtube-transcript-api` library (unofficial but popular, free) to fetch video transcripts, combine transcript text with title + description for AI brand extraction, handle videos without transcripts gracefully (not all videos have them). Benefits: Catch brand mentions that only appear in spoken content (e.g., "I'm using Maybelline mascara" said in video but not written in description), more comprehensive brand coverage especially for casual/conversational content, better detection for unsponsored organic mentions. Trade-offs: Unofficial library could break if YouTube changes (low risk, widely used), transcripts can be very long (10-30 min video = 3000-9000 words), significantly increases AI costs due to larger text analysis (could be 5-10x more tokens per video), auto-generated transcripts may have spelling errors for brand names. Technical considerations: Make transcript extraction optional via config flag `enable_transcript_extraction` (default: False due to cost), truncate very long transcripts (e.g., max 5000 words, prioritize first/last portions where products often mentioned), cache transcripts to avoid re-fetching, handle rate limiting and API errors gracefully, consider transcript language (English only initially). Estimated effort: 3-4 hours (1 hour add library and basic integration, 1-2 hours update YouTubeProcessor to include transcripts, 1 hour testing and error handling). Related files: `backend/src/providers/youtube_api_provider.py`, `backend/src/services/youtube_processor.py`, `requirements.txt`
14. **Instagram Stories scraping and visual brand detection**: Currently InstagramProvider only captures feed posts and reels, missing Instagram Stories which are a major source of influencer brand mentions (product tags, swipe-ups, organic mentions in story frames). Stories expire after 24 hours making them time-sensitive. Implementation options: (1) Use Apify Instagram Scraper with stories support (can fetch recent stories from profiles), (2) Use Instaloader library (open source, can download stories), (3) Monitor story highlights (permanent story collections on profiles). Once stories captured as images/videos, use GPT-4 Vision (multimodal LLM) to analyze each story frame for: brand logos visible in images, product packaging shown, text overlays mentioning brands, tagged products/accounts, swipe-up links. Combine visual analysis with any text captions. Benefits: Capture time-sensitive brand mentions before they disappear, influencers often share authentic product usage in stories more than feed posts, catch visual brand placements (product in hand, on vanity, in background), detect story-specific features like polls/questions about brands, swipe-up affiliate links indicate partnerships. Trade-offs: Stories expire in 24 hours requiring frequent scraping (daily or more), high AI costs for vision model analysis (GPT-4 Vision ~$0.01-0.03 per image), video stories require frame extraction (multiple images per story), Apify Instagram scraper may hit rate limits with frequent story checks, story scraping more fragile/likely to break than feed scraping. Technical considerations: Enable via config `enable_instagram_stories` (default: False due to cost/complexity), scrape stories from tracked influencer accounts only (not hashtag searches), store story images/videos for 7 days for compliance/review, use GPT-4 Vision for image analysis with brand-specific prompts, extract frames from video stories (e.g., 1 frame per 3 seconds), handle story highlights separately (permanent, less urgent), rate limit story scraping (max once per account per 6-12 hours), prioritize high-engagement influencers for story monitoring. UI considerations: Display story frames in carousel format, show timestamp and "expires in X hours" indicator, link to story highlight if available, mark visual vs text brand mentions. Estimated effort: 8-12 hours (2-3 hours add Apify story scraping, 3-4 hours GPT-4 Vision integration for image analysis, 2-3 hours InstagramProcessor updates, 1-2 hours UI for story display). Related files: `backend/src/providers/instagram_provider.py`, `backend/src/services/instagram_processor.py`, `backend/src/ai_client.py` (add vision methods), `frontend/src/components/StoryCarousel.tsx` (new)

---

## PR Firm Feature Requests
*Based on field research conducted 2025-11-19*

**Strategic Positioning**: Marketing Hunting aims to **replace** the current fragmented toolset used by PR firms:
- **MuckRack**: Digital press monitoring and media contact database
- **TVEyes**: Live TV broadcast monitoring
- **Tribe Dynamics**: Social media tracking and influencer content monitoring

Currently, PR firms pay for 3+ separate platforms with overlapping functionality. Marketing Hunting will be the **all-in-one PR intelligence platform** that consolidates media monitoring, contact management, and outreach automation into a single system.

---

## Technical Infrastructure: Apify Integration Strategy

**Apify** is a web scraping and automation platform with 7,000+ pre-built "Actors" (scraping tools) that will **dramatically accelerate** our development timeline and provide enterprise-grade infrastructure.

### Why Apify is Perfect for Marketing Hunting

| Challenge | Apify Solution | Impact |
|-----------|---------------|---------|
| Social media scraping complexity | Pre-built Instagram, TikTok, YouTube scrapers | **Reduce 7-10 day build to 2-3 days integration** |
| Anti-bot detection | Built-in IP rotation, CAPTCHA solving | No need to build custom evasion |
| Scale infrastructure | Cloud-based, handles millions of pages | No DevOps overhead |
| Legal compliance | SOC2, GDPR, CCPA certified | Enterprise-ready from day 1 |
| Maintenance burden | Actors maintained by Apify/community | Scrapers stay working when sites change |

### Apify Coverage for Our Features

#### **1. Social Media Monitoring (Tribe Dynamics Replacement) - Feature #2**
**Apify Actors Available:**
- ✅ **Instagram Scraper** - Posts, profiles, hashtags, comments, stories, reels
- ✅ **TikTok Scraper** - Videos, profiles, hashtags, engagement metrics
- ✅ **YouTube Scraper** - Videos, channels, comments, engagement
- ✅ **Twitter/X Scraper** - Tweets, profiles, hashtags
- ✅ **Social Insight Scraper** - Multi-platform monitoring (all-in-one)
- ✅ **Social Media Influencer Scraper** - Influencer discovery and metrics

**Cost:** ~$45-75/month for Actor rentals + usage credits
**Time Saved:** 7-10 days → 2-3 days (build API integration instead of scraper)

**Implementation:**
```python
# Instead of building Instagram scraper from scratch
from apify_client import ApifyClient

client = ApifyClient(os.getenv('APIFY_API_TOKEN'))

# Run Instagram scraper for brand mentions
run = client.actor("apify/instagram-scraper").call(run_input={
    "search": "#ColorWow OR @ColorWow",
    "resultsLimit": 100,
})

# Fetch scraped posts
for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    # Process influencer post
    save_to_reports(item)
```

---

#### **2. LinkedIn Scraping for Editor Contact Discovery - Feature #5**
**Apify Actors Available:**
- ✅ **LinkedIn Profile Scraper** - Profile data, job history, contact info
- ✅ **LinkedIn Company Scraper** - Employee lists, company info
- ✅ **LinkedIn Search Scraper** - Search for editors by title/company
- ✅ **Social Handle Scraper** - Extract social handles from websites

**Cost:** ~$20-30/month per Actor
**Time Saved:** 3-4 days → 1-2 days

**Use Case:**
- Find all "Beauty Editor" profiles at Vogue, Allure, Byrdie
- Extract contact info and recent activity
- Auto-populate editor database

---

#### **3. Podcast Monitoring - Feature #9**
**Apify Actors Available:**
- ✅ **Apple Podcasts Scraper** - Podcast metadata, episodes, ratings
- ✅ **Spotify Podcast Scraper** - Episodes, descriptions, hosts
- ✅ **YouTube Video Scraper** - Podcast episodes uploaded to YouTube

**Cost:** ~$10-20/month
**Time Saved:** 2-3 days → 1 day

---

#### **4. News Article Scraping Enhancement**
**Apify Actors Available:**
- ✅ **Web Scraper** (General) - Extract structured data from any website
- ✅ **Google News Scraper** - Already using Google News, but Apify can enhance
- ✅ **Article Scraper** - Clean article extraction (better than our current method)

**Current Pain Point:** We're building custom scrapers for each publication
**Apify Solution:** Use general Web Scraper Actor + AI extraction

---

#### **5. What Apify Can't Do (We Still Need to Build)**

❌ **Broadcast TV Monitoring** - No pre-built closed caption scrapers for live TV
   - **Alternative:** Partner with CC data providers or build custom

❌ **AI Brand Extraction** - Apify scrapes content, but we need AI to extract brands
   - **Solution:** Use scraped content as input to our existing AI pipeline

❌ **Multi-LLM Comparison** - Feature #6 requires custom LLM orchestration
   - **Solution:** Build in-house (this is our differentiator)

❌ **Editor Contact CRM** - Database and relationship management
   - **Solution:** Build custom (this is core IP)

---

### Recommended Apify Implementation Strategy

#### **Phase 1: Immediate Wins (Week 1-2)**
1. **Instagram Scraper** - Replace manual Instagram monitoring
   - Actor: `apify/instagram-scraper`
   - Cost: $45/month + usage
   - Integration: 2 days

2. **TikTok Scraper** - Brand mention tracking
   - Actor: `clockworks/tiktok-scraper`
   - Cost: $45/month + usage
   - Integration: 1 day

3. **LinkedIn Profile Scraper** - Editor discovery
   - Actor: `apify/linkedin-profile-scraper`
   - Cost: $30/month + usage
   - Integration: 2 days

**Total Phase 1 Cost:** ~$120/month + $50-100 usage = **$170-220/month**
**Time Saved:** ~8-10 days of development work

---

#### **Phase 2: Expansion (Week 3-4)**
4. **YouTube Scraper** - Video brand mentions
5. **Apple Podcasts Scraper** - Podcast discovery
6. **Twitter/X Scraper** - Tweet monitoring
7. **Article Scraper** - Better article extraction

**Total Phase 2 Cost:** +$60-80/month = **$230-300/month total**

---

### Cost-Benefit Analysis

**Building from Scratch:**
- Instagram scraper: 5-7 days @ $100/hr = $4,000-5,600
- TikTok scraper: 4-5 days = $3,200-4,000
- LinkedIn scraper: 3-4 days = $2,400-3,200
- Maintenance: ~20 hours/month = $2,000/month
- **Total First Year:** $60,000-80,000

**Using Apify:**
- Setup/integration: 5-7 days = $4,000-5,600 (one-time)
- Monthly cost: $300/month = $3,600/year
- Maintenance: ~2 hours/month = $200/month = $2,400/year
- **Total First Year:** $10,000-11,600

**Savings: $50,000-68,000 in Year 1** 💰

---

### Apify Pricing Breakdown

**Recommended Plan:** Apify Team Plan
- **Cost:** $499/month base
- **Includes:** $500 platform credits, team collaboration, priority support
- **Actor Rentals:** ~$200-300/month for needed Actors
- **Total:** ~$700-800/month

**Compare to Competitors:**
- Tribe Dynamics: $2,000-5,000/month ❌
- MuckRack contact database: $800-1,000/month ❌
- Custom dev team: $10,000+/month ❌

**Apify ROI:** We save $10k-20k/month vs. building + competing tools 📈

---

### Risk Mitigation

**Concern:** Vendor lock-in with Apify
**Mitigation:**
- All scraped data stored in our database
- Can build custom scrapers later if needed
- Apify Actors are replaceable (use alternative scrapers)

**Concern:** Actor reliability (maintained by 3rd parties)
**Mitigation:**
- Most critical Actors maintained by Apify (official)
- Monitor Actor performance, have backup Actors
- Build custom fallback scrapers for critical features

**Concern:** Cost scaling
**Mitigation:**
- Monitor usage closely
- Implement caching to reduce scraping frequency
- Optimize scraping runs (don't re-scrape same content)

---

### Implementation Checklist

**Week 1: Setup & Instagram**
- [ ] Sign up for Apify Team plan ($499/month)
- [ ] Get API credentials
- [ ] Set up `apify-client` in Python backend
- [ ] Integrate Instagram Scraper Actor
- [ ] Test brand mention tracking for 3-5 brands
- [ ] Set up scheduled runs (daily scraping)
- [ ] Build database ingestion pipeline

**Week 2: TikTok & LinkedIn**
- [ ] Integrate TikTok Scraper Actor
- [ ] Test influencer discovery and tracking
- [ ] Integrate LinkedIn Profile Scraper
- [ ] Build editor auto-discovery pipeline
- [ ] Test contact enrichment for 10-20 editors

**Week 3: YouTube & Podcasts**
- [ ] Integrate YouTube Scraper
- [ ] Set up video brand mention detection
- [ ] Integrate Apple Podcasts Scraper
- [ ] Build podcast discovery feature

**Week 4: Optimization & Monitoring**
- [ ] Optimize scraping schedules to minimize costs
- [ ] Implement caching and deduplication
- [ ] Set up monitoring dashboards for Apify usage
- [ ] Document all Actor integrations

---

## Alternative Scraping Platforms Comparison

### **Top Competitors to Apify (2025)**

| Platform | Best For | Social Media Support | Pricing Model | Pros | Cons |
|----------|----------|---------------------|---------------|------|------|
| **Apify** | Pre-built actors, ease of use | ✅ Instagram, TikTok, YouTube, Twitter, LinkedIn | $499/month Team + usage credits | 7,000+ actors, great documentation, easy integration | Can get expensive at scale |
| **Bright Data** | Enterprise scale, compliance | ✅ All major platforms + geo-targeting | Pay-as-you-go, enterprise pricing | Best proxy network, 99%+ success rate, compliance support | Expensive ($500-2k+/month) |
| **ScraperAPI** | Developer-friendly API | ✅ Instagram, LinkedIn, general scraping | $49-$249/month tiered | Simple API, auto IP rotation, CAPTCHA solving | Fewer pre-built social scrapers |
| **ScrapeCreators** | Real-time social APIs | ✅ TikTok, Instagram, YouTube, Twitter/X, Reddit | Starting $10/5k credits | 100+ endpoints, clean JSON, affordable | Newer platform, less proven |
| **Zyte** | Speed & reliability | ✅ Instagram (99%+ success), general web | Custom enterprise pricing | Fastest Instagram scraper (2.63s avg), 99%+ success | Expensive, enterprise-focused |
| **Octoparse** | No-code scraping | ✅ TikTok, Instagram, LinkedIn, Twitter/X | Free tier + $75-$249/month | No coding needed, visual interface | Limited API, less flexible |

---

### **Recommendation: Multi-Platform Strategy**

Instead of going all-in on one platform, consider a **hybrid approach**:

#### **Primary: Apify ($499-800/month)**
Use for:
- ✅ Instagram, TikTok, YouTube (pre-built actors)
- ✅ LinkedIn scraping (editor discovery)
- ✅ Podcast directories (Apple Podcasts, Spotify)
- ✅ General web scraping (article extraction)

**Why:** Best balance of pre-built tools, ease of use, and developer experience. Huge time savings.

---

#### **Secondary: Bright Data (Pay-as-you-go, ~$200-500/month)**
Use for:
- ✅ High-volume Instagram/TikTok scraping (better success rates)
- ✅ Geo-targeted scraping (international brand mentions)
- ✅ Enterprise compliance needs
- ✅ Backup when Apify actors fail

**Why:** Superior proxy network and success rates. Use selectively for critical/high-volume scraping.

---

#### **Tertiary: ScrapeCreators ($10-50/month)**
Use for:
- ✅ Real-time TikTok/Instagram data (faster than Apify)
- ✅ Testing and POC work
- ✅ Low-volume, specific endpoint needs

**Why:** Extremely affordable for testing. Good for specific use cases.

---

### **Cost Comparison: Hybrid vs. Single Platform**

**Option 1: Apify Only**
- Monthly cost: $700-800
- Coverage: 90% of needs
- Risk: Single vendor lock-in, potential reliability issues

**Option 2: Hybrid (Recommended)**
- Apify: $500-600 (reduced usage)
- Bright Data: $200-300 (pay-as-you-go for critical scraping)
- ScrapeCreators: $10-20 (testing/backup)
- **Total: $710-920/month**
- Coverage: 99% of needs
- Benefits: Redundancy, best tool for each job, no single point of failure

**Option 3: Bright Data Only**
- Monthly cost: $1,500-3,000+
- Coverage: 100% of needs
- Problem: Way too expensive, overkill for our needs

---

### **Decision Matrix: Which Platform for Which Feature?**

| Feature | Best Platform | Backup Platform | Notes |
|---------|--------------|-----------------|-------|
| **Instagram Scraper** | Apify | Bright Data | Apify has ready actors, Bright Data for scale |
| **TikTok Scraper** | Apify | ScrapeCreators | Both work well, ScrapeCreators is real-time |
| **YouTube Scraper** | Apify | ScraperAPI | YouTube API may be better than scraping |
| **LinkedIn Scraper** | Apify | Bright Data | LinkedIn is restrictive, may need both |
| **Podcast Scraping** | Apify | RSS feeds directly | Apify has Apple Podcasts/Spotify actors |
| **Article Extraction** | Apify | Custom (newspaper3k) | Can build custom as fallback |
| **General Web Scraping** | Apify | ScraperAPI | Apify Web Scraper actor is excellent |

---

### **Final Recommendation**

**Start with Apify exclusively** for first 1-2 months:
- Lowest risk, fastest implementation
- Evaluate performance and costs
- Identify gaps or failure points

**Add Bright Data selectively** if you hit issues:
- Only for high-failure-rate targets (e.g., LinkedIn)
- Geo-specific scraping needs
- Enterprise client compliance requirements

**Keep ScrapeCreators as cheap backup**:
- Real-time social media endpoints
- Development/testing environment
- Failover when primary platforms have issues

**Estimated Monthly Costs:**
- **Month 1-2:** $500-800 (Apify only)
- **Month 3+:** $700-1,000 (Apify + selective Bright Data + ScrapeCreators)

**vs. Building Everything In-House:** $5,000-10,000/month (dev time + infrastructure + maintenance)

**Savings: $48,000-110,000/year** 💰

---

### 1. Event Coverage Tracking & Tag Monitoring
**Priority**: High
**Category**: Social Media & Event Management
**Estimate**: 3-4 days

**Business Context**:
PR firms host events (e.g., 70 attendees) and need to track all social media posts, stories, and articles where attendees tagged brands or mentioned the event. Current manual process is extremely time-consuming.

**Current Pain Point**:
- Manually searching through Instagram stories, posts, Twitter/X, TikTok
- No centralized way to see all brand mentions from event attendees
- Difficult to measure event ROI and brand exposure

**Desired Features**:
- [ ] Social media monitoring for event hashtags and brand tags
- [ ] Aggregate all Instagram/TikTok stories mentioning brands
- [ ] Track who attended and who posted about the event
- [ ] Generate event coverage reports with metrics (reach, engagement, brand mentions)
- [ ] Integration with Tribe Dynamics (social media tracking platform)
- [ ] Automatically collect notifications from authorized social media accounts

**Related to**: Tribe Dynamics integration, Social media scraping

---

### 2. Social Media Tracking & Influencer Monitoring (Tribe Dynamics Replacement)
**Priority**: Critical
**Category**: Social Media Intelligence
**Estimate**: 7-10 days

**Competitive Context**:
**Tribe Dynamics** is currently used for social media tracking and influencer content monitoring. We need to **replace** this functionality entirely, not integrate with it.

**What Tribe Dynamics Does**:
- Tracks influencer posts mentioning brands
- Monitors Instagram Stories, TikTok, YouTube content
- Calculates influencer reach and engagement
- Measures earned media value (EMV) from influencer posts
- Identifies which influencers are organically mentioning brands

**Our Replacement Features**:
- [ ] Instagram monitoring (posts, stories, reels, mentions)
- [ ] TikTok video tracking (brand mentions, hashtags)
- [ ] YouTube video monitoring (product mentions, reviews)
- [ ] Twitter/X brand mention tracking
- [ ] Influencer identification (who's posting about brands)
- [ ] Engagement metrics (likes, comments, shares, reach)
- [ ] Earned Media Value (EMV) calculation
- [ ] Influencer database with reach/engagement stats
- [ ] Automated influencer discovery (find new people posting about brands)
- [ ] Gifting ROI tracking (track which influencers posted after receiving products)
- [ ] Competitor influencer analysis (who's posting about competing brands)

**Technical Approach**:
- Social media APIs (Instagram Graph API, TikTok API, YouTube Data API)
- Web scraping where APIs are limited (Instagram Stories)
- Computer vision for product recognition in images/videos
- NLP for brand mention extraction from captions

**Why We'll Win**:
- Unified platform (don't need separate tool)
- Real-time alerts vs. delayed reporting
- Better AI for brand mention detection
- Integrated with article monitoring (see full media picture)

---

### 3. Broadcast TV & News Segment Monitoring (TVEyes Replacement)
**Priority**: High
**Category**: Broadcast Media Intelligence
**Estimate**: 10-14 days

**Competitive Context**:
**TVEyes** is currently the go-to tool for live TV broadcast monitoring, but PR firms report it "might not get everything." We need to **replace** TVEyes with better, more comprehensive broadcast monitoring.

**What TVEyes Does**:
- Monitors live TV broadcasts across major networks
- Closed caption/subtitle search for brand mentions
- Provides video clips of brand mentions
- Archives broadcast content
- Email alerts for brand mentions on TV

**Our Replacement Features**:
- [ ] Live TV monitoring across all major news networks (CNN, Fox, MSNBC, etc.)
- [ ] Closed caption scraping and indexing
- [ ] Real-time speech-to-text transcription (backup to closed captions)
- [ ] Brand mention detection in transcripts
- [ ] Video clip extraction and storage
- [ ] Link TV segments to corresponding online articles
- [ ] Immediate alerts when clients mentioned on air
- [ ] Broadcast analytics (airtime, reach, sentiment)
- [ ] Morning show tracking (Today Show, GMA, etc.)
- [ ] Late night show monitoring (Tonight Show, Kimmel, etc.)
- [ ] Local news monitoring (major markets)
- [ ] Manual video upload for analysis (for content we missed)

**Technical Approach**:

**Phase 1: Closed Caption Scraping (Week 1-2)**
- Partner with closed caption data providers (e.g., TV Eyes API, or direct CC feeds)
- Alternative: Scrape CC data from network websites
- Index captions in real-time searchable database
- Brand mention detection via keyword matching + NLP

**Phase 2: Video Clip Recording (Week 2-3)**
- Record live TV streams (legally via streaming services or cable)
- Store segments containing brand mentions
- Video storage and CDN integration

**Phase 3: Audio Transcription Backup (Week 3-4)**
- Use Whisper API or AWS Transcribe for audio → text
- Cross-reference with closed captions for accuracy
- Handle segments where CC is unavailable

**Why We'll Win**:
- TVEyes is expensive and clunky
- We provide unified dashboard (articles + social + TV)
- Better AI for brand mention detection (catches more)
- Real-time alerts (faster than TVEyes)
- Integrated analytics (compare TV mentions to article spikes)
- Lower cost (bundled with other features vs. separate subscription)

---

### 4. Print Media Monitoring (PressReader Integration)
**Priority**: Medium
**Category**: Media Monitoring
**Estimate**: 4-5 days

**Business Context**:
PressReader is used to search actual printed media (newspapers, magazines). Need integration to monitor print publications for brand mentions.

**Acceptance Criteria**:
- [ ] Integration with PressReader API
- [ ] Search print publications for brand mentions
- [ ] OCR for scanned print media (if not available via API)
- [ ] Track magazine feature placements
- [ ] Link print mentions to digital versions (if available)

**Research Needed**:
- [ ] PressReader API availability and pricing
- [ ] Alternative print media databases
- [ ] OCR quality for print scanning

---

### 5. Media Contact Database & Editor Tracking (MuckRack Replacement)
**Priority**: Critical
**Category**: Contact Intelligence & CRM
**Estimate**: 8-10 days

**Competitive Context**:
**MuckRack** (and Cision) are the industry-standard media contact databases. PR firms pay $7k-12k/year per seat for these tools. We need to **replace** MuckRack by building a superior, automatically-updated media contact database.

**What MuckRack Does**:
- Database of journalists, editors, reporters with contact info
- Track who writes about what topics ("beats")
- Search for editors covering specific topics
- Contact information (email, phone, social media)
- Article history for each journalist
- Media outlet information
- Pitch tracking (who you've contacted)
- Press release distribution

**Our Replacement Features**:

**Phase 1: Automated Editor Discovery (Days 1-4)**
- [ ] Automatically detect new bylines from tracked publications
- [ ] Extract author names from articles we're already monitoring
- [ ] Build editor profiles automatically (no manual data entry)
- [ ] Track beat/topic for each editor based on article content
- [ ] Alert when new editors start covering relevant topics
- [ ] Track editor beat changes (e.g., beauty editor moves to fashion)
- [ ] Show writing history and recent articles for each editor
- [ ] Identify trending editors (who's writing more frequently)

**Phase 2: Contact Information Discovery (Days 5-7)**
- [ ] LinkedIn scraping for editor profiles
- [ ] Email pattern detection (common formats by publication)
- [ ] Twitter/X account linking
- [ ] Automated contact info enrichment
- [ ] Contact verification (check if email still valid)
- [ ] Track contact information changes over time

**Phase 3: Pitch Intelligence (Days 8-10)**
- [ ] "Suggest Pitch Targets" based on article content analysis
- [ ] Show editor's writing style and preferences
- [ ] Recent article topics for context
- [ ] Best time to pitch (analyze publishing patterns)
- [ ] Competitive advantage: editors NOT in MuckRack (find them first)
- [ ] Pitch tracking (who you've contacted, when, response rate)
- [ ] Relationship scoring (how responsive are they)

**Why We'll Win Over MuckRack**:
- **Automatic updates**: MuckRack data is manually curated and often stale. We discover editors the moment they publish.
- **First-mover advantage**: Find new editors before they're in MuckRack
- **Better context**: See exactly what they wrote recently, not just their bio
- **Integrated workflow**: From finding article → finding editor → pitching, all in one place
- **AI-powered matching**: Smart suggestions for who to pitch based on article content
- **Lower cost**: Bundled with media monitoring vs. separate $10k/year tool
- **Real-time**: MuckRack updates quarterly, we update daily

**Database Schema**:
```sql
CREATE TABLE editors (
    id UUID PRIMARY KEY,
    full_name VARCHAR(255),
    publication VARCHAR(255),
    beat VARCHAR(255), -- e.g., "Beauty", "Fashion", "Lifestyle"
    first_seen_date TIMESTAMP,
    last_article_date TIMESTAMP,
    article_count INTEGER,
    topics TEXT[], -- Array of topics they cover
    email VARCHAR(255),
    phone VARCHAR(50),
    twitter_handle VARCHAR(100),
    linkedin_url TEXT,
    contact_verified BOOLEAN DEFAULT false,
    contact_last_verified TIMESTAMP,
    writing_frequency VARCHAR(50), -- daily, weekly, monthly
    preferred_topics TEXT[],
    pitch_response_rate FLOAT, -- % of pitches that got response
    last_pitched_at TIMESTAMP,
    contact_info_id UUID REFERENCES brand_contacts(id)
);

CREATE TABLE editor_articles (
    id UUID PRIMARY KEY,
    editor_id UUID REFERENCES editors(id),
    report_id UUID REFERENCES reports(id),
    published_date TIMESTAMP,
    topics TEXT[]
);
```

---

### 6. AI-Powered Search Query Results & Multi-LLM Comparison
**Priority**: High
**Category**: AI & Search
**Estimate**: 4-5 days

**Business Context**:
PR teams need to answer natural language queries like "I have really chapped lips" and find relevant articles. They want to compare results from different AI models (ChatGPT, Gemini, Claude) and see which brands are mentioned, editor recommendations vs. expert recommendations.

**Use Case Example**:
1. User inputs query: "I have really chapped lips"
2. System queries ChatGPT, Gemini, Claude
3. Each LLM returns recommended articles
4. System fetches and analyzes those articles
5. Extract: brands mentioned, editor recommendations, expert quotes
6. Compare recommendations across LLMs
7. Generate summary report

**Desired Features**:
- [ ] Natural language search interface
- [ ] Multi-LLM query (ChatGPT, Gemini, Claude in parallel)
- [ ] Fetch and analyze articles recommended by each LLM
- [ ] Extract brand mentions from recommended articles
- [ ] Distinguish between editor recommendations vs. expert recommendations
- [ ] Compare which brands each LLM recommended
- [ ] Show overlap and differences between LLM results
- [ ] Export comparison results

**Acceptance Criteria**:
- [ ] Search page with natural language query input
- [ ] "Compare LLMs" toggle to run query across multiple models
- [ ] Side-by-side comparison view of LLM results
- [ ] Highlight which brands were recommended by each LLM
- [ ] Tag recommendations as "Editor Pick" vs "Expert Rec"
- [ ] Summary showing consensus vs. unique recommendations

**UI Mockup**:
```
┌─────────────────────────────────────────────────────────┐
│ Query: "I have really chapped lips"                    │
│ [Search with ChatGPT] [Gemini] [Claude] [All]          │
└─────────────────────────────────────────────────────────┘

┌──────────┬──────────┬──────────┐
│ ChatGPT  │  Gemini  │  Claude  │
├──────────┼──────────┼──────────┤
│ • Aquaphor│ • Aquaphor│ • Vaseline│
│ • Vaseline│ • La Roche│ • Aquaphor│
│ • Laneige │   Posay   │ • Burt's  │
│           │ • Vaseline│   Bees    │
└──────────┴──────────┴──────────┘

Consensus: Aquaphor (3/3), Vaseline (2/3)
```

---

### 7. Social Media Credential Management & Auto-Collection
**Priority**: Medium
**Category**: Social Media Automation
**Estimate**: 3-4 days

**Business Context**:
Brands like Color Wow give products to influencers, and PR teams need to monitor when those influencers post about the products. Some firms manually check notifications, but this should be automated.

**Desired Features**:
- [ ] Store social media account credentials (secure)
- [ ] Automatically collect notifications from Instagram, TikTok, Twitter/X
- [ ] Filter notifications for brand mentions and product tags
- [ ] Aggregate posts from gifted influencers
- [ ] Track influencer engagement and reach
- [ ] Generate influencer ROI reports

**Security Considerations**:
- [ ] Encrypted credential storage
- [ ] OAuth integration where possible (avoid storing passwords)
- [ ] Per-client credential isolation
- [ ] Audit log for credential access

---

### 8. Export to Google Sheets/Docs
**Priority**: Low (Easy Win)
**Category**: Data Export
**Estimate**: 1 day

**Description**:
Users want to export reports, brand mentions, and analytics to Google Sheets or Google Docs for sharing with clients and team collaboration.

**Acceptance Criteria**:
- [ ] "Export to Google Sheets" button on reports page
- [ ] "Export to Google Docs" for formatted reports
- [ ] Configure which columns/fields to export
- [ ] Google OAuth integration
- [ ] Export filters (date range, brands, publications)
- [ ] Schedule automated exports (daily/weekly reports to Sheets)

**Technical Approach**:
- Google Sheets API integration
- Google Docs API for formatted reports
- OAuth 2.0 for authentication

---

### 9. Podcast Monitoring & Media List Management
**Priority**: High
**Category**: Media Monitoring & Contact Management
**Estimate**: 5-7 days

**Business Context**:
PR firms want to pitch clients to appear on podcasts. Need to find relevant podcasts, track podcast mentions of brands/topics, and build podcast media lists.

**Use Case Example**:
- Client: Color Wow (hair care brand) with founder available for interviews
- Goal: Find beauty/lifestyle podcasts to pitch founder appearance
- Need: List of podcasts covering beauty, hair care, entrepreneurship

**Desired Features**:

**Phase 1: Podcast Discovery & Tracking (3 days)**
- [ ] Search podcast directories (Apple Podcasts, Spotify, etc.)
- [ ] Filter by category, audience size, topic
- [ ] Track podcasts covering specific beats (beauty, fashion, lifestyle)
- [ ] Store podcast metadata (host, episode frequency, audience size)
- [ ] Monitor new podcast episodes for brand mentions

**Phase 2: Podcast Media Lists (2 days)**
- [ ] Create curated podcast media lists by category
- [ ] Tag podcasts with relevant topics/beats
- [ ] Store host contact information
- [ ] Track pitch history (which podcasts were pitched when)
- [ ] Shared media lists across organization

**Phase 3: Podcast Content Analysis (2 days)**
- [ ] Transcribe podcast episodes (Whisper API, AssemblyAI)
- [ ] Extract brand mentions from transcripts
- [ ] Identify when competitors appear on podcasts
- [ ] Alert when relevant topics are discussed

**Acceptance Criteria**:
- [ ] Podcast search and discovery page
- [ ] Podcast database with metadata (host, contact, category, audience)
- [ ] "Create Media List" feature for podcasts
- [ ] Tag and categorize podcasts by topic
- [ ] Track brand mentions in podcast episodes
- [ ] Export podcast media lists
- [ ] Pitch tracking for podcast outreach

**Database Schema**:
```sql
CREATE TABLE podcasts (
    id UUID PRIMARY KEY,
    title VARCHAR(255),
    description TEXT,
    host_name VARCHAR(255),
    host_email VARCHAR(255),
    category VARCHAR(100), -- Beauty, Fashion, Business, etc.
    platform VARCHAR(50), -- Apple, Spotify, etc.
    audience_size INTEGER,
    episode_frequency VARCHAR(50),
    last_episode_date TIMESTAMP,
    topics TEXT[]
);

CREATE TABLE podcast_media_lists (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    category VARCHAR(100),
    created_by UUID,
    shared_across_tenants BOOLEAN DEFAULT false,
    podcasts UUID[] -- Array of podcast IDs
);
```

---

### 10. Shared Media Lists Across Tenants
**Priority**: High
**Category**: Multi-Tenant Collaboration
**Estimate**: 3-4 days

**Business Context**:
When a PR firm onboards a new accessories client, they want to reuse an existing "Accessories Editors" media list that was built for a previous accessories client. Currently, media lists are siloed per client, requiring duplicate work.

**Desired Features**:
- [ ] Mark media lists as "Shared" vs "Private"
- [ ] Shared media lists accessible across all tenants/clients
- [ ] Permission controls (who can view/edit shared lists)
- [ ] Automatically pull editors covering specific beats (e.g., "accessories")
- [ ] Suggest relevant shared media lists when onboarding new clients
- [ ] Version control for shared media lists
- [ ] Track which clients are using which shared lists

**Use Cases**:
1. **Onboard new accessories client** → System suggests existing "Accessories Editors" list
2. **Update shared list** → All clients using that list get updates
3. **Add new editor to "Beauty" list** → Available to all beauty clients

**Acceptance Criteria**:
- [ ] Toggle "Share this list" when creating media lists
- [ ] "Shared Media Lists" library page
- [ ] Browse shared lists by category/beat
- [ ] Copy shared list to client-specific list (with option to keep synced)
- [ ] Permissions: Admin can create shared lists, users can view/copy
- [ ] Track usage: "Used by 5 clients"
- [ ] Automatic editor discovery for shared lists (e.g., auto-add new accessories editors)

**Database Schema**:
```sql
CREATE TABLE media_lists (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    category VARCHAR(100), -- Accessories, Beauty, Fashion, etc.
    is_shared BOOLEAN DEFAULT false,
    created_by UUID,
    organization_id UUID, -- Which org owns this list
    auto_update BOOLEAN DEFAULT false, -- Auto-add new editors matching criteria
    contacts UUID[] -- Array of contact IDs
);

CREATE TABLE media_list_usage (
    id UUID PRIMARY KEY,
    media_list_id UUID REFERENCES media_lists(id),
    tenant_id UUID,
    used_at TIMESTAMP
);
```

---

### 11. Automated Editor Discovery for Shared Lists
**Priority**: High
**Category**: AI & Automation
**Estimate**: 3-4 days

**Business Context**:
When a shared media list exists for "Accessories", the system should automatically find and add new editors who write about accessories, keeping the list fresh without manual updates.

**Desired Features**:
- [ ] Define search criteria for media lists (e.g., "editors writing about accessories")
- [ ] Automated daily/weekly scan for new editors matching criteria
- [ ] Auto-add discovered editors to shared media lists
- [ ] Review queue for suggested editors before auto-adding
- [ ] Track discovery source (which article/publication led to discovery)
- [ ] Confidence score for editor matching (how relevant they are)

**Acceptance Criteria**:
- [ ] "Auto-Update" toggle for media lists
- [ ] Configure search criteria (keywords, publications, topics)
- [ ] Daily background job to discover new editors
- [ ] "Suggested Editors" review page (approve/reject)
- [ ] Notification when new editors are added to lists
- [ ] Show discovery date and source article

**Example Workflow**:
1. Create shared media list: "Accessories Editors"
2. Enable auto-update with criteria: articles about "handbags, jewelry, accessories"
3. System finds new article: "Top 10 Handbags for Fall" by Jane Smith at Vogue
4. System adds Jane Smith to "Suggested Editors" queue
5. Admin approves → Jane Smith added to "Accessories Editors" list
6. All clients using that list now have Jane Smith

---

### 12. Lead Routing & Task Assignment
**Priority**: Medium
**Category**: Workflow & Collaboration
**Estimate**: 3-4 days

**Business Context**:
PR firms mention "divide and conquer" and "lead routing" - they need to assign articles, brand mentions, and outreach tasks to specific team members.

**Desired Features**:
- [ ] Assign articles/reports to team members
- [ ] Task assignment workflow (review article, pitch editor, follow up)
- [ ] Lead routing rules (e.g., all beauty articles → Sarah)
- [ ] Task status tracking (pending, in progress, completed)
- [ ] Comments/notes on assigned tasks
- [ ] Email notifications for new assignments
- [ ] Task dashboard showing assigned vs. completed tasks

**Acceptance Criteria**:
- [ ] "Assign to" dropdown on each report/article
- [ ] Task list page showing assigned tasks
- [ ] Filter by assignee, status, date
- [ ] Automated routing rules (if article matches X → assign to Y)
- [ ] Task completion workflow
- [ ] Activity feed showing task assignments and completions

---

## Summary of PR Firm Priorities

### **Competitive Analysis: Tools We're Replacing**

| Current Tool | Annual Cost | What It Does | Our Replacement Feature | Advantage |
|-------------|-------------|--------------|------------------------|-----------|
| **MuckRack** | $7k-12k/seat | Media contact database | Automated Editor Discovery (#5) | Auto-updating, find editors first, better context |
| **TVEyes** | $500-1k/month | TV broadcast monitoring | Broadcast Monitoring (#3) | Unified platform, better AI, real-time alerts |
| **Tribe Dynamics** | $2k-5k/month | Social media tracking | Social Media Monitoring (#2) | Integrated analytics, lower cost |
| **PressReader** | $300-500/month | Print media search | Print Monitoring (#4) | Optional add-on |

**Total savings for PR firms: $20k-40k/year by replacing these tools with Marketing Hunting**

---

### **Phase 1: Core Competitive Features** (Weeks 1-8)
**Goal**: Replace MuckRack, Tribe Dynamics, and TVEyes with superior alternatives

#### Week 1-2: MuckRack Replacement Foundation
1. **Media Contact Database & Editor Tracking** (#5) - **CRITICAL**
   - Auto-discover editors from articles we're already monitoring
   - Build editor profiles with writing history and contact info
   - First-mover advantage: find editors before they're in MuckRack

#### Week 3-4: Tribe Dynamics Replacement
2. **Social Media Tracking & Influencer Monitoring** (#2) - **CRITICAL**
   - Instagram, TikTok, YouTube brand mention tracking
   - Influencer identification and engagement metrics
   - Earned Media Value (EMV) calculation
   - Integrated with article monitoring (unified view)

#### Week 5-6: Quick Wins & Workflow
3. **AI-Powered Search & Multi-LLM Comparison** (#6) - **HIGH VALUE**
   - Natural language search across all content
   - Compare ChatGPT, Gemini, Claude recommendations
   - Editor vs. expert recommendation tagging

4. **Export to Google Sheets/Docs** (#8) - **EASY WIN**
   - Client reporting automation
   - 1-day implementation, high satisfaction

#### Week 7-8: Strategic Features
5. **Shared Media Lists Across Tenants** (#10) - **EFFICIENCY**
   - Reuse editor lists across clients
   - Auto-populate lists with discovered editors
   - Huge time-saver for onboarding

6. **Automated Editor Discovery for Lists** (#11) - **AUTOMATION**
   - Keep media lists fresh automatically
   - Daily scan for new editors matching criteria

---

### **Phase 2: Advanced Media Monitoring** (Weeks 9-16)
**Goal**: Complete the TVEyes replacement and add differentiating features

#### Week 9-12: TVEyes Replacement
7. **Broadcast TV & News Segment Monitoring** (#3) - **CRITICAL**
   - Closed caption scraping and indexing
   - Video clip extraction for brand mentions
   - Morning show, late night, local news coverage
   - Real-time alerts for TV mentions

#### Week 13-14: Podcast Intelligence
8. **Podcast Monitoring & Media Lists** (#9) - **GROWING CHANNEL**
   - Podcast discovery and tracking
   - Episode transcription and brand mention detection
   - Host contact database
   - Pitch tracking for podcast appearances

#### Week 15-16: Workflow & Collaboration
9. **Lead Routing & Task Assignment** (#12) - **WORKFLOW**
   - Assign articles and outreach tasks to team members
   - Automated routing rules
   - Task tracking and completion

---

### **Phase 3: Premium Features & Scale** (Months 3-6)
**Goal**: Advanced features that create market differentiation

10. **Event Coverage Tracking** (#1)
    - Social media monitoring for events
    - ROI measurement for event activations
    - Influencer attendance and post tracking

11. **Print Media Monitoring** (#4)
    - PressReader integration or alternative
    - Magazine placement tracking
    - Print circulation and reach metrics

12. **Social Media Credential Management** (#7)
    - Secure credential storage
    - Auto-collect notifications
    - Influencer gifting ROI automation

---

### **Success Metrics**

**To Replace MuckRack**:
- [ ] Auto-discover 80%+ of editors from monitored articles
- [ ] Find new editors 30+ days before they appear in MuckRack
- [ ] Contact info accuracy >85%
- [ ] Editor profile completeness >90%

**To Replace Tribe Dynamics**:
- [ ] Track 95%+ of public Instagram/TikTok brand mentions
- [ ] Calculate EMV within 10% accuracy of Tribe Dynamics
- [ ] Real-time alerts (<5 min delay)

**To Replace TVEyes**:
- [ ] Monitor top 20 news networks 24/7
- [ ] Closed caption indexing <1 min delay
- [ ] Brand mention accuracy >90%

**Business Success**:
- [ ] PR firms can cancel MuckRack, Tribe, TVEyes subscriptions
- [ ] 50%+ cost savings vs. buying all three tools separately
- [ ] Single unified platform = better workflow = higher productivity

---

*Last Updated: 2025-11-19*
