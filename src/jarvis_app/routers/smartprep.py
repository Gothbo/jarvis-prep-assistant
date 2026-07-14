"""智能售前准备 API — 接入双引擎核心，生成真实 Prep 包"""

import sys
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

# 确保 jarvis 模块可被找到
SRC_DIR = Path(__file__).resolve().parent.parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from jarvis.engine.hybrid_engine import generate_prep_hybrid  # noqa: E402
from jarvis.engine.intent import recognize  # noqa: E402
from jarvis.knowledge.loader import load_all  # noqa: E402

router = APIRouter()


class SmartPrepRequest(BaseModel):
    scenario: str = Field(..., min_length=10, description="客户场景描述")
    industry: str | None = Field(default=None, description="行业（可选）")


class SmartPrepResponse(BaseModel):
    industry: str
    scenario: str
    summary: str
    key_points: list[str]
    products: list[str]
    next_steps: str
    # 双引擎扩展字段
    engine_mode: str = Field(default="hybrid", description="生成模式: hybrid | rule_only")
    sensitivity_alerts: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    solution_direction: str = ""
    talking_points: str = ""
    solution_outline: list[str] = Field(default_factory=list)


@router.post("/generate", response_model=SmartPrepResponse)
async def generate_prep(request: SmartPrepRequest):
    """根据客户场景生成售前准备方案（双引擎并行生成）"""
    # 意图识别
    intent = recognize(request.scenario)
    if request.industry:
        intent = intent.__class__(
            industry=request.industry,
            scenario=intent.scenario,
            raw_input=request.scenario,
        )

    # 加载知识库
    kb = load_all()

    # 双引擎并行生成（在线程中运行，避免与 FastAPI 事件循环冲突）
    import asyncio
    pkg, mode = await asyncio.to_thread(
        generate_prep_hybrid, intent, kb, 30.0
    )

    # 保存到历史记录
    try:
        from jarvis_app.routers.history import save_prep_record
        await save_prep_record(
            industry=intent.industry or "unknown",
            scenario=request.scenario,
            engine_mode=mode,
            summary=pkg.scenario_assessment[:500],
        )
    except Exception:
        pass  # 历史记录保存失败不影响主流程

    # 从 solution_direction 中提取产品名（简单启发式）
    products = []
    for line in (pkg.solution_direction or "").split("\n"):
        line = line.strip()
        if line.startswith("Product:") or line.startswith("产品:"):
            products.append(line.split(":", 1)[-1].strip())

    return SmartPrepResponse(
        industry=intent.industry or "unknown",
        scenario=request.scenario[:100],
        summary=pkg.scenario_assessment,
        key_points=pkg.sensitivity_alerts[:5],
        products=products or ["(见方案方向)"],
        next_steps=pkg.talking_points[:500] if pkg.talking_points else "",
        engine_mode=mode,
        sensitivity_alerts=pkg.sensitivity_alerts,
        follow_up_questions=pkg.follow_up_questions,
        solution_direction=pkg.solution_direction,
        talking_points=pkg.talking_points,
        solution_outline=pkg.solution_outline,
    )
