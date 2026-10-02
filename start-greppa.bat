@echo off
REM Greppa Quick Start Script for Windows
REM This script starts both backend and frontend in development mode

echo ========================================
echo    Starting Greppa Development Stack
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.10 or higher.
    pause
    exit /b 1
)

REM Check if Node is installed
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js not found. Please install Node.js 18 or higher.
    pause
    exit /b 1
)

echo [1/5] Checking backend virtual environment...
if not exist "backend\.venv\" (
    echo Creating virtual environment...
    cd backend
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo Installing dependencies...
    pip install -r requirements.txt
    cd ..
) else (
    echo Virtual environment exists.
)

echo.
echo [2/5] Checking frontend dependencies...
if not exist "frontend\node_modules\" (
    echo Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
) else (
    echo Frontend dependencies installed.
)

echo.
echo [3/5] Running database migrations...
cd backend
call .venv\Scripts\activate.bat
set PYTHONPATH=.
alembic upgrade head
if %errorlevel% neq 0 (
    echo WARNING: Migration failed. Continuing anyway...
)
cd ..

echo.
echo [4/5] Starting backend server...
start "Greppa Backend" cmd /k "cd backend && .venv\Scripts\activate.bat && set PYTHONPATH=. && python app/main.py"

REM Wait for backend to start
timeout /t 5 /nobreak >nul

echo.
echo [5/5] Starting frontend server...
start "Greppa Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo    Greppa is starting!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C in each window to stop the servers.
echo.
echo TIP: Get a free Gemini API key at:
echo      https://aistudio.google.com/app/apikey
echo.

REM Wait a bit more and open browser
timeout /t 3 /nobreak >nul
start http://localhost:3000

pause
