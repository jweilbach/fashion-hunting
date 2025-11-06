#!/bin/bash
# Startup script for FastAPI server

cd "$(dirname "$0")"
source .venv/bin/activate

# Set PYTHONPATH to include the project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Run uvicorn
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
