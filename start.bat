@echo off
chcp 65001 >nul 2>&1
title JARVIS AI

set "PROJECT_DIR=%~dp0"

rem ============================================================
rem  [1] Auto-detect Python
rem ============================================================
set "PYTHON="

where py >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON=py"
    goto :python_found
)
where python >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON=python"
    goto :python_found
)
where python3 >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON=python3"
    goto :python_found
)

echo [ERROR] Python not found.
echo         Please install Python 3.10+ from https://python.org
echo         Make sure "Add Python to PATH" is checked during install.
pause
exit /b 1

:python_found
for /f "tokens=*" %%v in ('%PYTHON% --version 2^>^&1') do set "PY_VERSION=%%v"
echo [*] Detected: %PY_VERSION% (%PYTHON%)

rem ============================================================
rem  [2] Setup virtual environment
rem ============================================================
if not exist "%PROJECT_DIR%.venv\Scripts\activate.bat" (
    echo [*] Creating virtual environment...
    %PYTHON% -m venv "%PROJECT_DIR%.venv"
    if errorlevel 1 (
        echo [ERROR] Failed to create venv. Is the "venv" module installed?
        pause
        exit /b 1
    )
)

call "%PROJECT_DIR%.venv\Scripts\activate.bat"
echo [*] Virtual environment activated.

rem ============================================================
rem  [3] Install dependencies (skip if already done)
rem ============================================================
if not exist "%PROJECT_DIR%.venv\.deps_installed" (
    echo [*] Installing dependencies (first run, may take a minute^)...
    %PYTHON% -m pip install --upgrade pip -q
    %PYTHON% -m pip install -r "%PROJECT_DIR%requirements.txt" -q
    if errorlevel 1 (
        echo [ERROR] pip install failed. Check your network or requirements.txt.
        pause
        exit /b 1
    )
    echo. > "%PROJECT_DIR%.venv\.deps_installed"
    echo [*] Dependencies installed.
) else (
    echo [*] Dependencies already installed.
)

rem ============================================================
rem  [4] Check .env file
rem ============================================================
if not exist "%PROJECT_DIR%.env" (
    if exist "%PROJECT_DIR%.env.example" (
        echo [!] .env not found, copying from .env.example ...
        copy "%PROJECT_DIR%.env.example" "%PROJECT_DIR%.env" >nul
        echo [!] >>> Please edit .env and fill in your API Key before using LLM features.
    ) else (
        echo [!] .env not found and no .env.example available.
    )
)

rem [4b] Load .env via Python helper
if exist "%PROJECT_DIR%_load_env.py" (
    %PYTHON% "%PROJECT_DIR%_load_env.py"
    if exist "%TEMP%\jarvis_env.bat" (
        call "%TEMP%\jarvis_env.bat"
        del "%TEMP%\jarvis_env.bat" >nul 2>&1
    )
)

rem ============================================================
rem  [5] Set defaults for missing env vars
rem ============================================================
if "%LLM_BASE_URL%"=="" set "LLM_BASE_URL=https://api.deepseek.com/v1"
if "%LLM_MODEL%"=="" set "LLM_MODEL=deepseek-chat"
if "%LLM_TIMEOUT%"=="" set "LLM_TIMEOUT=30.0"

echo.
echo ========================================
echo   JARVIS AI - Starting...
echo ========================================
echo.
echo   Python:       %PY_VERSION%
echo   LLM_MODEL:    %LLM_MODEL%
echo   LLM_BASE_URL: %LLM_BASE_URL%
echo.

rem ============================================================
rem  [6] Kill old processes
rem ============================================================
echo [*] Cleaning old processes...
taskkill /F /FI "WINDOWTITLE eq JARVIS Backend*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq JARVIS Frontend*" >nul 2>&1
timeout /t 1 /nobreak >nul

rem ============================================================
rem  [7] Write launcher scripts to TEMP
rem ============================================================
set "VENV_PYTHON=%PROJECT_DIR%.venv\Scripts\python.exe"

rem --- Backend launcher ---
(
    echo @echo off
    echo chcp 65001 ^>nul 2^>^&1
    echo title JARVIS Backend
    echo cd /d "%PROJECT_DIR%"
    echo call "%PROJECT_DIR%.venv\Scripts\activate.bat"
    echo %PYTHON% -m uvicorn backend_main:app --host 0.0.0.0 --port 8000
    echo pause
) > "%TEMP%\jarvis_backend.bat"

rem --- Frontend launcher ---
(
    echo @echo off
    echo chcp 65001 ^>nul 2^>^&1
    echo title JARVIS Frontend
    echo cd /d "%PROJECT_DIR%"
    echo call "%PROJECT_DIR%.venv\Scripts\activate.bat"
    echo %PYTHON% -m streamlit run app/Home.py --server.port 8501
    echo pause
) > "%TEMP%\jarvis_frontend.bat"

rem ============================================================
rem  [8] Start services
rem ============================================================
echo [1/2] Starting Backend FastAPI (port 8000)...
start "JARVIS Backend" cmd /c "%TEMP%\jarvis_backend.bat"

echo [*] Waiting for backend...
timeout /t 4 /nobreak >nul

echo [2/2] Starting Frontend Streamlit (port 8501)...
start "JARVIS Frontend" cmd /c "%TEMP%\jarvis_frontend.bat"

echo.
echo ========================================
echo   Services started!
echo   Backend API:  http://localhost:8000
echo   Frontend UI:  http://localhost:8501
echo   API Docs:     http://localhost:8000/docs
echo ========================================
echo.
echo Press any key to close this window
pause >nul
