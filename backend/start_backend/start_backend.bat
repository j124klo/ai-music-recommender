@echo off
REM Przejście zawsze do folderu 'backend', niezależnie skąd uruchamiasz skrypt
cd /d "%~dp0\.."
call .venv\Scripts\activate.bat
uvicorn main:app --reload
pause