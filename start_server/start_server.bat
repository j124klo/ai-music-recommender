@echo off
echo ==================================================
echo      AI Music Recommender - Application Start
echo ==================================================
echo.
echo [1/2] Starting Backend (FastAPI)...
start "AI Music Recommender - Backend" cmd /k "cd backend && .venv\Scripts\activate && uvicorn main:app --reload"

echo [2/2] Starting Frontend (React/Vite)...
start "AI Music Recommender - Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Done! Servers are starting in new windows.
echo To close the application, simply close these two new black windows.
pause