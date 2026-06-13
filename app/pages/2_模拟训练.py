"""Training Role-Play page — chat with an AI customer and get scored."""

import os
import streamlit as st

# ---------------------------------------------------------------------------
# Page config — MUST be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="JARVIS - 模拟训练",
    page_icon="🎭",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Bridge secrets → env (same pattern as Smart Prep page)
# ---------------------------------------------------------------------------
for _key in ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "LLM_TIMEOUT"]:
    if _key not in os.environ:
        try:
            val = st.secrets[_key]
            if val:
                os.environ[_key] = str(val)
        except (KeyError, FileNotFoundError):
            pass

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
try:
    from jarvis.engine.training import (
        TrainingConfig,
        ChatMessage,
        ScoreDimension,
        PERSONALITY_MAP,
        PERSONALITY_REVERSE,
        INDUSTRY_LABELS,
        generate_first_message,
        generate_customer_reply,
        score_conversation,
    )
    from jarvis.knowledge.loader import load_all

    _IMPORTS_OK = True
except Exception as _import_err:
    _IMPORTS_OK = False
    _IMPORT_ERROR = _import_err

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
.chat-bubble {
    padding: 14px 18px; border-radius: 14px; font-size: 14px;
    line-height: 1.7; margin-bottom: 8px; max-width: 85%;
}
.chat-customer {
    background: #f0f2f6; border: 1px solid #e0e0e0;
    border-bottom-left-radius: 4px;
}
.chat-user {
    background: #6366f1; color: white;
    border-bottom-right-radius: 4px; margin-left: auto;
}
.score-bar-wrap {
    display: flex; align-items: center; gap: 12px; margin-bottom: 14px;
}
.score-label { font-size: 13px; color: #64748b; width: 80px; font-weight: 500; }
.score-track {
    flex: 1; height: 8px; background: #f1f5f9;
    border-radius: 4px; overflow: hidden;
}
.score-fill { height: 100%; border-radius: 4px; transition: width 0.6s ease; }
.score-val { font-size: 14px; font-weight: 600; width: 30px; text-align: right; }
.warning-box {
    background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.3);
    border-radius: 12px; padding: 16px 20px; color: #92400e;
}
</style>
""", unsafe_allow_html=True)

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
    st.caption("JARVIS v0.3 · Training Module")

# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------
st.title("🎭 模拟训练")
st.markdown("与 AI 客户进行真实场景的多轮对话训练，提升售前沟通能力。")
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

        scenario_map = {
            "manufacturing": ["ransomware", "apt", "compliance"],
            "finance": ["compliance", "data_leak", "ransomware", "apt"],
            "healthcare": ["data_leak", "ransomware", "compliance"],
            "government": ["compliance", "data_leak"],
            "education": ["data_leak", "compliance"],
            "retail": ["data_leak", "ransomware", "compliance"],
        }
        scenario_options = scenario_map.get(industry_key, ["ransomware"])
        scenario_labels = {
            "ransomware": "勒索软件",
            "apt": "高级威胁",
            "data_leak": "数据泄露",
            "compliance": "合规审计",
            "phishing": "钓鱼攻击",
        }
        scenario_display = [scenario_labels.get(s, s) for s in scenario_options]
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
            st.rerun()

    with col2:
        # Stats
        mc1, mc2, mc3 = st.columns(3)
        past_count = st.session_state.get("past_training_count", 0)
        past_avg = st.session_state.get("past_avg_score", 0)
        mc1.metric("已完成训练", str(past_count))
        mc2.metric("历史均分", str(past_avg) if past_avg else "—")
        mc3.metric("训练模块", "MVP")

        st.markdown("""
#### 训练建议

- **开场**：先了解客户业务背景，再逐步深入技术细节
- **异议处理**：先认可客户顾虑，再用行业案例回应
- **收尾**：明确下一步行动，推动销售进程
- **提问**：围绕 environment / time / asset / budget 四个维度
        """)

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

    # Header
    cols_h = st.columns([3, 1])
    with cols_h[0]:
        st.markdown(f"**模拟训练进行中** — {ind_cn} · {config.scenario} · {pers_cn} · {len(msgs)} 条消息")
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
            st.rerun()

    st.divider()

    # Chat messages
    for m in msgs:
        if m.role == "customer":
            st.markdown(
                f'<div style="display:flex;gap:10px;margin-bottom:14px;">'
                f'<div style="width:34px;height:34px;border-radius:11px;'
                f'background:#e0e7ff;display:flex;align-items:center;'
                f'justify-content:center;font-size:13px;font-weight:600;'
                f'flex-shrink:0;">客</div>'
                f'<div class="chat-bubble chat-customer">{m.content}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="display:flex;gap:10px;margin-bottom:14px;'
                f'flex-direction:row-reverse;">'
                f'<div style="width:34px;height:34px;border-radius:11px;'
                f'background:#1e293b;color:white;display:flex;align-items:center;'
                f'justify-content:center;font-size:13px;font-weight:600;'
                f'flex-shrink:0;">我</div>'
                f'<div class="chat-bubble chat-user">{m.content}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # Input
    col_in, col_send = st.columns([6, 1])
    with col_in:
        user_input = st.text_input(
            "输入回复",
            key="training_input",
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

    st.markdown("## 训练评分")
    st.markdown("基于本次对话的 AI 综合评估")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 五维评分")
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
<div style="margin-top:20px;padding-top:20px;border-top:1px solid #e2e8f0;
display:flex;justify-content:space-between;align-items:center;">
<span style="font-size:14px;color:#64748b;">综合评分</span>
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

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("再次训练", type="primary", use_container_width=True):
            for k in [
                "training_phase", "training_config", "training_msgs",
                "training_kb", "training_result",
            ]:
                st.session_state.pop(k, None)
            st.rerun()
    with col_b:
        if st.button("返回首页", use_container_width=True):
            st.switch_page("Home.py")
