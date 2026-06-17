"""Smart Prep page - main Prep package generation UI."""

import streamlit as st

from jarvis.config import load_config

load_config()

# ---------------------------------------------------------------------------
# Top-level imports (wrapped so the page still renders if modules are missing)
# ---------------------------------------------------------------------------
try:
    from jarvis.engine.intent import recognize
    from jarvis.engine.llm_engine import LLMUnavailableError, generate_prep
    from jarvis.engine.rule_engine import generate_prep_fallback
    from jarvis.generators.ppt_outline import generate_outline
    from jarvis.intelligence.threat_feed import fetch_threats
    from jarvis.knowledge.loader import load_all

    _IMPORTS_OK = True
except Exception as _import_err:
    _IMPORTS_OK = False
    _IMPORT_ERROR = _import_err

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="JARVIS - 智能 Prep",
    page_icon="🛡️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Sidebar — project info & quick stats
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## JARVIS 智能 Prep")
    st.markdown("AI 驱动的销售拜访准备助手")
    st.divider()

    st.markdown("### 知识库概览")
    try:
        _kb = load_all()
        st.metric("案例数量", len(_kb.cases))
        st.metric("方法论数量", len(_kb.methodologies))
        st.metric("敏感度规则", len(_kb.sensitivities))
        st.metric("产品信息", len(_kb.products))
    except Exception:
        st.caption("知识库加载失败，请检查数据目录。")

    st.divider()
    st.caption("JARVIS v0.3 · Prep Assistant")

# ---------------------------------------------------------------------------
# Title & description
# ---------------------------------------------------------------------------
st.title("智能 Prep")
st.markdown("为你的客户拜访生成结构化 Prep 包。")

st.divider()

# ---------------------------------------------------------------------------
# Input section
# ---------------------------------------------------------------------------
user_input = st.text_area(
    "描述你的拜访场景",
    placeholder="例如：明天拜访一家制造业客户，他们的产线刚遭受勒索软件攻击",
    height=100,
)

# Quick-fill examples
if st.button("填入示例"):
    user_input = "明天拜访一家制造业客户，他们的产线刚遭受勒索软件攻击"
    st.rerun()

# Industry quick tags
st.markdown("**行业快捷标签：**")
cols = st.columns(3)
industries = {
    "制造业": "manufacturing",
    "金融": "finance",
    "医疗": "healthcare",
}
for col, (label, eng) in zip(cols, industries.items()):
    if col.button(label):
        user_input = f"拜访一家{label}客户，讨论安全挑战"

st.divider()

# ---------------------------------------------------------------------------
# Generate button
# ---------------------------------------------------------------------------
if st.button("生成 Prep 包", type="primary", disabled=not user_input):
    if not _IMPORTS_OK:
        st.error(f"模块导入失败：{_IMPORT_ERROR}")
    else:
        with st.spinner("正在生成 Prep 包…"):
            try:
                # Load knowledge base
                kb = load_all()

                # Recognize intent
                intent = recognize(user_input)
                st.info(f"识别结果：行业={intent.industry}，场景={intent.scenario}")

                # Try LLM generation, fallback to rules
                fallback_used = False
                try:
                    pkg = generate_prep(intent, kb)
                except LLMUnavailableError as e:
                    st.warning(f"已切换为基础模式（{e}）")
                    pkg = generate_prep_fallback(intent, kb)
                    fallback_used = True

                # Enrich with threat intel
                pkg.threat_intel = fetch_threats(intent.industry)

                # Persist in session state so other interactions can reuse
                st.session_state["pkg"] = pkg

                st.success(
                    "Prep 包已生成！"
                    + ("（基础模式）" if fallback_used else "")
                )

            except Exception as e:
                st.error(f"生成出错：{e}")

# ---------------------------------------------------------------------------
# Render results (from freshly generated or previously cached session state)
# ---------------------------------------------------------------------------
pkg = st.session_state.get("pkg")

if pkg is not None:
    with st.expander("场景判断", expanded=True):
        st.markdown(pkg.scenario_assessment)

    with st.expander("敏感度提醒"):
        for alert in pkg.sensitivity_alerts:
            st.markdown(f"- {alert}")

    with st.expander("案例匹配"):
        if pkg.matched_cases:
            for case_id in pkg.matched_cases:
                st.markdown(f"- `{case_id}`")
        else:
            st.markdown("_未匹配到具体案例_")

    with st.expander("追问清单"):
        for q in pkg.follow_up_questions:
            st.markdown(f"- {q}")

    with st.expander("方案方向"):
        st.markdown(pkg.solution_direction)

    with st.expander("话术要点"):
        st.markdown(pkg.talking_points)

    if pkg.threat_intel:
        with st.expander("威胁情报"):
            for event in pkg.threat_intel:
                st.markdown(f"**{event.title}** ({event.date})")
                st.markdown(event.description)
                if event.source_url:
                    st.markdown(f"[来源]({event.source_url})")

    # ------------------------------------------------------------------
    # PPT Outline section
    # ------------------------------------------------------------------
    st.divider()
    st.markdown("### PPT 大纲")

    if st.button("生成 PPT 大纲"):
        try:
            outline = generate_outline(pkg)
            st.session_state["ppt_outline"] = outline
        except Exception as e:
            st.error(f"生成 PPT 大纲失败：{e}")

    outline = st.session_state.get("ppt_outline")
    if outline:
        st.markdown(outline)
        st.code(outline, language="markdown")

        st.download_button(
            label="下载 PPT 大纲 (.md)",
            data=outline.encode("utf-8"),
            file_name="prep_outline.md",
            mime="text/markdown",
        )
