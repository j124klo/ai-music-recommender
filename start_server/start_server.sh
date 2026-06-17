#!/bin/bash
# Skrypt uruchamiający Frontend i Backend jednocześnie (macOS/Linux)

# Ta linijka sprawia, że wciśnięcie Ctrl+C zamyka jednocześnie oba serwery
trap "kill 0" EXIT

echo "Uruchamianie Backend'u (FastAPI)..."
cd backend
source .venv/bin/activate
uvicorn main:app --reload &
cd ..

echo "Uruchamianie Frontend'u (React/Vite)..."
cd frontend
npm run dev &
cd ..

echo "Aplikacja działa! Naciśnij Ctrl+C, aby wyłączyć serwery."
wait