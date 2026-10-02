#!/bin/bash
# Greppa Quick Start Script for Mac/Linux
# This script starts both backend and frontend in development mode

set -e

echo "========================================"
echo "   Starting Greppa Development Stack"
echo "========================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.10 or higher."
    exit 1
fi

# Check if Node is installed
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js not found. Please install Node.js 18 or higher."
    exit 1
fi

echo "[1/5] Checking backend virtual environment..."
if [ ! -d "backend/.venv" ]; then
    echo "Creating virtual environment..."
    cd backend
    python3 -m venv .venv
    source .venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
    cd ..
else
    echo "Virtual environment exists."
fi

echo ""
echo "[2/5] Checking frontend dependencies..."
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
else
    echo "Frontend dependencies installed."
fi

echo ""
echo "[3/5] Running database migrations..."
cd backend
source .venv/bin/activate
export PYTHONPATH=.
alembic upgrade head || echo "WARNING: Migration failed. Continuing anyway..."
cd ..

echo ""
echo "[4/5] Starting backend server..."
cd backend
source .venv/bin/activate
export PYTHONPATH=.
python app/main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 5

echo ""
echo "[5/5] Starting frontend server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================"
echo "   Greppa is running!"
echo "========================================"
echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Backend PID:  $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "To stop: kill $BACKEND_PID $FRONTEND_PID"
echo "Or press Ctrl+C"
echo ""
echo "TIP: Get a free Gemini API key at:"
echo "     https://aistudio.google.com/app/apikey"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
