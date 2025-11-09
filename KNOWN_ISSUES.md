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
**Status**: UX/Analytics Issue
**Priority**: High
**Date Identified**: 2025-11-08

**Description**:
There is no UI to view the execution history for scheduled jobs. Users cannot see aggregated statistics, success/failure trends, or detailed execution logs for individual jobs. This makes it difficult to understand job performance, troubleshoot failures, or track improvements over time.

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
- [ ] Add "Execution History" tab/page for each job
- [ ] Display table of recent executions (last 50-100)
- [ ] Show aggregated statistics (success rate, avg duration, total items)
- [ ] Implement execution detail view with full logs
- [ ] Add charts for success rate trends over time
- [ ] Filter executions by status and date range
- [ ] Link from execution to reports created during that execution
- [ ] Show currently running execution with live progress
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
**Status**: Critical Performance Issue
**Priority**: High
**Date Identified**: 2025-11-08

**Description**:
When start scripts are run multiple times without properly stopping previous instances (especially after failures or errors), duplicate Celery worker processes accumulate, causing severe performance degradation. The `stop_all.sh` script fails to reliably kill Celery workers, leading to process leaks that consume CPU, memory, and database connections.

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
