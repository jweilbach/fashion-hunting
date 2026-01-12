#!/bin/bash

# ABMC Phase 1 - Stop All Servers Script
# This script stops the frontend, backend API, and Celery worker

set -e

echo "🛑 Stopping ABMC Phase 1 servers..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to kill process by port with escalating signals
kill_by_port() {
    local port=$1
    local service=$2

    echo -e "${YELLOW}Stopping $service on port $port...${NC}"

    # Find the process using the port
    local pid=$(lsof -ti :$port 2>/dev/null || true)

    if [ -z "$pid" ]; then
        echo -e "${GREEN}✓ $service is not running${NC}"
        return 0
    fi

    # Attempt 1: SIGTERM (graceful)
    echo -e "${YELLOW}  Sending SIGTERM to PID $pid...${NC}"
    kill -15 $pid 2>/dev/null || true
    sleep 2

    # Check if still running
    if ! lsof -ti :$port > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $service stopped gracefully${NC}"
        return 0
    fi

    # Attempt 2: SIGKILL (force)
    pid=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}  Process still running, forcing SIGKILL...${NC}"
        kill -9 $pid 2>/dev/null || true
        sleep 1
    fi

    # Final verification
    if lsof -ti :$port > /dev/null 2>&1; then
        echo -e "${RED}✗ Failed to stop $service on port $port${NC}"
        return 1
    else
        echo -e "${GREEN}✓ $service stopped${NC}"
        return 0
    fi
}

# Function to kill process by name pattern with escalating signals
kill_by_name() {
    local pattern=$1
    local service=$2
    local max_attempts=3

    echo -e "${YELLOW}Stopping $service...${NC}"

    # Find processes matching the pattern
    local pids=$(pgrep -f "$pattern" 2>/dev/null || true)

    if [ -z "$pids" ]; then
        echo -e "${GREEN}✓ $service is not running${NC}"
        return 0
    fi

    local count=$(echo "$pids" | wc -l | tr -d ' ')
    echo -e "${YELLOW}  Found $count process(es) to stop${NC}"

    # Attempt 1: SIGTERM (graceful)
    echo -e "${YELLOW}  Sending SIGTERM...${NC}"
    echo "$pids" | xargs kill -15 2>/dev/null || true
    sleep 2

    # Check if still running
    pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [ -z "$pids" ]; then
        echo -e "${GREEN}✓ $service stopped gracefully${NC}"
        return 0
    fi

    # Attempt 2: SIGINT
    echo -e "${YELLOW}  Processes still running, sending SIGINT...${NC}"
    echo "$pids" | xargs kill -2 2>/dev/null || true
    sleep 2

    # Check if still running
    pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [ -z "$pids" ]; then
        echo -e "${GREEN}✓ $service stopped${NC}"
        return 0
    fi

    # Attempt 3: SIGKILL (force)
    echo -e "${YELLOW}  Processes still running, forcing SIGKILL...${NC}"
    echo "$pids" | xargs kill -9 2>/dev/null || true
    sleep 1

    # Final verification
    pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [ -z "$pids" ]; then
        echo -e "${GREEN}✓ $service stopped (forced)${NC}"
        return 0
    else
        local remaining=$(echo "$pids" | wc -l | tr -d ' ')
        echo -e "${RED}✗ Failed to stop $service ($remaining process(es) still running)${NC}"
        echo -e "${RED}  PIDs: $pids${NC}"
        return 1
    fi
}

# Stop Frontend (Vite dev server on port 5173)
kill_by_port 5173 "Frontend (Vite)"

# Stop Backend API (FastAPI on port 8000)
kill_by_port 8000 "Backend API (FastAPI)"

# Stop Celery worker (match both "celery worker" and "celery -A" patterns)
kill_by_name "celery" "Celery Worker"

# Stop any remaining Python processes from run scripts
kill_by_name "run_celery_worker.sh" "Celery Worker Script"
kill_by_name "run_api.sh" "API Script"

# Optional: Stop PostgreSQL (uncomment if you want to stop the database too)
# echo -e "${YELLOW}Stopping PostgreSQL...${NC}"
# pg_ctl -D /usr/local/var/postgres stop
# echo -e "${GREEN}✓ PostgreSQL stopped${NC}"

# Optional: Stop Redis (uncomment if you want to stop Redis too)
# echo -e "${YELLOW}Stopping Redis...${NC}"
# redis-cli shutdown
# echo -e "${GREEN}✓ Redis stopped${NC}"

# Clean up running jobs in database
echo -e "${YELLOW}Cleaning up running jobs in database...${NC}"
psql -d fashion_hunting -c "UPDATE job_executions SET status = 'failed', completed_at = NOW(), error_message = 'Job interrupted by server shutdown' WHERE status = 'running' AND completed_at IS NULL;" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Running jobs marked as failed${NC}"
else
    echo -e "${RED}✗ Failed to update running jobs (database may not be running)${NC}"
fi

echo ""
echo -e "${GREEN}✅ All servers stopped successfully!${NC}"
echo ""
echo "To start the servers again, run:"
echo "  Backend API: ./backend/scripts/run_api.sh"
echo "  Celery Worker: ./backend/scripts/run_celery_worker.sh"
echo "  Frontend: cd frontend && npm run dev"
