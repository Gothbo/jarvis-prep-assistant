@echo off
chcp 65001 >nul 2>&1
title JARVIS AI

set "PROJECT_DIR=%~dp0"

rem [1] Check .env file
if not exist "%PROJECT_DIR%.env" (
    echo [!] .env not found
    echo [!] Copy .env.example to .env and fill in your API Key
    pause
    exit /b 1
)

rem [2] Load .env via Python helper
E:\anaconda3\python.exe "%PROJECT_DIR%_load_env.py"
if exist "%TEMP%\jarvis_env.bat" (
    call "%TEMP%\jarvis_env.bat"
    del "%TEMP%\jarvis_env.bat" >nul 2>&1
) else (
    echo [!] Warning: env loading failed, using defaults
)

rem [3] Set defaults
if "%LLM_BASE_URL%"=="" set "LLM_BASE_URL=https://api.deepseek.com/v1"
if "%LLM_MODEL%"=="" set "LLM_MODEL=deepseek-chat"
if "%LLM_TIMEOUT%"=="" set "LLM_TIMEOUT=15.0"

echo ========================================
echo   JARVIS AI - Starting...
echo ========================================
echo.
echo   LLM_MODEL:    %LLM_MODEL%
echo   LLM_BASE_URL: %LLM_BASE_URL%
echo.

rem [4] Kill old processes
echo [*] Cleaning old processes...
taskkill /F /FI "WINDOWTITLE eq JARVIS Backend*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq JARVIS Frontend*" >nul 2>&1
timeout /t 1 /nobreak >nul

rem [5] Write launcher scripts to TEMP to avoid nested-quote issues

rem --- Backend launcher ---
(
    echo @echo off
    echo chcp 65001 ^>nul 2^>^&1
    echo title JARVIS Backend
    echo cd /d "%PROJECT_DIR%"
    echo E:\anaconda3\python.exe -m uvicorn backend_main:app --host 0.0.0.0 --port 8000
    echo pause
) > "%TEMP%\jarvis_backend.bat"

rem --- Frontend launcher ---
(
    echo @echo off
    echo chcp 65001 ^>nul 2^>^&1
    echo title JARVIS Frontend
    echo cd /d "%PROJECT_DIR%"
    echo E:\anaconda3\python.exe -m streamlit run app/Home.py --server.port 8501
    echo pause
) > "%TEMP%\jarvis_frontend.bat"

rem [6] Start services
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
