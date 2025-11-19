#!/bin/bash
# Monitor all application logs in real-time

LOG_DIR="$(dirname "$0")/backend/logs"

echo "==================================================================="
echo "Monitoring logs from: $LOG_DIR"
echo "==================================================================="
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Use multitail if available, otherwise fall back to tail
if command -v multitail &> /dev/null; then
    multitail -s 2 \
        -l "tail -f $LOG_DIR/api.log" \
        -l "tail -f $LOG_DIR/celery_worker.log"
else
    echo "Tip: Install multitail for better multi-log viewing: brew install multitail"
    echo ""
    echo "--- API Logs (api.log) ---"
    echo "--- Celery Logs (celery_worker.log) ---"
    echo ""

    # Show both logs together with prefixes
    tail -f "$LOG_DIR/api.log" "$LOG_DIR/celery_worker.log" 2>/dev/null | \
        awk '/==> .*api.log <==/    {print "\n\033[0;34m[API]\033[0m"; next}
             /==> .*celery_worker.log <==/  {print "\n\033[0;32m[CELERY]\033[0m"; next}
             {print}'
fi
