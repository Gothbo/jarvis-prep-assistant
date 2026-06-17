"""Score report generator — produces Markdown reports for training sessions."""

from __future__ import annotations

from typing import Any

from jarvis.engine.training import (
    INDUSTRY_LABELS,
    PERSONALITY_MAP,
    SCENARIO_LABELS,
)

# Threshold below which a dimension is flagged as weak and needs improvement.
_WEAK_THRESHOLD = 70

# Actionable improvement tips keyed by dimension identifier.
_IMPROVEMENT_TIPS: dict[str, str] = {
    "opening": (
        "练习更有针对性的开场白：提前研究客户行业背景，"
        "用行业痛点或近期安全事件切入，快速建立专业形象和对话价值。"
    ),
    "discovery": (
        "加强需求挖掘能力：围绕 environment / time / asset / budget 四个维度"
        "设计开放式问题，引导客户主动表达真实需求和痛点。"
    ),
    "objection": (
        "提升异议处理技巧：先认可客户顾虑（\"您说得很对...\"），"
        "再用行业案例和数据回应，避免单纯解释技术细节。"
    ),
    "solution": (
        "优化方案呈现方式：先总结客户核心需求，再逐一对应解决方案，"
        "配合 ROI 分析或同行业成功案例增强说服力。"
    ),
    "closing": (
        "强化收尾推动能力：在对话尾声明确总结共识，"
        "提出具体的下一步行动（如技术交流会、方案评审会、试用部署等），"
        "避免对话无果而终。"
    ),
}


def _get(obj: Any, attr: str, default: Any = "") -> Any:
    """Get a value from a dataclass/object or dict.

    Supports both attribute access (for dataclass instances) and key lookup
    (for plain dicts), making the generator flexible for different callers.

    Args:
        obj: The object or dict to read from.
        attr: The attribute name or dict key.
        default: Fallback value when the attribute/key is missing.

    Returns:
        The resolved value, or *default* if not found.
    """
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def generate_score_summary(scores: list) -> str:
    """Generate the Markdown scoring breakdown section.

    Produces a table with each dimension's name, score, and visual progress
    bar, followed by the overall average score.

    Args:
        scores: List of ``ScoreDimension`` objects (or dicts with keys
            ``key``, ``label``, ``score``).

    Returns:
        A Markdown-formatted string containing the scoring section.
    """
    if not scores:
        return ""

    lines: list[str] = []
    lines.append("### 五维评分\n")
    lines.append("| 维度 | 得分 | 评分条 |")
    lines.append("|:-----|:----:|:-------|")

    total = 0
    comments: list[tuple[str, str]] = []
    for s in scores:
        label = _get(s, "label", "")
        score = _get(s, "score", 0)
        comment = _get(s, "comment", "")
        total += score

        filled = score // 10
        bar = "\u25a0" * filled + "\u25a1" * (10 - filled)
        lines.append(f"| {label} | {score} | {bar} |")

        if comment:
            comments.append((label, comment))

    avg = round(total / len(scores))
    lines.append("")
    lines.append(f"**综合评分：{avg}**")

    # Append per-dimension feedback when available
    if comments:
        lines.append("")
        for label, comment in comments:
            lines.append(f"- **{label}**：{comment}")

    return "\n".join(lines)


def generate_markdown_report(session_data: dict) -> str:
    """Generate a full Markdown report for a training session.

    The report includes the session metadata, full conversation transcript,
    five-dimension scoring breakdown, overall assessment, and targeted
    improvement suggestions for dimensions that scored below the threshold.

    Args:
        session_data: A dictionary containing:

            - ``config``: ``TrainingConfig`` instance (or dict with keys
              ``industry``, ``scenario``, ``personality``).
            - ``messages``: List of ``ChatMessage`` instances (or dicts with
              keys ``role``, ``content``).
            - ``result``: ``TrainingResult`` instance (or dict with keys
              ``scores``, ``avg_score``, ``summary``, ``takeaway``).
            - ``datetime`` (optional): Human-readable date/time string.
              Defaults to ``"未知"``.

    Returns:
        A complete Markdown document as a string.
    """
    config = session_data.get("config")
    messages: list = session_data.get("messages", [])
    result = session_data.get("result")
    dt_str: str = session_data.get("datetime", "未知")

    # Resolve display labels from config
    industry_key = _get(config, "industry", "")
    scenario_key = _get(config, "scenario", "")
    personality_key = _get(config, "personality", "")

    industry_cn = INDUSTRY_LABELS.get(industry_key, industry_key)
    scenario_cn = SCENARIO_LABELS.get(scenario_key, scenario_key)
    personality_cn = PERSONALITY_MAP.get(personality_key, personality_key)

    sections: list[str] = []

    # ------------------------------------------------------------------
    # Title
    # ------------------------------------------------------------------
    sections.append("# 模拟训练评分报告\n")
    sections.append(f"> 生成时间：{dt_str}  ")
    sections.append("> 生成工具：JARVIS 智能训练系统\n")

    # ------------------------------------------------------------------
    # Session configuration summary
    # ------------------------------------------------------------------
    sections.append("## 训练配置\n")
    sections.append(f"- **目标行业**：{industry_cn}")
    sections.append(f"- **业务场景**：{scenario_cn}")
    sections.append(f"- **客户性格**：{personality_cn}")
    sections.append(f"- **对话轮次**：{len(messages)} 条消息")
    sections.append("")

    # ------------------------------------------------------------------
    # Conversation transcript
    # ------------------------------------------------------------------
    sections.append("## 对话记录\n")
    if messages:
        for msg in messages:
            role_raw = _get(msg, "role", "")
            content = _get(msg, "content", "")
            role_label = "售前顾问" if role_raw == "user" else "客户"
            sections.append(f"**{role_label}**：{content}\n")
    else:
        sections.append("（无对话记录）\n")

    # ------------------------------------------------------------------
    # Five-dimension scoring breakdown
    # ------------------------------------------------------------------
    if result:
        scores = _get(result, "scores", [])
        summary_text = _get(result, "summary", "")
        takeaway_text = _get(result, "takeaway", "")

        sections.append("## 评分详情\n")
        sections.append(generate_score_summary(scores))
        sections.append("")

        # --------------------------------------------------------------
        # Overall assessment
        # --------------------------------------------------------------
        sections.append("## 综合评价\n")
        sections.append(f"{summary_text}\n")
        sections.append(f"**关键提炼**：{takeaway_text}\n")

        # --------------------------------------------------------------
        # Improvement suggestions
        # --------------------------------------------------------------
        weak_dims: list[str] = []
        for s in scores:
            if _get(s, "score", 100) < _WEAK_THRESHOLD:
                weak_dims.append(_get(s, "key", ""))

        if weak_dims:
            sections.append("## 改进建议\n")
            for dim_key in weak_dims:
                label = _DIM_LABELS.get(dim_key, dim_key)
                tip = _IMPROVEMENT_TIPS.get(dim_key, "")
                if tip:
                    sections.append(f"### {label}\n")
                    sections.append(f"{tip}\n")

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    sections.append("---\n")
    sections.append("*本报告由 JARVIS 智能训练系统自动生成，仅供训练参考。*")

    return "\n".join(sections)


# Internal label lookup for dimension keys (used in improvement section).
_DIM_LABELS: dict[str, str] = {
    "opening": "开场能力",
    "discovery": "需求挖掘",
    "objection": "异议处理",
    "solution": "方案呈现",
    "closing": "收尾能力",
}
