@echo off
chcp 65001 >nul 2>&1
title JARVIS AI - 启动服务

:: 检查 secrets.toml 是否存在
if not exist "%~dp0.streamlit\secrets.toml" (
    echo [!] 未找到 .streamlit\secrets.toml，请先配置 LLM API Key
    echo [!] 参考 .streamlit\secrets.toml.example 创建配置文件
    pause
    exit /b 1
)

:: 用 Python 生成 _env.bat（包含 set 命令），然后 call 它
E:\anaconda3\python.exe "%~dp0_make_env.py" "%~dp0"

:: 加载生成的环境变量
if exist "%~dp0_env.bat" call "%~dp0_env.bat"

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
