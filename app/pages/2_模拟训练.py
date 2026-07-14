"""Training Role-Play page — chat with an AI customer and get scored."""

import math
from datetime import datetime
from pathlib import Path

import streamlit as st

from jarvis.config import load_config

load_config()

# ---------------------------------------------------------------------------
# Page config — MUST be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="JARVIS - 模拟训练",
    page_icon="../favicon.svg",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
try:
    from jarvis.engine.training import (
        INDUSTRY_LABELS,
        INDUSTRY_SCENARIOS,
        PERSONALITY_MAP,
        PERSONALITY_REVERSE,
        SCENARIO_LABELS,
        ChatMessage,
        ScoreDimension,
        TrainingConfig,
        generate_customer_reply,
        generate_first_message,
        score_conversation,
    )
    from jarvis.generators.score_report import generate_markdown_report
    from jarvis.knowledge.loader import load_all
    from jarvis.ui.icons import icon
    from jarvis.ui.styles import inject_css

    _IMPORTS_OK = True
except Exception as _import_err:
    _IMPORTS_OK = False
    _IMPORT_ERROR = _import_err

if _IMPORTS_OK:
    inject_css()

# Page-specific CSS
st.markdown("""
<style>
/* -- Config section card -- */
.training-config-card {
    background: var(--jarvis-surface);
    border: 1px solid var(--jarvis-border);
    border-radius: var(--radius-md);
    padding: 20px 24px;
    margin-bottom: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.training-config-card h4 {
    font-size: 15px;
    font-weight: 600;
    color: var(--jarvis-text);
    margin: 0 0 12px 0;
}
.training-tips-card {
    background: var(--jarvis-background);
    border: 1px solid var(--jarvis-border);
    border-radius: var(--radius-md);
    padding: 20px 24px;
    margin-bottom: 16px;
}
.training-tips-card h4 {
    font-size: 15px;
    font-weight: 600;
    color: var(--jarvis-text);
    margin: 0 0 12px 0;
}
.training-tips-card ul { margin: 0; padding-left: 18px; }
.training-tips-card li { font-size: 13px; color: var(--jarvis-text-secondary); line-height: 1.8; }

/* -- Chat area -- */
.chat-input-area {
    background: var(--jarvis-background);
    border: 1px solid var(--jarvis-border);
    border-radius: var(--radius-md);
    padding: 16px 20px;
}

/* -- Score page header -- */
.score-header-card {
    background: linear-gradient(135deg, var(--jarvis-primary) 0%, var(--jarvis-primary-light) 100%);
    border-radius: var(--radius-lg);
    padding: 28px 32px;
    color: white;
    margin-bottom: 20px;
}
.score-header-card h2 { color: white !important; margin: 0 0 4px 0 !important; }
.score-header-card p { color: rgba(255,255,255,0.85) !important; margin: 0 !important; }

/* -- Training status bar -- */
.training-status-bar {
    background: var(--jarvis-background);
    border: 1px solid var(--jarvis-border);
    border-radius: var(--radius-md);
    padding: 12px 20px;
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;
    font-size: 13px;
    color: var(--jarvis-text-secondary);
}
.training-status-bar .status-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--jarvis-success); display: inline-block;
    animation: pulse 1.5s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* -- Chat messages -- */
.chat-msg {
    display: flex; gap: 12px; margin-bottom: 18px;
    animation: fadeSlideIn 0.35s ease-out;
}
.chat-msg-right { flex-direction: row-reverse; }
.avatar {
    width: 38px; height: 38px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; font-weight: 700; flex-shrink: 0;
    box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}
.avatar-customer {
    background: linear-gradient(135deg, var(--jarvis-primary-bg) 0%, #c7d2fe 100%);
    color: #4338ca;
}
.avatar-user {
    background: linear-gradient(135deg, var(--jarvis-text) 0%, #334155 100%);
    color: white;
}
.bubble-wrap { max-width: 75%; }
.bubble-left { margin-right: auto; }
.bubble-right { margin-left: auto; }
.chat-bubble {
    padding: 14px 18px; border-radius: 16px; font-size: 14px;
    line-height: 1.7; word-wrap: break-word;
}
.chat-customer {
    background: var(--jarvis-background); border: 1px solid var(--jarvis-border);
    border-bottom-left-radius: 4px;
}
.chat-user {
    background: linear-gradient(135deg, var(--jarvis-primary) 0%, var(--jarvis-primary-light) 100%);
    color: white; border-bottom-right-radius: 4px;
}
.chat-time {
    font-size: 11px; color: var(--jarvis-text-muted); margin-top: 4px; padding-left: 4px;
}
.chat-time-right { text-align: right; padding-right: 4px; }

/* -- Score bars -- */
.score-bar-wrap {
    display: flex; align-items: center; gap: 12px; margin-bottom: 14px;
}
.score-label { font-size: 13px; color: var(--jarvis-text-secondary); width: 80px; font-weight: 500; }
.score-track {
    flex: 1; height: 8px; background: var(--jarvis-background);
    border-radius: 4px; overflow: hidden;
}
.score-fill {
    height: 100%; border-radius: 4px;
    animation: barGrow 0.8s ease-out;
}
.score-val { font-size: 14px; font-weight: 600; width: 30px; text-align: right; }

/* -- Boxes -- */
.warning-box {
    background: var(--jarvis-warning-bg); border: 1px solid rgba(245,158,11,0.3);
    border-radius: 12px; padding: 16px 20px; color: #92400e;
}
.score-card {
    background: var(--jarvis-surface); border: 1px solid var(--jarvis-border); border-radius: var(--radius-lg);
    padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

/* -- Animations -- */
@keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes barGrow {
    from { width: 0 !important; }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Radar chart helper (pure SVG, no external library needed)
# ---------------------------------------------------------------------------
def _render_radar_svg(scores: list, size: int = 260) -> str:
    """Generate an SVG radar chart from score dimensions."""
    cx, cy = size // 2, size // 2
    radius = size // 2 - 40
    n = len(scores)
    if n < 3:
        return ""

    def _point(angle_offset: float, r: float) -> tuple[float, float]:
        angle = (2 * math.pi / n) * angle_offset - math.pi / 2
        return cx + r * math.cos(angle), cy + r * math.sin(angle)

    # Grid rings (20%, 40%, 60%, 80%, 100%)
    grid_lines = ""
    for pct in [0.2, 0.4, 0.6, 0.8, 1.0]:
        pts = " ".join(
            f"{_point(i, radius * pct)[0]:.1f},{_point(i, radius * pct)[1]:.1f}"
            for i in range(n)
        )
        grid_lines += f'<polygon points="{pts}" fill="none" stroke="var(--jarvis-border)" stroke-width="1"/>'

    # Axis lines
    axis_lines = ""
    for i in range(n):
        px, py = _point(i, radius)
        axis_lines += f'<line x1="{cx}" y1="{cy}" x2="{px:.1f}" y2="{py:.1f}" stroke="var(--jarvis-border)" stroke-width="1"/>'

    # Data polygon
    data_pts = " ".join(
        f"{_point(i, radius * s.score / 100)[0]:.1f},{_point(i, radius * s.score / 100)[1]:.1f}"
        for i, s in enumerate(scores)
    )
    data_polygon = (
        f'<polygon points="{data_pts}" fill="var(--jarvis-primary-bg)" '
        f'stroke="var(--jarvis-primary)" stroke-width="2.5"/>'
    )

    # Data dots
    dots = ""
    for i, s in enumerate(scores):
        dx, dy = _point(i, radius * s.score / 100)
        dots += f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="4" fill="{s.color}" stroke="white" stroke-width="2"/>'

    # Labels
    labels = ""
    for i, s in enumerate(scores):
        lx, ly = _point(i, radius + 24)
        anchor = "middle"
        if lx < cx - 10:
            anchor = "end"
        elif lx > cx + 10:
            anchor = "start"
        labels += (
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
            f'font-size="11" font-weight="500" fill="var(--jarvis-text-secondary)">{s.label}</text>'
        )
        # Score value below label
        labels += (
            f'<text x="{lx:.1f}" y="{ly + 14:.1f}" text-anchor="{anchor}" '
            f'font-size="12" font-weight="700" fill="{s.color}">{s.score}</text>'
        )

    return (
        f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'{grid_lines}{axis_lines}{data_polygon}{dots}{labels}</svg>'
    )


# ---------------------------------------------------------------------------
# Chat bubble rendering helper
# ---------------------------------------------------------------------------
def _render_chat_bubble(role: str, content: str, timestamp: str = "") -> str:
    """Render a styled chat bubble with avatar and optional timestamp."""
    ts_html = ""
    if timestamp:
        if role == "customer":
            ts_html = f'<div class="chat-time">{timestamp}</div>'
        else:
            ts_html = f'<div class="chat-time chat-time-right">{timestamp}</div>'

    if role == "customer":
        return (
            f'<div class="chat-msg chat-msg-left">'
            f'<div class="avatar avatar-customer">C</div>'
            f'<div class="bubble-wrap bubble-left">'
            f'<div class="chat-bubble chat-customer">{content}</div>'
            f'{ts_html}'
            f'</div></div>'
        )
    return (
        f'<div class="chat-msg chat-msg-right">'
        f'<div class="avatar avatar-user">S</div>'
        f'<div class="bubble-wrap bubble-right">'
        f'<div class="chat-bubble chat-user">{content}</div>'
        f'{ts_html}'
        f'</div></div>'
    )


# ---------------------------------------------------------------------------
# Database initialisation (singleton in session_state)
# ---------------------------------------------------------------------------
def _get_training_db():
    """Return a TrainingDB instance, creating it once per session."""
    if "training_db" not in st.session_state:
        try:
            from jarvis.paths import CACHE_DIR
            from jarvis.persistence import TrainingDB
            db_path = CACHE_DIR / "training_sessions.db"
            st.session_state["training_db"] = TrainingDB(db_path)
        except Exception:
            try:
                import tempfile

                from jarvis.persistence import TrainingDB
                db_path = Path(tempfile.gettempdir()) / "jarvis_cache" / "training_sessions.db"
                st.session_state["training_db"] = TrainingDB(db_path)
            except Exception:
                st.session_state["training_db"] = None
    return st.session_state["training_db"]


def _save_new_msgs(db, session_id, msgs, saved_count):
    """Persist any messages beyond *saved_count* and return the new count."""
    if db is None or session_id is None:
        return saved_count
    new_msgs = msgs[saved_count:]
    if new_msgs:
        db.save_messages(session_id, new_msgs)
    return len(msgs)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## JARVIS 模拟训练")
    st.markdown("AI 客户角色扮演 · 销售话术练习")
    st.divider()

    phase = st.session_state.get("training_phase", "config")
    if phase == "chatting":
        cfg = st.session_state.get("training_config")
        if cfg:
            ind_cn = INDUSTRY_LABELS.get(cfg.industry, cfg.industry)
            pers_cn = PERSONALITY_MAP.get(cfg.personality, cfg.personality)
            st.metric("行业", ind_cn)
            st.metric("场景", cfg.scenario)
            st.metric("性格", pers_cn)
            st.metric("消息数", len(st.session_state.get("training_msgs", [])))

    st.divider()

    # ------------------------------------------------------------------
    # 训练历史 (Training History)
    # ------------------------------------------------------------------
    st.markdown("### 训练历史")
    _db = _get_training_db()
    if _db is not None:
        try:
            _sessions = _db.list_sessions()
        except Exception:
            _sessions = []

        if not _sessions:
            st.caption("暂无历史记录")
        else:
            for _sess in _sessions:
                _date_str = _sess["created_at"][:10] if _sess.get("created_at") else "未知日期"
                _ind_label = INDUSTRY_LABELS.get(_sess["industry"], _sess.get("industry", ""))
                _score_val = _sess.get("final_score")
                _score_str = str(_score_val) if _score_val is not None else "未评分"
                _hdr = f"**{_date_str}** | {_ind_label} | {_score_str}分"

                with st.expander(_hdr):
                    _view_key = f"view_{_sess['id']}"
                    _del_key = f"del_{_sess['id']}"
                    _c1, _c2 = st.columns(2)
                    with _c1:
                        if st.button("查看", key=_view_key, use_container_width=True):
                            st.session_state["training_phase"] = "review"
                            st.session_state["review_session_id"] = _sess["id"]
                            st.rerun()
                    with _c2:
                        if st.button("删除", key=_del_key, use_container_width=True):
                            _db.delete_session(_sess["id"])
                            if st.session_state.get("review_session_id") == _sess["id"]:
                                st.session_state.pop("review_session_id", None)
                                st.session_state["training_phase"] = "config"
                            st.rerun()
    else:
        st.caption("数据库初始化失败，历史记录不可用")

    st.divider()
    st.caption("JARVIS v0.3 · Training Module")

# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------
st.markdown(
    f"""
<div style="display:flex;align-items:center;gap:12px;padding:8px 0 4px;">
    {icon("chat_dots", size=32, color="var(--jarvis-primary)")}
    <div>
        <h2 style="margin:0;font-size:24px;font-weight:700;color:var(--jarvis-text);">模拟训练</h2>
        <p style="margin:4px 0 0;font-size:14px;color:var(--jarvis-text-secondary);">与 AI 客户进行真实场景的多轮对话训练，提升售前沟通能力</p>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

st.divider()

if not _IMPORTS_OK:
    st.error(f"模块导入失败：{_IMPORT_ERROR}")
    st.stop()

# ---------------------------------------------------------------------------
# Phase: CONFIG
# ---------------------------------------------------------------------------
if phase == "config":
    st.markdown("### 训练配置")

    col1, col2 = st.columns([1, 2])

    with col1:
        industry_options = list(INDUSTRY_LABELS.keys())
        industry_labels = list(INDUSTRY_LABELS.values())
        selected_industry_label = st.selectbox(
            "目标行业", industry_labels, key="train_ind_sel"
        )
        selected_industry = industry_labels.index(selected_industry_label)
        industry_key = industry_options[selected_industry]

        scenario_map = INDUSTRY_SCENARIOS or {
            "manufacturing": ["ransomware", "apt", "compliance"],
            "finance": ["compliance", "data_leak", "ransomware", "apt"],
            "healthcare": ["data_leak", "ransomware", "compliance"],
            "government": ["compliance", "data_leak"],
            "education": ["data_leak", "compliance"],
            "retail": ["data_leak", "ransomware", "compliance"],
        }
        scenario_options = scenario_map.get(industry_key, ["ransomware"])
        scenario_display = [SCENARIO_LABELS.get(s, s) for s in scenario_options]
        selected_scenario_label = st.selectbox(
            "业务场景", scenario_display, key="train_scen_sel"
        )
        selected_scenario = scenario_options[scenario_display.index(selected_scenario_label)]

        personality_labels = list(PERSONALITY_MAP.values())
        selected_personality = st.selectbox(
            "客户性格", personality_labels, key="train_pers_sel"
        )
        personality_key = PERSONALITY_REVERSE.get(selected_personality, "skeptical")

        st.divider()
        if st.button("开始训练", type="primary", use_container_width=True):
            config = TrainingConfig(
                industry=industry_key,
                scenario=selected_scenario,
                personality=personality_key,
            )
            try:
                kb = load_all()
            except Exception as e:
                st.error(f"知识库加载失败：{e}")
                st.stop()

            first_msg = generate_first_message(config, kb)
            st.session_state["training_config"] = config
            st.session_state["training_kb"] = kb
            st.session_state["training_phase"] = "chatting"
            st.session_state["training_msgs"] = [
                ChatMessage(role="customer", content=first_msg)
            ]
            # Create DB session and persist the opening message
            _db = _get_training_db()
            if _db is not None:
                try:
                    _sid = _db.save_session(config, [], [])
                    _db.save_messages(_sid, [ChatMessage(role="customer", content=first_msg)])
                    st.session_state["training_session_id"] = _sid
                    st.session_state["training_saved_msg_count"] = 1
                except Exception:
                    st.session_state["training_session_id"] = None
                    st.session_state["training_saved_msg_count"] = 0
            else:
                st.session_state["training_session_id"] = None
                st.session_state["training_saved_msg_count"] = 0
            st.rerun()

    with col2:
        # Stats
        st.markdown('<div class="training-config-card">', unsafe_allow_html=True)
        st.markdown('<h4>训练统计</h4>', unsafe_allow_html=True)
        mc1, mc2, mc3 = st.columns(3)
        past_count = st.session_state.get("past_training_count", 0)
        past_avg = st.session_state.get("past_avg_score", 0)
        mc1.metric("已完成训练", str(past_count))
        mc2.metric("历史均分", str(past_avg) if past_avg else "—")
        mc3.metric("训练模块", "MVP")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("""
<div class="training-tips-card">
<h4>训练建议</h4>
<ul>
<li><b>开场</b>：先了解客户业务背景，再逐步深入技术细节</li>
<li><b>异议处理</b>：先认可客户顾虑，再用行业案例回应</li>
<li><b>收尾</b>：明确下一步行动，推动销售进程</li>
<li><b>提问</b>：围绕 environment / time / asset / budget 四个维度</li>
</ul>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Phase: CHATTING
# ---------------------------------------------------------------------------
elif phase == "chatting":
    config: TrainingConfig = st.session_state.get("training_config")
    msgs: list[ChatMessage] = st.session_state.get("training_msgs", [])
    kb = st.session_state.get("training_kb")

    if not config or kb is None:
        st.error("会话状态异常，请重新开始训练")
        st.session_state["training_phase"] = "config"
        st.rerun()

    ind_cn = INDUSTRY_LABELS.get(config.industry, config.industry)
    pers_cn = PERSONALITY_MAP.get(config.personality, config.personality)

    # Status bar
    st.markdown(
        f"""
<div class="training-status-bar">
    <span class="status-dot"></span>
    <span><b>模拟训练进行中</b></span>
    <span>{icon("compass", size=14, color="var(--jarvis-text-secondary)")} {ind_cn}</span>
    <span>{icon("target", size=14, color="var(--jarvis-text-secondary)")} {SCENARIO_LABELS.get(config.scenario, config.scenario)}</span>
    <span>{icon("chat_dots", size=14, color="var(--jarvis-text-secondary)")} {pers_cn}</span>
    <span>{icon("info", size=14, color="var(--jarvis-text-secondary)")} {len(msgs)} 条消息</span>
</div>
""",
        unsafe_allow_html=True,
    )

    cols_h = st.columns([5, 1])
    with cols_h[1]:
        if st.button("结束训练", type="secondary", use_container_width=True):
            with st.spinner("AI 正在评估你的表现..."):
                result = score_conversation(config, msgs, kb)
            st.session_state["training_result"] = result
            st.session_state["training_phase"] = "scored"
            # Update stats
            st.session_state["past_training_count"] = (
                st.session_state.get("past_training_count", 0) + 1
            )
            st.session_state["past_avg_score"] = result.avg_score
            # Persist remaining messages and scores to DB
            _db = _get_training_db()
            _sid = st.session_state.get("training_session_id")
            if _db is not None and _sid is not None:
                try:
                    _saved = st.session_state.get("training_saved_msg_count", 0)
                    _save_new_msgs(_db, _sid, msgs, _saved)
                    st.session_state["training_saved_msg_count"] = len(msgs)
                    _db.save_scores(_sid, result.scores)
                except Exception:
                    pass  # scoring already in session_state; DB is best-effort
            st.rerun()

    st.divider()

    # Chat messages
    now = datetime.now()
    for idx, m in enumerate(msgs):
        # Generate a pseudo-timestamp based on message index
        ts = now.strftime("%H:%M")
        st.markdown(
            _render_chat_bubble(m.role, m.content, ts),
            unsafe_allow_html=True,
        )

    st.divider()

    # Input — use dynamic key so input clears after each send
    _msg_counter = st.session_state.get("training_msg_counter", 0)
    col_in, col_send = st.columns([6, 1])
    with col_in:
        user_input = st.text_input(
            "输入回复",
            key=f"training_input_{_msg_counter}",
            label_visibility="collapsed",
            placeholder="输入你的回复...",
        )
    with col_send:
        send_clicked = st.button(
            "发送", type="primary", use_container_width=True,
            disabled=not user_input or not user_input.strip(),
        )

    if send_clicked and user_input and user_input.strip():
        msgs.append(ChatMessage(role="user", content=user_input.strip()))
        st.session_state["training_msgs"] = msgs

        with st.spinner("客户正在思考..."):
            reply = generate_customer_reply(config, msgs, kb)
        msgs.append(ChatMessage(role="customer", content=reply))
        st.session_state["training_msgs"] = msgs

        # Auto-save new messages to DB
        _db = _get_training_db()
        _sid = st.session_state.get("training_session_id")
        _saved = st.session_state.get("training_saved_msg_count", 0)
        st.session_state["training_saved_msg_count"] = _save_new_msgs(
            _db, _sid, msgs, _saved
        )

        # Increment counter so next rerun uses a new key → empty input box
        st.session_state["training_msg_counter"] = _msg_counter + 1

        st.rerun()

# ---------------------------------------------------------------------------
# Phase: SCORED
# ---------------------------------------------------------------------------
elif phase == "scored":
    result = st.session_state.get("training_result")
    if not result:
        st.error("评分数据丢失，请重新开始训练")
        st.session_state["training_phase"] = "config"
        st.rerun()

    st.markdown(
        f"""
<div class="score-header-card">
    <h2>训练评分</h2>
    <p>基于本次对话的 AI 综合评估 · 综合得分 <b>{result.avg_score}</b> 分</p>
</div>
""",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("### 五维评分")

        # Radar chart
        radar_svg = _render_radar_svg(result.scores)
        st.markdown(
            f'<div style="display:flex;justify-content:center;padding:10px 0 20px;">'
            f'{radar_svg}</div>',
            unsafe_allow_html=True,
        )

        for s in result.scores:
            st.markdown(
                f'<div class="score-bar-wrap">'
                f'<span class="score-label">{s.label}</span>'
                f'<div class="score-track">'
                f'<div class="score-fill" style="width:{s.score}%;background:{s.color};"></div>'
                f'</div>'
                f'<span class="score-val">{s.score}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown(f"""
<div style="margin-top:20px;padding-top:20px;border-top:1px solid var(--jarvis-border);
display:flex;justify-content:space-between;align-items:center;">
<span style="font-size:14px;color:var(--jarvis-text-secondary);">综合评分</span>
<span style="font-size:32px;font-weight:700;">{result.avg_score}</span>
</div>
""", unsafe_allow_html=True)

    with col2:
        st.markdown("### 综合评价")
        st.markdown(result.summary)

        st.markdown("### 关键提炼")
        st.markdown(
            f'<div class="warning-box">{result.takeaway}</div>',
            unsafe_allow_html=True,
        )

    # Export report
    session_data = {
        "config": st.session_state.get("training_config"),
        "messages": st.session_state.get("training_msgs", []),
        "result": result,
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    report_md = generate_markdown_report(session_data)
    filename = f"训练报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    st.download_button(
        label="导出报告",
        data=report_md,
        file_name=filename,
        mime="text/markdown",
        use_container_width=True,
    )

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("再次训练", type="primary", use_container_width=True):
            for k in [
                "training_phase", "training_config", "training_msgs",
                "training_kb", "training_result",
                "training_session_id", "training_saved_msg_count",
            ]:
                st.session_state.pop(k, None)
            st.rerun()
    with col_b:
        if st.button("返回首页", use_container_width=True):
            st.switch_page("Home.py")

# ---------------------------------------------------------------------------
# Phase: REVIEW (viewing a past session from 训练历史)
# ---------------------------------------------------------------------------
elif phase == "review":
    _db = _get_training_db()
    _review_sid = st.session_state.get("review_session_id")

    if _db is None or not _review_sid:
        st.error("无法加载历史会话")
        st.session_state["training_phase"] = "config"
        st.rerun()

    _review_data = _db.load_session(_review_sid)
    if not _review_data:
        st.error("该会话记录不存在或已被删除")
        st.session_state.pop("review_session_id", None)
        st.session_state["training_phase"] = "config"
        st.rerun()

    _sess_meta = _review_data["session"]
    _review_msgs = _review_data["messages"]
    _review_scores = _review_data["scores"]

    _ind_label = INDUSTRY_LABELS.get(_sess_meta["industry"], _sess_meta["industry"])
    _score_val = _sess_meta.get("final_score")
    _score_str = str(_score_val) if _score_val is not None else "未评分"

    st.markdown("## 历史训练回顾")
    st.markdown(
        f"**{_ind_label}** | {_sess_meta['scenario']} | "
        f"综合评分: **{_score_str}** | {_sess_meta['created_at'][:19]}"
    )
    st.divider()

    # ---- conversation replay ----
    st.markdown("### 对话记录")
    if not _review_msgs:
        st.caption("（无消息记录）")
    for m in _review_msgs:
        _role = m["role"]
        _content = m["content"]
        _ts = m.get("timestamp", "")
        if _ts and len(_ts) >= 16:
            _ts = _ts[11:16]  # Extract HH:MM from ISO timestamp
        else:
            _ts = ""
        st.markdown(
            _render_chat_bubble(_role, _content, _ts),
            unsafe_allow_html=True,
        )

    # ---- score bars + radar ----
    if _review_scores:
        st.divider()
        st.markdown("### 评分详情")

        _dim_labels = {
            "opening": ("开场能力", "#6366f1"),
            "discovery": ("需求挖掘", "#06b6d4"),
            "objection": ("异议处理", "#f59e0b"),
            "solution": ("方案呈现", "#10b981"),
            "closing": ("收尾能力", "#ef4444"),
        }

        # Build a lightweight score object for the radar chart
        _radar_scores = []
        for sc in _review_scores:
            _dim = sc["dimension"]
            _lbl_info = _dim_labels.get(_dim, (_dim, "#94a3b8"))
            _radar_scores.append(
                ScoreDimension(key=_dim, label=_lbl_info[0], score=sc["score"], color=_lbl_info[1])
            )
        if _radar_scores:
            radar_svg = _render_radar_svg(_radar_scores)
            st.markdown(
                f'<div style="display:flex;justify-content:center;padding:10px 0 20px;">'
                f'{radar_svg}</div>',
                unsafe_allow_html=True,
            )

        for sc in _review_scores:
            _dim = sc["dimension"]
            _sc_score = sc["score"]
            _lbl_info = _dim_labels.get(_dim, (_dim, "#94a3b8"))
            _sc_label = _lbl_info[0]
            _sc_color = _lbl_info[1]
            _feedback = sc.get("feedback", "")
            st.markdown(
                f'<div class="score-bar-wrap">'
                f'<span class="score-label">{_sc_label}</span>'
                f'<div class="score-track">'
                f'<div class="score-fill" style="width:{_sc_score}%;'
                f'background:{_sc_color};"></div>'
                f'</div>'
                f'<span class="score-val">{_sc_score}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if _feedback:
                st.caption(_feedback)

    st.divider()

    # ---- action buttons ----
    _ra, _rb = st.columns(2)
    with _ra:
        if st.button("返回", use_container_width=True):
            st.session_state.pop("review_session_id", None)
            st.session_state["training_phase"] = "config"
            st.rerun()
    with _rb:
        if st.button("删除此记录", type="secondary", use_container_width=True):
            _db.delete_session(_review_sid)
            st.session_state.pop("review_session_id", None)
            st.session_state["training_phase"] = "config"
            st.rerun()
