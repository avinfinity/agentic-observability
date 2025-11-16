@echo off
REM Simple run script for Windows

echo ========================================
echo Agentic Observability Backend
echo ========================================
echo.

REM Check if .env file exists
if not exist .env (
    echo [ERROR] .env file not found
    echo.
    echo Please create a .env file with your configuration.
    echo Example:
    echo   GOOGLE_API_KEY="your-api-key-here"
    echo   GEMINI_MODEL_ID="gemini-2.0-flash-exp"
    echo   TEMPERATURE=0.7
    echo   MAX_TOKENS=8192
    echo.
    exit /b 1
)

echo [OK] .env file found
echo.

REM Check if we should run verification
if "%1"=="--verify" (
    echo Running setup verification...
    python verify_setup.py
    if errorlevel 1 (
        echo [ERROR] Setup verification failed
        exit /b 1
    )
    echo.
)

REM Determine if we're using poetry or pip
where poetry >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] Using Poetry
    echo Starting server with Poetry...
    poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
) else if exist venv (
    echo [OK] Using virtual environment
    echo Activating venv and starting server...
    call venv\Scripts\activate.bat
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
) else (
    echo [WARNING] No Poetry or venv found, running directly...
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
)

