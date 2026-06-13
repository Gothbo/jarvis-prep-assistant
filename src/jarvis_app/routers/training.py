"""模拟训练 API — 接入真实训练引擎，支持 DeepSeek LLM 智能回复和打分"""

import os
import sys
import uuid
from pathlib import Path
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# 确保 jarvis 模块可被找到
SRC_DIR = Path(__file__).resolve().parent.parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from jarvis.engine.training import (
    TrainingConfig as EngineConfig,
    ChatMessage,
    TrainingResult,
    PERSONALITY_MAP,
    PERSONALITY_REVERSE,
    INDUSTRY_LABELS,
    generate_customer_reply,
    generate_first_message,
    score_conversation,
)
from jarvis.knowledge.loader import load_all, KnowledgeBase

router = APIRouter()

# ── 行业映射 ──
INDUSTRY_OPTIONS = {
    "金融": "finance",
    "医疗": "healthcare",
    "制造业": "manufacturing",
    "政务": "government",
    "教育": "education",
    "零售": "retail",
}

INDUSTRY_CN = {v: k for k, v in INDUSTRY_OPTIONS.items()}

# ── 场景映射 ──
SCENARIO_OPTIONS = {
    "合规审计": "compliance",
    "数据泄露": "data_leak",
    "勒索软件": "ransomware",
    "APT攻击": "apt",
    "钓鱼攻击": "phishing",
}

SCENARIO_CN = {v: k for k, v in SCENARIO_OPTIONS.items()}

# ── 行业场景映射 ──
INDUSTRY_SCENARIOS = {
    "金融": ["合规审计", "数据泄露", "勒索软件", "APT攻击"],
    "医疗": ["数据泄露", "勒索软件", "合规审计"],
    "制造业": ["勒索软件", "APT攻击", "合规审计"],
    "政务": ["合规审计", "数据安全治理"],
    "教育": ["数据泄露", "合规审计"],
    "零售": ["数据泄露", "勒索软件", "合规审计"],
}

# ── 性格映射 ──
PERSONALITY_OPTIONS = PERSONALITY_MAP

# ── 缓存 ──
_kb_cache: Optional[KnowledgeBase] = None

def _get_kb() -> KnowledgeBase:
    global _kb_cache
    if _kb_cache is None:
        _kb_cache = load_all()
    return _kb_cache

# ── 会话存储 ──
sessions: dict = {}


# ── 请求/响应模型 ──

class StartRequest(BaseModel):
    industry: str = Field(..., description="行业（中文或英文）")
    scenario: str = Field(..., description="场景（中文或英文）")
    personality: str = Field(..., description="客户性格（中文或英文）")

class StartResponse(BaseModel):
    session_id: str
    first_message: str
    industry_cn: str
    scenario_cn: str
    personality_cn: str
    config: dict

class SendRequest(BaseModel):
    session_id: str
    message: str

class SendResponse(BaseModel):
    reply: str
    session_id: str

class ScoreDimension(BaseModel):
    key: str
    label: str
    score: int
    color: str
    comment: str = ""

class EndResponse(BaseModel):
    scores: List[ScoreDimension]
    avg_score: int
    summary: str
    takeaway: str
    session_id: str


# ── 辅助函数 ──

def _normalize_industry(val: str) -> str:
    if val in INDUSTRY_OPTIONS:
        return INDUSTRY_OPTIONS[val]
    return val

def _normalize_scenario(val: str) -> str:
    if val in SCENARIO_OPTIONS:
        return SCENARIO_OPTIONS[val]
    return val

def _normalize_personality(val: str) -> str:
    if val in PERSONALITY_REVERSE:
        return PERSONALITY_REVERSE[val]
    return val


# ── 路由 ──

@router.get("/scenarios")
async def get_scenarios(industry: str = Query(default="金融", description="行业名称（中文）")):
    """获取指定行业的可选场景列表"""
    scenarios = INDUSTRY_SCENARIOS.get(industry, ["合规审计", "数据泄露", "勒索软件"])
    return {"industry": industry, "scenarios": scenarios}


@router.post("/start", response_model=StartResponse)
async def start_training(req: StartRequest):
    """开始新的模拟训练会话"""
    industry = _normalize_industry(req.industry)
    scenario = _normalize_scenario(req.scenario)
    personality = _normalize_personality(req.personality)

    kb = _get_kb()
    config = EngineConfig(industry=industry, scenario=scenario, personality=personality)

    first_msg = generate_first_message(config, kb)

    session_id = str(uuid.uuid4())[:8]
    sessions[session_id] = {
        "config": config,
        "messages": [ChatMessage(role="customer", content=first_msg)],
    }

    industry_cn = INDUSTRY_CN.get(industry, industry)
    scenario_cn = SCENARIO_CN.get(scenario, scenario)
    personality_cn = PERSONALITY_MAP.get(personality, personality)

    return StartResponse(
        session_id=session_id,
        first_message=first_msg,
        industry_cn=industry_cn,
        scenario_cn=scenario_cn,
        personality_cn=personality_cn,
        config={
            "industry": industry,
            "industry_cn": industry_cn,
            "scenario": scenario,
            "scenario_cn": scenario_cn,
            "personality": personality,
            "personality_cn": personality_cn,
        },
    )


@router.post("/send", response_model=SendResponse)
async def send_message(req: SendRequest):
    """发送消息，获取客户智能回复"""
    session = sessions.get(req.session_id)
    if not session:
        return SendResponse(reply="会话不存在，请先开始新的训练。", session_id=req.session_id)

    config = session["config"]
    history = session["messages"]
    history.append(ChatMessage(role="user", content=req.message))

    kb = _get_kb()
    reply = generate_customer_reply(config, history, kb)
    history.append(ChatMessage(role="customer", content=reply))

    return SendResponse(reply=reply, session_id=req.session_id)


@router.post("/end/{session_id}", response_model=EndResponse)
async def end_training(session_id: str):
    """结束训练，使用 LLM 对整场对话进行智能评分"""
    session = sessions.get(session_id)
    if not session:
        return EndResponse(
            scores=[ScoreDimension(key="opening", label="开场能力", score=60, color="#6366f1"),
                    ScoreDimension(key="discovery", label="需求挖掘", score=60, color="#06b6d4"),
                    ScoreDimension(key="objection", label="异议处理", score=60, color="#f59e0b"),
                    ScoreDimension(key="solution", label="方案呈现", score=60, color="#10b981"),
                    ScoreDimension(key="closing", label="收尾能力", score=60, color="#ef4444")],
            avg_score=60, summary="未找到训练会话记录。", takeaway="请先完成模拟训练再评分。", session_id=session_id)

    config = session["config"]
    history = session["messages"]

    kb = _get_kb()
    result = score_conversation(config, history, kb)

    scores = [ScoreDimension(key=s.key, label=s.label, score=s.score, color=s.color, comment=s.comment) for s in result.scores]
    sessions.pop(session_id, None)

    return EndResponse(scores=scores, avg_score=result.avg_score, summary=result.summary, takeaway=result.takeaway, session_id=session_id)


@router.get("/options")
async def get_training_options():
    """获取训练配置选项列表"""
    return {
        "industries": [{"key": k, "label": v} for k, v in INDUSTRY_OPTIONS.items()],
        "scenarios": [{"key": k, "label": v} for k, v in SCENARIO_OPTIONS.items()],
        "personality": [{"key": k, "label": v} for k, v in PERSONALITY_MAP.items()],
    }
