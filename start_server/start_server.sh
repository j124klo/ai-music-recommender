#!/bin/bash
# Script to start Frontend and Backend simultaneously (macOS/Linux)

# This line ensures that pressing Ctrl+C closes both servers
trap "kill 0" EXIT

echo "Starting Backend (FastAPI)..."
cd backend
source .venv/bin/activate
uvicorn main:app --reload &
cd ..

echo "Starting Frontend (React/Vite)..."
cd frontend
npm run dev &
cd ..

echo "Application is running! Press Ctrl+C to shut down the servers."
wait