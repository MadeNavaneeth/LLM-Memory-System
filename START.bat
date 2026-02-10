@echo off
title LLM Memory System - Startup
color 0A

echo ========================================
echo    LLM Memory System - Quick Start
echo ========================================
echo.

:: Check if MongoDB is running
echo Checking MongoDB...
sc query MongoDB | find "RUNNING" >nul
if %ERRORLEVEL% == 0 (
    echo [OK] MongoDB is running
) else (
    echo [!] Starting MongoDB...
    net start MongoDB >nul 2>&1
    timeout /t 2 >nul
)

:: Activate venv and start server
echo.
echo Starting FastAPI server...
echo.
echo ========================================
echo    Server will be at: http://127.0.0.1:8000
echo    Press Ctrl+C to stop
echo ========================================
echo.

call venv\Scripts\activate.bat
python -m uvicorn app.main:app --reload

pause
