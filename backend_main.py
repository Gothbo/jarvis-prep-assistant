"""JARVIS AI 售前助手 - FastAPI 后端"""
import sys
from pathlib import Path

# Add src to Python path
SRC_DIR = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

from jarvis_app.routers import smartprep, training, knowledge, history, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    print("JARVIS Backend starting...")
    yield
    print("JARVIS Backend shutting down...")


app = FastAPI(
    title="JARVIS AI 售前助手",
    description="AI驱动的售前准备与模拟训练平台",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - 允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(smartprep.router, prefix="/api/smartprep", tags=["智能售前准备"])
app.include_router(training.router, prefix="/api/training", tags=["模拟训练"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["知识库"])
app.include_router(history.router, prefix="/api/history", tags=["历史记录"])
app.include_router(settings.router, prefix="/api/settings", tags=["系统设置"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "jarvis-ai-backend"}


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """提供前端页面"""
    frontend_path = Path(__file__).parent / "frontend" / "jarvis-ui-prototype.html"
    if frontend_path.exists():
        return HTMLResponse(content=frontend_path.read_text(encoding="utf-8"), status_code=200)
    return HTMLResponse(content="<h1>JARVIS AI Backend is running</h1><p>Frontend file not found.</p>", status_code=404)
