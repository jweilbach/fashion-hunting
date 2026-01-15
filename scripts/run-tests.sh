#!/bin/bash
#
# Unified Test Runner Script
# Runs both frontend and backend tests with optional coverage
#
# Usage:
#   ./scripts/run-tests.sh          # Run all tests
#   ./scripts/run-tests.sh backend  # Run backend tests only
#   ./scripts/run-tests.sh frontend # Run frontend tests only
#   ./scripts/run-tests.sh --coverage # Run with coverage reports
#

# Don't exit immediately on error - we want to show helpful messages
set +e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Parse arguments
RUN_BACKEND=true
RUN_FRONTEND=true
COVERAGE=false
VERBOSE=false

for arg in "$@"; do
    case $arg in
        backend)
            RUN_FRONTEND=false
            ;;
        frontend)
            RUN_BACKEND=false
            ;;
        --coverage|-c)
            COVERAGE=true
            ;;
        --verbose|-v)
            VERBOSE=true
            ;;
        --help|-h)
            echo "Usage: $0 [backend|frontend] [--coverage] [--verbose]"
            echo ""
            echo "Options:"
            echo "  backend     Run backend tests only"
            echo "  frontend    Run frontend tests only"
            echo "  --coverage  Generate coverage reports"
            echo "  --verbose   Verbose output"
            echo ""
            echo "Requirements:"
            echo "  Backend:  Python 3.11+ with virtual environment at .venv/"
            echo "  Frontend: Node.js 18+ (use 'nvm use 20' if available)"
            exit 0
            ;;
    esac
done

# Helper function to print error with fix suggestion
print_error() {
    local title="$1"
    local message="$2"
    local fix="$3"

    echo ""
    echo -e "${RED}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ERROR: $title${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Problem:${NC}"
    echo "  $message"
    echo ""
    echo -e "${CYAN}How to fix:${NC}"
    echo "$fix"
    echo ""
}

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║               ABMC Test Runner                           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

BACKEND_EXIT=0
FRONTEND_EXIT=0
BACKEND_PASSED=0
BACKEND_SKIPPED=0
BACKEND_FAILED=0
FRONTEND_PASSED=0
FRONTEND_SKIPPED=0
FRONTEND_FAILED=0

