@echo off
title JIRO AI - Complete Setup (LOCAL-FIRST)
color 0B
echo.
echo  ================================================
echo         JIRO AI - ONE CLICK COMPLETE SETUP
echo         LOCAL-FIRST Architecture
echo  ================================================
echo.

:: ---- Step 1: Check Python ----
echo [1/11] Checking Python...
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

:: ---- Step 2: Check Git ----
echo [2/11] Checking Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Git not found. Auto-update won't work.
    echo          Install from: https://git-scm.com/downloads
) else (
    echo        Git found. Auto-update enabled.
)

:: ---- Step 3: Create virtual environment ----
echo [3/11] Setting up virtual environment...
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

:: ---- Step 4: Activate venv ----
echo [4/11] Activating virtual environment...
call venv\Scripts\activate.bat

:: ---- Step 5: Upgrade pip ----
echo [5/11] Upgrading pip...
python -m pip install --upgrade pip --quiet 2>nul

:: ---- Step 6: Install dependencies ----
echo [6/11] Installing dependencies (this may take a few minutes)...
pip install -r requirements.txt 2>nul
if errorlevel 1 (
    echo [WARNING] Some packages failed. Trying individually...
    pip install httpx numpy psutil schedule 2>nul
    pip install pyttsx3 edge-tts 2>nul
    pip install customtkinter Pillow 2>nul
    pip install SpeechRecognition sounddevice pygame 2>nul
    pip install mss PyMuPDF 2>nul
    pip install groq 2>nul
    pip install python-docx reportlab python-pptx 2>nul
)
echo        Dependencies installed.

:: ---- Step 7: Install PyAudio (special handling for Windows) ----
echo [7/11] Installing PyAudio...
pip install PyAudio 2>nul
if errorlevel 1 (
    echo        PyAudio pip install failed, trying pipwin...
    pip install pipwin 2>nul
    pipwin install pyaudio 2>nul
    if errorlevel 1 (
        echo        [INFO] PyAudio not installed. Voice will use SpeechRecognition fallback.
    )
)

:: ---- Step 8: Create directories ----
echo [8/11] Creating data directories...
if not exist "data\memory" mkdir data\memory
if not exist "data\recordings\screenshots" mkdir data\recordings\screenshots
if not exist "data\models" mkdir data\models
if not exist "data\logs" mkdir data\logs
if not exist "data\reports" mkdir data\reports
echo        Directories ready.

:: ---- Step 9: Run first-time setup ----
echo [9/11] Running first-time setup...
echo.
python main.py --setup
echo.

:: ---- Step 10: Setup auto-start with auto-update ----
echo [10/11] Setting up auto-start with auto-update...
set "SCRIPT_PATH=%~dp0"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

:: Create start script that auto-updates first
(
    echo @echo off
    echo cd /d "%SCRIPT_PATH%"
    echo call venv\Scripts\activate.bat
    echo echo Checking for Jiro AI updates...
    echo git pull origin main 2^>nul
    echo pip install -r requirements.txt -q 2^>nul
    echo echo Starting Jiro AI...
    echo start /min pythonw main.py
) > start_jiro.bat

:: Create silent VBS launcher for auto-start
(
    echo Set WshShell = CreateObject^("WScript.Shell"^)
    echo WshShell.Run chr^(34^) ^& "%SCRIPT_PATH%start_jiro.bat" ^& chr^(34^), 0
    echo Set WshShell = Nothing
) > "%STARTUP%\JiroAI.vbs"

echo        Auto-start configured with auto-update!
echo        Jiro will update and run on Windows login.

:: ---- Step 11: Run health check ----
echo [11/11] Running health check...
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
echo    python main.py --cli       Text-only mode (best for low-end PCs)
echo    python main.py --health    Health check
echo    python main.py --report    Self-assessment report
echo    python main.py --dashboard Activity stats
echo.
echo  New Commands:
echo    create doc/pdf/ppt         Create files
echo    create folder              Create folders
echo    run command ^<cmd^>          Execute system commands
echo    powershell ^<cmd^>           Run PowerShell commands
echo    show report                View self-report
echo    register autostart         Re-register auto-start
echo.
echo  Architecture: LOCAL-FIRST
echo    - Offline LLM processes first (no API call)
echo    - API keys only for generation/research
echo    - Auto-updates from GitHub on every startup
echo.
echo  To disable auto-start:
echo    Delete: %STARTUP%\JiroAI.vbs
echo.
echo  Starting Jiro AI now...
echo.

python main.py

pause
