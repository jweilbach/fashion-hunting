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

# Function to kill process by port
kill_by_port() {
    local port=$1
    local service=$2

    echo -e "${YELLOW}Stopping $service on port $port...${NC}"

    # Find the process using the port
    local pid=$(lsof -ti :$port)

    if [ -z "$pid" ]; then
        echo -e "${GREEN}✓ $service is not running${NC}"
    else
        kill -15 $pid 2>/dev/null || kill -9 $pid 2>/dev/null
        sleep 1

        # Check if process is still running
        if lsof -ti :$port > /dev/null 2>&1; then
            echo -e "${RED}✗ Failed to stop $service${NC}"
        else
            echo -e "${GREEN}✓ $service stopped${NC}"
        fi
    fi
}

# Function to kill process by name pattern
kill_by_name() {
    local pattern=$1
    local service=$2

    echo -e "${YELLOW}Stopping $service...${NC}"

    # Find processes matching the pattern
    local pids=$(pgrep -f "$pattern" || true)

    if [ -z "$pids" ]; then
        echo -e "${GREEN}✓ $service is not running${NC}"
    else
        echo "$pids" | xargs kill -15 2>/dev/null || echo "$pids" | xargs kill -9 2>/dev/null
        sleep 1

        # Check if any processes are still running
        if pgrep -f "$pattern" > /dev/null 2>&1; then
            echo -e "${RED}✗ Failed to stop $service${NC}"
        else
            echo -e "${GREEN}✓ $service stopped${NC}"
        fi
    fi
}

# Stop Frontend (Vite dev server on port 5174)
kill_by_port 5174 "Frontend (Vite)"

# Stop Backend API (FastAPI on port 8000)
kill_by_port 8000 "Backend API (FastAPI)"

# Stop Celery worker
kill_by_name "celery.*worker" "Celery Worker"

# Stop Celery beat (if running)
kill_by_name "celery.*beat" "Celery Beat"

# Optional: Stop PostgreSQL (uncomment if you want to stop the database too)
# echo -e "${YELLOW}Stopping PostgreSQL...${NC}"
# pg_ctl -D /usr/local/var/postgres stop
# echo -e "${GREEN}✓ PostgreSQL stopped${NC}"

# Optional: Stop Redis (uncomment if you want to stop Redis too)
# echo -e "${YELLOW}Stopping Redis...${NC}"
# redis-cli shutdown
# echo -e "${GREEN}✓ Redis stopped${NC}"

echo ""
echo -e "${GREEN}✅ All servers stopped successfully!${NC}"
echo ""
echo "To start the servers again, run:"
echo "  Backend API: ./backend/scripts/run_api.sh"
echo "  Celery Worker: ./backend/scripts/run_celery_worker.sh"
echo "  Frontend: cd frontend && npm run dev"
