#!/bin/bash
echo "Starting ListifyAI Backend..."
cd backend
export PYTHONPATH=..:$PYTHONPATH
source venv/bin/activate
echo "Running migrations..."
alembic -c alembic.ini upgrade head
echo "Starting server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
