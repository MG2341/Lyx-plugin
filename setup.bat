@echo off
REM LyX Autocomplete Plugin - Installation and Setup Script
REM This script sets up the environment and runs the service

setlocal enabledelayedexpansion

echo.
echo ========================================
echo LyX Autocomplete Plugin - Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo [OK] Python found
python --version

REM Create virtual environment if not exists
if not exist ".venv" (
    echo.
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Install dependencies
echo.
echo Installing dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed

REM Run tests
echo.
echo Running tests...
python test.py

REM Ask what to do next
echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Choose what to do next:
echo  1. Run interactive mode (test before full deployment)
echo  2. Start background service
echo  3. Exit
echo.

set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" (
    echo.
    echo Starting interactive mode...
    echo.
    python autocomplete_service.py --interactive
) else if "%choice%"=="2" (
    echo.
    echo Starting autocomplete service...
    echo Press Ctrl+C to stop the service
    echo.
    python autocomplete_service.py
) else (
    echo Exiting...
)

pause
