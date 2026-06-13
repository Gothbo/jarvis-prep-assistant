"""Training chat engine — LLM-powered role-play with rule-based fallback."""

import json
import logging
import os
import random
from dataclasses import dataclass, field

from jarvis.engine.intent import IntentResult
from jarvis.knowledge.loader import KnowledgeBase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

PERSONALITY_MAP = {
    "skeptical": "怀疑型",
    "budget_conscious": "预算敏感型",
    "technical_expert": "技术专家型",
    "friendly": "友好型",
}

PERSONALITY_REVERSE = {v: k for k, v in PERSONALITY_MAP.items()}

SCENARIO_LABELS = {
    "compliance": "合规审计",
    "data_leak": "数据安全",
    "ransomware": "勒索防护",
    "apt": "高级威胁防护",
    "phishing": "钓鱼攻击防护",
}

INDUSTRY_LABELS = {
    "manufacturing": "制造业",
    "finance": "金融",
    "healthcare": "医疗",
    "government": "政务",
    "education": "教育",
    "retail": "零售",
}


@dataclass
class TrainingConfig:
    industry: str
    scenario: str
    personality: str  # key from PERSONALITY_MAP


@dataclass
class ChatMessage:
    role: str  # "customer" | "user"
    content: str


@dataclass
class ScoreDimension:
    key: str
    label: str
    score: int
    color: str
    comment: str = ""


@dataclass
class TrainingResult:
    scores: list[ScoreDimension]
    avg_score: int
    summary: str
    takeaway: str


# ---------------------------------------------------------------------------
# Customer reply generation
# ---------------------------------------------------------------------------

_FALLBACK_REPLIES: dict[str, list[str]] = {
    "skeptical": [
        "这个方案听起来不错，但你们有同行业的成功案例吗？",
        "实施周期多长？我们等不起太长时间。",
        "你们的方案跟竞品比有什么优势？",
        "我需要看到更详细的 ROI 分析才能做决定。",
        "之前也试过类似方案，效果一般，你们凭什么不一样？",
    ],
    "budget_conscious": [
        "价格方面呢？我们今年的预算已经分配了大半。",
        "能不能先做一个小范围的试点？",
        "分期付款可以吗？一次性投入太大了。",
        "我们老板对安全投入一直很谨慎，需要看到明确的收益。",
        "有没有更经济的方案？不需要一步到位。",
    ],
    "technical_expert": [
        "API 安全这块，你们能覆盖哪些攻击类型？",
        "你们的检测引擎是基于签名还是行为分析？误报率多少？",
        "能否跟现有的 SIEM 平台集成？支持哪些协议？",
        "部署模式是什么？支持私有化部署吗？",
        "你们的威胁情报数据源有哪些？更新频率？",
    ],
    "friendly": [
        "听起来不错，能再详细说说吗？",
        "我们团队之前也讨论过这个问题，正好需要了解。",
        "好的，那下一步怎么推进？",
        "我觉得这个方向是对的，还有其他建议吗？",
        "谢谢你的分析，很有帮助。我们内部讨论一下。",
    ],
}

# Generic replies when personality-specific list is exhausted
_GENERIC_REPLIES = [
    "嗯，让我想想...还有其他需要注意的吗？",
    "这个我们确实需要考虑。",
    "好的，那关于实施方面有什么具体要求？",
    "我们内部还需要再评估一下。",
]


def generate_customer_reply(
    config: TrainingConfig,
    history: list[ChatMessage],
    kb: KnowledgeBase,
) -> str:
    """Generate a customer reply, trying LLM first, then rule-based fallback."""
    # Try LLM
    try:
        return _llm_customer_reply(config, history, kb)
    except Exception as e:
        logger.info("LLM customer reply failed (%s), using fallback", e)

    # Fallback
    return _rule_customer_reply(config, history)


def _llm_customer_reply(
    config: TrainingConfig,
    history: list[ChatMessage],
    kb: KnowledgeBase,
) -> str:
    """Use LLM to generate customer reply."""
    from openai import OpenAI

    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key:
        raise RuntimeError("LLM_API_KEY not configured")

    # Build context from knowledge base
    relevant_cases = [c for c in kb.cases if c.industry == config.industry]
    case_context = ""
    if relevant_cases:
        case = relevant_cases[0]
        case_context = f"Client deep pain: {case.pain_points.deep}"

    personality_cn = PERSONALITY_MAP.get(config.personality, config.personality)
    industry_cn = INDUSTRY_LABELS.get(config.industry, config.industry)

    system_prompt = f"""You are role-playing as a customer in a sales meeting.

Customer profile:
- Industry: {industry_cn} ({config.industry})
- Scenario: {config.scenario}
- Personality: {personality_cn} ({config.personality})
{f'- Context: {case_context}' if case_context else ''}

Rules:
- Stay in character as the customer
- Respond in Chinese (中文)
- Keep responses to 1-3 sentences
- Be realistic — ask follow-up questions, raise concerns, show personality
- Do NOT break character or mention that you are an AI"""

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        role = "assistant" if msg.role == "customer" else "user"
        messages.append({"role": role, "content": msg.content})

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        timeout=float(os.getenv("LLM_TIMEOUT", "8.0")),
    )

    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=messages,
        temperature=0.9,
        max_tokens=200,
    )

    return response.choices[0].message.content.strip()


