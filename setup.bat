@echo off
title JIRO AI - Complete Setup
color 0B
echo.
echo  ================================================
echo         JIRO AI - ONE CLICK COMPLETE SETUP
echo  ================================================
echo.

:: ---- Step 1: Check Python ----
echo [1/10] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install Python 3.10+ from:
    echo         https://python.org/downloads
    echo         IMPORTANT: Check "Add Python to PATH" during install!
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo        Python %PYVER% found.

:: ---- Step 2: Create virtual environment ----
echo [2/10] Setting up virtual environment...
if not exist "venv" (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv. Try: python -m pip install virtualenv
        pause
        exit /b 1
    )
    echo        Virtual environment created.
) else (
    echo        Virtual environment exists.
)

:: ---- Step 3: Activate venv ----
echo [3/10] Activating virtual environment...
call venv\Scripts\activate.bat

:: ---- Step 4: Upgrade pip ----
echo [4/10] Upgrading pip...
python -m pip install --upgrade pip --quiet 2>nul

:: ---- Step 5: Install dependencies ----
echo [5/10] Installing dependencies (this may take a few minutes)...
pip install -r requirements.txt 2>nul
if errorlevel 1 (
    echo [WARNING] Some packages failed. Trying individually...
    pip install httpx numpy edge-tts psutil schedule 2>nul
    pip install customtkinter Pillow 2>nul
    pip install sounddevice SpeechRecognition 2>nul
    pip install mss PyMuPDF 2>nul
    pip install groq 2>nul
)
echo        Dependencies installed.

:: ---- Step 6: Check ffmpeg ----
echo [6/10] Checking ffmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo        ffmpeg not found. Installing via winget...
    winget install ffmpeg --accept-package-agreements --accept-source-agreements >nul 2>&1
    if errorlevel 1 (
        echo        [INFO] Could not auto-install ffmpeg.
        echo        Download manually: https://ffmpeg.org/download.html
        echo        Or run: winget install ffmpeg
    ) else (
        echo        ffmpeg installed!
    )
) else (
    echo        ffmpeg found.
)

:: ---- Step 7: Create directories ----
echo [7/10] Creating data directories...
if not exist "data\memory" mkdir data\memory
if not exist "data\recordings\screenshots" mkdir data\recordings\screenshots
if not exist "data\models" mkdir data\models
if not exist "data\logs" mkdir data\logs
echo        Directories ready.

:: ---- Step 8: Run first-time setup ----
echo [8/10] Running first-time setup...
echo.
python main.py --setup
echo.

:: ---- Step 9: Setup auto-start ----
echo [9/10] Setting up auto-start...
set "SCRIPT_PATH=%~dp0"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

:: Create start script
(
    echo @echo off
    echo cd /d "%SCRIPT_PATH%"
    echo call venv\Scripts\activate.bat
    echo python main.py
) > start_jiro.bat

:: Create silent VBS launcher for auto-start
(
    echo Set WshShell = CreateObject^("WScript.Shell"^)
    echo WshShell.Run chr^(34^) ^& "%SCRIPT_PATH%start_jiro.bat" ^& chr^(34^), 0
    echo Set WshShell = Nothing
) > "%STARTUP%\JiroAI.vbs"

echo        Auto-start configured!
echo        Jiro will run on Windows login.

:: ---- Step 10: Run health check ----
echo [10/10] Running health check...
python main.py --health

echo.
echo  ================================================
echo        SETUP COMPLETE!
echo  ================================================
echo.
echo  To start Jiro AI:
echo    - Double-click start_jiro.bat
echo    - Or run: python main.py
echo    - Or say "Hey Jiro" (it auto-starts on login!)
echo.
echo  Modes:
echo    python main.py             Full GUI mode
echo    python main.py --cli       Text-only mode
echo    python main.py --health    Health check
echo    python main.py --dashboard Activity stats
echo.
echo  To disable auto-start:
echo    Delete: %STARTUP%\JiroAI.vbs
echo.
echo  Starting Jiro AI now...
echo.

python main.py

pause
