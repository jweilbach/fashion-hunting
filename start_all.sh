#!/bin/bash

# ABMC Phase 1 - Start All Servers Script
# This script starts the backend API, Celery worker, and frontend

set -e

echo "🚀 Starting ABMC Phase 1 servers..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# =============================================================================
# PRE-FLIGHT CHECKS - Detect and clean up leaked processes
# =============================================================================

echo -e "${BLUE}Running pre-flight checks...${NC}"

# Count existing Celery processes
celery_count=$(pgrep -f "celery" 2>/dev/null | wc -l | tr -d ' ')
if [ "$celery_count" -gt 4 ]; then
    echo -e "${RED}⚠ WARNING: Found $celery_count Celery processes (expected max 4)${NC}"
    echo -e "${YELLOW}This indicates a process leak. Running cleanup...${NC}"
    "$SCRIPT_DIR/stop_all.sh"
    sleep 2
    echo -e "${GREEN}✓ Cleanup complete${NC}"
fi

# Check for orphaned processes on ports
check_and_warn_port() {
    local port=$1
    local service=$2
    local pid=$(lsof -ti :$port 2>/dev/null || true)

    if [ -n "$pid" ]; then
        echo -e "${YELLOW}⚠ Found existing process on port $port ($service)${NC}"
        return 0
    fi
    return 1
}

# If any service is already running, offer to restart cleanly
existing_services=0
check_and_warn_port 8000 "Backend API" && existing_services=$((existing_services + 1))
check_and_warn_port 5173 "Frontend" && existing_services=$((existing_services + 1))
if pgrep -f "celery.*worker" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Found existing Celery worker process${NC}"
    existing_services=$((existing_services + 1))
fi

if [ "$existing_services" -gt 0 ]; then
    echo -e "${YELLOW}Found $existing_services existing service(s). Stopping them first...${NC}"
    "$SCRIPT_DIR/stop_all.sh"
    sleep 2
    echo -e "${GREEN}✓ Existing services stopped${NC}"
fi

echo -e "${GREEN}✓ Pre-flight checks complete${NC}"
echo ""

# =============================================================================
# SERVICE STARTUP
# =============================================================================

# Check if services are already running
check_running() {
    local port=$1
    local service=$2

    if lsof -ti :$port > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠ $service is already running on port $port${NC}"
        return 0
    else
        return 1
    fi
}

# Start Backend API
echo -e "${BLUE}Starting Backend API (FastAPI)...${NC}"
if check_running 8000 "Backend API"; then
    echo -e "${YELLOW}Skipping Backend API startup${NC}"
else
    cd "$SCRIPT_DIR"
    ./backend/scripts/run_api.sh > /dev/null 2>&1 &
    sleep 3

    if lsof -ti :8000 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend API started on http://0.0.0.0:8000${NC}"
    else
        echo -e "${RED}✗ Failed to start Backend API${NC}"
        exit 1
    fi
fi

# Start Celery Worker
echo -e "${BLUE}Starting Celery Worker...${NC}"
if pgrep -f "celery.*worker" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Celery Worker is already running${NC}"
    echo -e "${YELLOW}Skipping Celery Worker startup${NC}"
else
    cd "$SCRIPT_DIR"
    ./backend/scripts/run_celery_worker.sh > /dev/null 2>&1 &
    sleep 3

    if pgrep -f "celery.*worker" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Celery Worker started${NC}"
    else
        echo -e "${RED}✗ Failed to start Celery Worker${NC}"
        exit 1
    fi
fi

# Start Frontend
echo -e "${BLUE}Starting Frontend (Vite)...${NC}"
if check_running 5173 "Frontend"; then
    echo -e "${YELLOW}Skipping Frontend startup${NC}"
else
    cd "$SCRIPT_DIR/frontend"
    source ~/.nvm/nvm.sh
    nvm use 20 > /dev/null 2>&1
    npm run dev > /dev/null 2>&1 &
    sleep 4

    if lsof -ti :5173 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Frontend started on http://localhost:5173${NC}"
    else
        echo -e "${RED}✗ Failed to start Frontend${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}✅ All servers started successfully!${NC}"
echo ""
echo -e "Services running:"
echo -e "  ${BLUE}Backend API:${NC} http://0.0.0.0:8000"
echo -e "  ${BLUE}Frontend:${NC} http://localhost:5173"
echo -e "  ${BLUE}Celery Worker:${NC} Running in background"
echo ""
echo -e "To stop all servers, run: ${YELLOW}./stop_all.sh${NC}"
echo ""