# ========================================
# Backend Tests
# ========================================
if [ "$RUN_BACKEND" = true ]; then
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Running Backend Tests (pytest)${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Check if backend directory exists
    if [ ! -d "$PROJECT_ROOT/backend" ]; then
        print_error "Backend directory not found" \
            "The backend/ directory does not exist at $PROJECT_ROOT/backend" \
            "  Ensure you're running this script from the project root directory."
        BACKEND_EXIT=1
    else
        cd "$PROJECT_ROOT/backend"

        # Check for virtual environment
        if [ ! -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
            print_error "Virtual environment not found" \
                "No Python virtual environment found at $PROJECT_ROOT/.venv/" \
                "  Create a virtual environment:
    cd $PROJECT_ROOT
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt"
            BACKEND_EXIT=1
        else
            # Activate virtual environment
            source "$PROJECT_ROOT/.venv/bin/activate"

            # Check if pytest is installed
            if ! python -c "import pytest" 2>/dev/null; then
                print_error "pytest not installed" \
                    "pytest is not installed in the virtual environment" \
                    "  Install test dependencies:
    source $PROJECT_ROOT/.venv/bin/activate
    pip install pytest pytest-asyncio pytest-cov"
                BACKEND_EXIT=1
            else
                # Check if tests directory exists
                if [ ! -d "tests" ]; then
                    print_error "Tests directory not found" \
                        "No tests/ directory found in backend/" \
                        "  The test directory structure should be:
    backend/
    └── tests/
        ├── unit/
        └── integration/"
                    BACKEND_EXIT=1
                else
                    # Build pytest command
                    PYTEST_CMD="python -m pytest"

                    if [ "$COVERAGE" = true ]; then
                        # Check if pytest-cov is installed
                        if ! python -c "import pytest_cov" 2>/dev/null; then
                            echo -e "${YELLOW}Warning: pytest-cov not installed, running without coverage${NC}"
                            echo -e "${CYAN}To enable coverage: pip install pytest-cov${NC}"
                            echo ""
                        else
                            PYTEST_CMD="$PYTEST_CMD --cov=src --cov=api --cov-report=term-missing --cov-report=html:coverage_html"
                        fi
                    fi

                    if [ "$VERBOSE" = true ]; then
                        PYTEST_CMD="$PYTEST_CMD -v"
                    fi

                    # Run pytest and capture output
                    echo -e "${BLUE}Command: $PYTEST_CMD${NC}"
                    echo ""

                    BACKEND_OUTPUT=$($PYTEST_CMD 2>&1)
                    BACKEND_EXIT=$?
                    echo "$BACKEND_OUTPUT"

                    # Parse test counts from pytest output (e.g., "29 passed, 8 skipped")
                    BACKEND_PASSED=$(echo "$BACKEND_OUTPUT" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' || echo "0")
                    BACKEND_SKIPPED=$(echo "$BACKEND_OUTPUT" | grep -oE '[0-9]+ skipped' | grep -oE '[0-9]+' || echo "0")
                    BACKEND_FAILED=$(echo "$BACKEND_OUTPUT" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+' || echo "0")

                    if [ $BACKEND_EXIT -eq 0 ]; then
                        echo ""
                        echo -e "${GREEN}✓ Backend tests passed${NC}"
                    else
                        echo ""
                        echo -e "${RED}✗ Backend tests failed${NC}"
                        echo ""
                        echo -e "${CYAN}Troubleshooting tips:${NC}"
                        echo "  • Check the test output above for specific failures"
                        echo "  • Run a specific test: python -m pytest tests/unit/services/test_analytics_service.py -v"
                        echo "  • Check if all dependencies are installed: pip install -r requirements.txt"
                        echo "  • Database tests require PostgreSQL - they will be skipped if unavailable"
                    fi
                fi
            fi
        fi

        cd "$PROJECT_ROOT"
    fi
    echo ""
fi

# ========================================
# Frontend Tests
# ========================================
if [ "$RUN_FRONTEND" = true ]; then
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Running Frontend Tests (vitest)${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Check if frontend directory exists
    if [ ! -d "$PROJECT_ROOT/frontend" ]; then
        print_error "Frontend directory not found" \
            "The frontend/ directory does not exist at $PROJECT_ROOT/frontend" \
            "  Ensure you're running this script from the project root directory."
        FRONTEND_EXIT=1
    else
        cd "$PROJECT_ROOT/frontend"

        # Check if Node.js is installed
        if ! command -v node &> /dev/null; then
            print_error "Node.js not found" \
                "Node.js is not installed or not in PATH" \
                "  Install Node.js:
    • macOS: brew install node
    • Or use nvm: nvm install 20 && nvm use 20
    • Download: https://nodejs.org/"
            FRONTEND_EXIT=1
        else
            # Check Node.js version
            NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
            if [ "$NODE_VERSION" -lt 18 ]; then
                print_error "Node.js version too old" \
                    "Node.js v$NODE_VERSION detected, but v18+ is required for Vitest" \
                    "  Upgrade Node.js:
    • If using nvm: nvm install 20 && nvm use 20
    • Or update your default: nvm alias default 20
    • Current version: $(node -v)
    • Required: v18.0.0 or higher"
                FRONTEND_EXIT=1
            else
                # Check if npm is available
                if ! command -v npm &> /dev/null; then
                    print_error "npm not found" \
                        "npm is not installed or not in PATH" \
                        "  npm should come with Node.js. Try reinstalling Node.js."
                    FRONTEND_EXIT=1
                else
                    # Check if package.json exists
                    if [ ! -f "package.json" ]; then
                        print_error "package.json not found" \
                            "No package.json found in frontend/" \
                            "  Ensure the frontend directory is properly set up."
                        FRONTEND_EXIT=1
                    else
                        # Check if node_modules exists
                        if [ ! -d "node_modules" ]; then
                            echo -e "${YELLOW}Installing frontend dependencies...${NC}"
                            echo -e "${CYAN}Running: npm install${NC}"
                            echo ""
                            npm install
                            if [ $? -ne 0 ]; then
                                print_error "npm install failed" \
                                    "Failed to install frontend dependencies" \
                                    "  Try:
    1. Delete node_modules and package-lock.json
    2. Run: npm install
    3. Check for npm errors above"
                                FRONTEND_EXIT=1
                            fi
                        fi

                        if [ $FRONTEND_EXIT -eq 0 ]; then
                            # Check if vitest is available
                            if ! npm list vitest &> /dev/null; then
                                print_error "vitest not installed" \
                                    "vitest is not in the project dependencies" \
                                    "  Install vitest:
    npm install -D vitest @vitest/ui @vitest/coverage-v8"
                                FRONTEND_EXIT=1
                            else
                                # Build vitest command
                                if [ "$COVERAGE" = true ]; then
                                    VITEST_CMD="npm run test:coverage"
                                else
                                    VITEST_CMD="npm run test:run"
                                fi

                                # Run vitest and capture output
                                echo -e "${BLUE}Command: $VITEST_CMD${NC}"
                                echo ""

                                FRONTEND_OUTPUT=$($VITEST_CMD 2>&1)
                                FRONTEND_EXIT=$?
                                echo "$FRONTEND_OUTPUT"

                                # Parse test counts from vitest output (e.g., "Tests  22 passed (22)")
                                FRONTEND_PASSED=$(echo "$FRONTEND_OUTPUT" | grep -oE 'Tests[[:space:]]+[0-9]+' | grep -oE '[0-9]+' || echo "0")
                                FRONTEND_SKIPPED=$(echo "$FRONTEND_OUTPUT" | grep -oE '[0-9]+ skipped' | grep -oE '[0-9]+' || echo "0")
                                FRONTEND_FAILED=$(echo "$FRONTEND_OUTPUT" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+' || echo "0")

                                if [ $FRONTEND_EXIT -eq 0 ]; then
                                    echo ""
                                    echo -e "${GREEN}✓ Frontend tests passed${NC}"
                                else
                                    echo ""
                                    echo -e "${RED}✗ Frontend tests failed${NC}"
                                    echo ""
                                    echo -e "${CYAN}Troubleshooting tips:${NC}"
                                    echo "  • Check the test output above for specific failures"
                                    echo "  • Run tests in watch mode for debugging: npm test"
                                    echo "  • Run a specific test file: npm test -- src/api/__tests__/lists.test.ts"
                                    echo "  • Check if all dependencies are installed: npm install"
                                fi
                            fi
                        fi
                    fi
                fi
            fi
        fi

        cd "$PROJECT_ROOT"
    fi
    echo ""
fi

# ========================================
# Summary
# ========================================
echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    Test Summary                          ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$RUN_BACKEND" = true ]; then
    if [ $BACKEND_EXIT -eq 0 ]; then
        BACKEND_STATUS="${GREEN}✓ PASSED${NC}"
    else
        BACKEND_STATUS="${RED}✗ FAILED${NC}"
    fi
    # Build counts string
    BACKEND_COUNTS=""
    [ -n "$BACKEND_PASSED" ] && [ "$BACKEND_PASSED" != "0" ] && BACKEND_COUNTS="${GREEN}$BACKEND_PASSED passed${NC}"
    [ -n "$BACKEND_SKIPPED" ] && [ "$BACKEND_SKIPPED" != "0" ] && BACKEND_COUNTS="$BACKEND_COUNTS, ${YELLOW}$BACKEND_SKIPPED skipped${NC}"
    [ -n "$BACKEND_FAILED" ] && [ "$BACKEND_FAILED" != "0" ] && BACKEND_COUNTS="$BACKEND_COUNTS, ${RED}$BACKEND_FAILED failed${NC}"
    # Remove leading comma if present
    BACKEND_COUNTS=$(echo "$BACKEND_COUNTS" | sed 's/^, //')

    echo -e "  Backend:  $BACKEND_STATUS"
    [ -n "$BACKEND_COUNTS" ] && echo -e "            ($BACKEND_COUNTS)"
fi

if [ "$RUN_FRONTEND" = true ]; then
    if [ $FRONTEND_EXIT -eq 0 ]; then
        FRONTEND_STATUS="${GREEN}✓ PASSED${NC}"
    else
        FRONTEND_STATUS="${RED}✗ FAILED${NC}"
    fi
    # Build counts string
    FRONTEND_COUNTS=""
    [ -n "$FRONTEND_PASSED" ] && [ "$FRONTEND_PASSED" != "0" ] && FRONTEND_COUNTS="${GREEN}$FRONTEND_PASSED passed${NC}"
    [ -n "$FRONTEND_SKIPPED" ] && [ "$FRONTEND_SKIPPED" != "0" ] && FRONTEND_COUNTS="$FRONTEND_COUNTS, ${YELLOW}$FRONTEND_SKIPPED skipped${NC}"
    [ -n "$FRONTEND_FAILED" ] && [ "$FRONTEND_FAILED" != "0" ] && FRONTEND_COUNTS="$FRONTEND_COUNTS, ${RED}$FRONTEND_FAILED failed${NC}"
    # Remove leading comma if present
    FRONTEND_COUNTS=$(echo "$FRONTEND_COUNTS" | sed 's/^, //')

    echo -e "  Frontend: $FRONTEND_STATUS"
    [ -n "$FRONTEND_COUNTS" ] && echo -e "            ($FRONTEND_COUNTS)"
fi

echo ""

# Exit with error if any tests failed
if [ $BACKEND_EXIT -ne 0 ] || [ $FRONTEND_EXIT -ne 0 ]; then
    echo -e "${RED}Some tests failed. See output above for details.${NC}"
    echo ""
    echo -e "${CYAN}Need help?${NC}"
    echo "  • Read manifests/TESTING.md for detailed documentation"
    echo "  • Run with --help for usage information"
    echo "  • Backend issues: Check .venv is activated and dependencies installed"
    echo "  • Frontend issues: Ensure Node.js 18+ (try: nvm use 20)"
    exit 1
else
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
