@echo off
echo ==================================================
echo      AI Music Recommender - Start aplikacji
echo ==================================================
echo.

echo [1/2] Uruchamianie Backend'u (FastAPI)...
start "AI Music Recommender - Backend" cmd /k "cd backend && .venv\Scripts\activate && uvicorn main:app --reload"

echo [2/2] Uruchamianie Frontend'u (React/Vite)...
start "AI Music Recommender - Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Gotowe! Serwery uruchamiaja sie w nowych oknach.
echo Aby wylaczyc aplikacje, po prostu zamknij te dwa nowe czarne okna.
pause