@echo off
title Jiro AI - Setup & Launcher
color 0B
echo.
echo  ========================================
echo        JIRO AI - Setup ^& Launcher
echo  ========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo [1/6] Checking Python version...
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo        Python %PYVER% found.

:: Check if venv exists
if not exist "venv" (
    echo [2/6] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [2/6] Virtual environment already exists.
)

:: Activate venv
echo [3/6] Activating virtual environment...
call venv\Scripts\activate.bat

:: Install dependencies
echo [4/6] Installing dependencies...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if errorlevel 1 (
    echo [WARNING] Some dependencies failed to install.
    echo          Audio features may require additional system packages.
    echo          Install PortAudio: https://www.portaudio.com/
)

:: Install ffmpeg if not present
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [INFO] ffmpeg not found. TTS audio playback may be limited.
    echo        Install ffmpeg: https://ffmpeg.org/download.html
    echo        Or: winget install ffmpeg
)

:: Create data directories
echo [5/6] Setting up data directories...
if not exist "data\memory" mkdir data\memory
if not exist "data\recordings\screenshots" mkdir data\recordings\screenshots
if not exist "data\models" mkdir data\models

:: Setup autostart
echo [6/6] Setting up autostart...
set SCRIPT_PATH=%~dp0
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

:: Create autostart VBS script (runs hidden in background)
echo Set WshShell = CreateObject("WScript.Shell") > "%STARTUP_DIR%\JiroAI.vbs"
echo WshShell.Run chr(34) ^& "%SCRIPT_PATH%start_jiro.bat" ^& chr(34), 0 >> "%STARTUP_DIR%\JiroAI.vbs"
echo Set WshShell = Nothing >> "%STARTUP_DIR%\JiroAI.vbs"

:: Create the actual start script
echo @echo off > start_jiro.bat
echo cd /d "%SCRIPT_PATH%" >> start_jiro.bat
echo call venv\Scripts\activate.bat >> start_jiro.bat
echo python main.py >> start_jiro.bat

echo.
echo  ========================================
echo       SETUP COMPLETE!
echo  ========================================
echo.
echo  Jiro AI has been set up successfully!
echo.
echo  - Auto-start: ENABLED (runs on Windows login)
echo  - To start now: run 'start_jiro.bat'
echo  - To disable auto-start: delete JiroAI.vbs from
echo    %STARTUP_DIR%
echo.
echo  Starting Jiro AI now...
echo.

:: Start Jiro AI
call venv\Scripts\activate.bat
python main.py

pause