def _rule_customer_reply(
    config: TrainingConfig,
    history: list[ChatMessage],
) -> str:
    """Rule-based fallback for customer replies."""
    replies = _FALLBACK_REPLIES.get(config.personality, _GENERIC_REPLIES)
    # Avoid repeating the same reply
    used = {m.content for m in history if m.role == "customer"}
    available = [r for r in replies if r not in used]
    if not available:
        available = _GENERIC_REPLIES
    return random.choice(available)


# ---------------------------------------------------------------------------
# First message
# ---------------------------------------------------------------------------

def generate_first_message(config: TrainingConfig, kb: KnowledgeBase) -> str:
    """Generate the customer's opening message."""
    industry_cn = INDUSTRY_LABELS.get(config.industry, config.industry)
    scenario_cn = SCENARIO_LABELS.get(config.scenario, config.scenario)
    return (
        f"你好，我是{industry_cn}行业负责{scenario_cn}相关工作的。"
        f"我们最近遇到了一些安全方面的问题，想了解一下你们的解决方案。"
    )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

_DIMENSIONS = [
    ("opening", "开场能力", "#6366f1"),
    ("discovery", "需求挖掘", "#06b6d4"),
    ("objection", "异议处理", "#f59e0b"),
    ("solution", "方案呈现", "#10b981"),
    ("closing", "收尾能力", "#ef4444"),
]


def score_conversation(
    config: TrainingConfig,
    history: list[ChatMessage],
    kb: KnowledgeBase,
) -> TrainingResult:
    """Score the training conversation."""
    try:
        return _llm_score(config, history, kb)
    except Exception as e:
        logger.info("LLM scoring failed (%s), using rule-based", e)

    return _rule_score(config, history)


def _llm_score(
    config: TrainingConfig,
    history: list[ChatMessage],
    kb: KnowledgeBase,
) -> TrainingResult:
    """Use LLM to score the conversation."""
    from openai import OpenAI

    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key:
        raise RuntimeError("LLM_API_KEY not configured")

    personality_cn = PERSONALITY_MAP.get(config.personality, config.personality)
    industry_cn = INDUSTRY_LABELS.get(config.industry, config.industry)

    transcript = "\n".join(
        f"{'销售代表' if m.role == 'user' else '客户'}: {m.content}"
        for m in history
    )

    prompt = f"""Evaluate this sales training conversation and return a JSON score.

Context: {industry_cn} industry, {config.scenario} scenario, customer personality: {personality_cn}

Conversation:
{transcript}

Return JSON with these fields:
- "opening": score 0-100 for opening ability (开场能力)
- "discovery": score 0-100 for needs discovery (需求挖掘)
- "objection": score 0-100 for objection handling (异议处理)
- "solution": score 0-100 for solution presentation (方案呈现)
- "closing": score 0-100 for closing ability (收尾能力)
- "summary": 2-3 sentence overall evaluation in Chinese
- "takeaway": one key learning point in Chinese

Respond ONLY with valid JSON."""

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        timeout=float(os.getenv("LLM_TIMEOUT", "10.0")),
    )

    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    data = json.loads(response.choices[0].message.content)

    scores = []
    for key, label, color in _DIMENSIONS:
        s = min(100, max(0, int(data.get(key, 70))))
        scores.append(ScoreDimension(key=key, label=label, score=s, color=color))

    avg = round(sum(s.score for s in scores) / len(scores))
    return TrainingResult(
        scores=scores,
        avg_score=avg,
        summary=data.get("summary", "评分生成中..."),
        takeaway=data.get("takeaway", "继续练习，不断提升！"),
    )


def _rule_score(
    config: TrainingConfig,
    history: list[ChatMessage],
) -> TrainingResult:
    """Rule-based scoring fallback."""
    user_msgs = [m for m in history if m.role == "user"]
    total_msgs = len(user_msgs)

    # Heuristic scoring based on message count and length
    base = 60
    length_bonus = min(15, total_msgs * 3)
    detail_bonus = min(15, sum(len(m.content) for m in user_msgs) // 50)

    opening = min(95, base + length_bonus + 5)
    discovery = min(95, base + detail_bonus + 3)
    objection = min(95, base + length_bonus)
    solution = min(95, base + detail_bonus)
    closing = min(95, base + length_bonus - 2)

    scores = [
        ScoreDimension("opening", "开场能力", opening, "#6366f1"),
        ScoreDimension("discovery", "需求挖掘", discovery, "#06b6d4"),
        ScoreDimension("objection", "异议处理", objection, "#f59e0b"),
        ScoreDimension("solution", "方案呈现", solution, "#10b981"),
        ScoreDimension("closing", "收尾能力", closing, "#ef4444"),
    ]
    avg = round(sum(s.score for s in scores) / len(scores))

    summary = (
        f"本次训练共进行了 {total_msgs} 轮对话。"
        f"开场表现{'有力' if opening >= 75 else '可以更自信'}，"
        f"需求挖掘{'较为深入' if discovery >= 75 else '可以更主动提问'}。"
        f"建议多准备行业案例来增强说服力。"
    )

    takeaway = (
        "在面对客户异议时，先认可客户的顾虑，再用行业案例和数据来回应，"
        "会比单纯解释技术方案更有效。"
    )

    return TrainingResult(
        scores=scores, avg_score=avg, summary=summary, takeaway=takeaway
    )
