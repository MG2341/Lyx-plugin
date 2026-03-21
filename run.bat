@echo off
REM LyX Autocomplete Plugin - Simple Launcher
REM Run this to start the autocomplete service

cd /d "%~dp0"

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first to initialize the environment
    pause
    exit /b 1
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Start the service
echo LyX Autocomplete Service Starting...
echo Press Ctrl+C to stop
echo.

if "%1"=="--interactive" (
    python autocomplete_service.py --interactive
) else (
    python autocomplete_service.py
)

pause
