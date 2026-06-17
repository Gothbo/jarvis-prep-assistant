@echo off
chcp 65001 >nul 2>&1
title JARVIS AI - 启动服务

:: 检查 .env 是否存在
if not exist "%~dp0.env" (
    echo [!] 未找到 .env 文件，请先配置 API Key
    echo [!] 复制 .env.example 为 .env 并填入你的 LLM API Key
    pause
    exit /b 1
)

:: 用 Python 加载 .env 并生成临时环境设置
setlocal enabledelayedexpansion
E:\anaconda3\python.exe -c "import os,sys; sys.path.insert(0,r'%~dp0src'); from jarvis.config import load_config; load_config(); f=open(r'%~dp0_env_tmp.bat','w',encoding='utf-8'); [f.write(f'set {k}={v}\n') for k,v in os.environ.items() if k.startswith(('LLM_','THREAT_','JARVIS_'))]; f.close()"
if exist "%~dp0_env_tmp.bat" call "%~dp0_env_tmp.bat"
del "%~dp0_env_tmp.bat" >nul 2>&1

:: 默认值
if "%LLM_BASE_URL%"=="" set LLM_BASE_URL=https://api.deepseek.com/v1
if "%LLM_MODEL%"=="" set LLM_MODEL=deepseek-chat
if "%LLM_TIMEOUT%"=="" set LLM_TIMEOUT=15.0

echo ========================================
echo   JARVIS AI 售前助手 - 启动中...
echo ========================================
echo.
echo   DeepSeek 已配置
echo   LLM_MODEL: %LLM_MODEL%
echo   LLM_BASE_URL: %LLM_BASE_URL%
echo.

:: 先杀掉可能残留的旧进程
echo [*] 清理可能残留的旧进程...
powershell -Command "Get-NetTCPConnection -LocalPort 8000,8501 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq JARVIS Backend" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq JARVIS Frontend" >nul 2>&1
timeout /t 2 /nobreak >nul

:: 启动后端 (FastAPI on port 8000)
echo [1/2] 启动后端 FastAPI...
start "JARVIS Backend" cmd /c "cd /d %~dp0 && E:\anaconda3\python.exe -m uvicorn backend_main:app --host 0.0.0.0 --port 8000"

:: 等待后端就绪
echo [1/2] 等待后端启动...
timeout /t 3 /nobreak >nul

:: 启动前端 (Streamlit on port 8501)
echo [2/2] 启动前端 Streamlit...
start "JARVIS Frontend" cmd /c "cd /d %~dp0 && E:\anaconda3\python.exe -m streamlit run app/Home.py --server.port 8501"

echo.
echo ========================================
echo   服务已启动!
echo   后端 API:  http://localhost:8000
echo   前端 UI:   http://localhost:8501
echo   API 文档:  http://localhost:8000/docs
echo   HTML 前端: http://localhost:8000/
echo ========================================
echo.
echo 按任意键关闭此窗口 (服务会继续运行)
pause >nul
