"""系统设置 API — 从环境变量读取真实配置"""

import os
import sys
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

# 确保 jarvis 模块可被找到
SRC_DIR = Path(__file__).resolve().parent.parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from jarvis.knowledge.loader import load_all  # noqa: E402

router = APIRouter()


class LLMConfig(BaseModel):
    model: str = Field(description="LLM模型名称")
    api_key_set: bool = Field(description="API密钥是否已配置")
    base_url: str = Field(description="API基础地址")
    timeout: float = Field(description="请求超时秒数")

class KBConfig(BaseModel):
    cases: int
    methodologies: int
    sensitivities: int
    products: int
    total: int
    status: str

class SettingsResponse(BaseModel):
    llm: LLMConfig
    kb: KBConfig


_kb_cache = None
def _get_kb():
    global _kb_cache
    if _kb_cache is None:
        _kb_cache = load_all()
    return _kb_cache


@router.get("/", response_model=SettingsResponse)
async def get_settings():
    """获取系统设置（从环境变量读取）"""
    api_key = os.getenv("LLM_API_KEY", "")
    kb = _get_kb()
    return SettingsResponse(
        llm=LLMConfig(
            model=os.getenv("LLM_MODEL", "deepseek-chat"),
            api_key_set=bool(api_key and api_key.strip()),
            base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1"),
            timeout=float(os.getenv("LLM_TIMEOUT", "15.0")),
        ),
        kb=KBConfig(
            cases=len(kb.cases),
            methodologies=len(kb.methodologies),
            sensitivities=len(kb.sensitivities),
            products=len(kb.products),
            total=len(kb.cases) + len(kb.methodologies) + len(kb.sensitivities) + len(kb.products),
            status="connected",
        ),
    )


@router.put("/llm")
async def update_llm_config(model: str = "deepseek-chat", base_url: str = "https://api.deepseek.com/v1"):
    """更新 LLM 配置（写入环境变量）"""
    os.environ["LLM_MODEL"] = model
    os.environ["LLM_BASE_URL"] = base_url
    return {"message": "LLM配置已更新", "model": model, "base_url": base_url}


@router.post("/kb/reload")
async def reload_knowledge_base():
    """重新加载知识库"""
    global _kb_cache
    _kb_cache = load_all()
    return {
        "message": "知识库已重新加载",
        "cases": len(_kb_cache.cases),
        "methodologies": len(_kb_cache.methodologies),
        "sensitivities": len(_kb_cache.sensitivities),
        "products": len(_kb_cache.products),
        "total": len(_kb_cache.cases) + len(_kb_cache.methodologies) + len(_kb_cache.sensitivities) + len(_kb_cache.products),
    }
