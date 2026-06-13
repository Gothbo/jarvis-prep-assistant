"""Knowledge Base browsing page — explore cases, methodologies, sensitivities, products."""

import streamlit as st

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
try:
    from jarvis.knowledge.loader import load_all, KnowledgeBase

    _IMPORTS_OK = True
except Exception as _import_err:
    _IMPORTS_OK = False
    _IMPORT_ERROR = _import_err

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="JARVIS - 知识库",
    page_icon="📚",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
.kb-card {
    background: white; border: 1px solid #e2e8f0; border-radius: 14px;
    padding: 24px 28px; margin-bottom: 14px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    transition: border-color 0.2s, box-shadow 0.2s;
}
.kb-card:hover { border-color: #6366f1; box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
.kb-card h4 { font-size: 15px; font-weight: 600; margin-bottom: 6px; }
.kb-card p { font-size: 13px; color: #64748b; line-height: 1.6; margin: 0; }
.kb-tag {
    display: inline-block; padding: 2px 10px; border-radius: 7px;
    font-size: 11px; font-weight: 500; margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## JARVIS 知识库")
    st.markdown("浏览案例、方法论、行业敏感度和产品数据")
    st.divider()

    if _IMPORTS_OK:
        try:
            kb = load_all()
            st.metric("案例", len(kb.cases))
            st.metric("方法论", len(kb.methodologies))
            st.metric("敏感度规则", len(kb.sensitivities))
            st.metric("产品", len(kb.products))
        except Exception:
            st.caption("知识库加载失败")
    else:
        st.caption("模块导入失败")

    st.divider()
    st.caption("JARVIS v0.3 · Knowledge Base")

# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------
st.title("📚 知识库")
st.markdown("浏览和搜索 JARVIS 内置的行业知识库，包含案例研究、销售方法论、行业敏感度分析和产品资料。")
st.divider()

if not _IMPORTS_OK:
    st.error(f"模块导入失败：{_IMPORT_ERROR}")
    st.stop()

try:
    kb: KnowledgeBase = load_all()
except Exception as e:
    st.error(f"知识库加载失败：{e}")
    st.stop()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_cases, tab_methods, tab_sens, tab_products = st.tabs(
    ["案例研究", "方法论", "行业敏感度", "产品"]
)

# ── Cases ──────────────────────────────────────────────────────────────────
with tab_cases:
    search_case = st.text_input(
        "搜索案例", placeholder="输入关键词...", key="search_case",
        label_visibility="collapsed",
    )

    total = len(kb.cases)
    cases = kb.cases
    if search_case:
        sl = search_case.lower()
        cases = [
            c for c in cases
            if sl in c.id.lower()
            or sl in c.industry.lower()
            or sl in c.scenario.lower()
            or sl in c.pain_points.surface.lower()
            or sl in c.pain_points.deep.lower()
        ]

    st.caption(f"共 {len(cases)} / {total} 条案例")

    for case in cases:
        tag_bg = "#e0e7ff" if case.industry == "finance" else ("#d1fae5" if case.industry == "healthcare" else "#fef3c7")
        tag_fg = "#4338ca" if case.industry == "finance" else ("#065f46" if case.industry == "healthcare" else "#92400e")

        with st.expander(f"**{case.id}** — {case.industry} / {case.scenario}", expanded=False):
            st.markdown(f"""
<span class="kb-tag" style="background:{tag_bg};color:{tag_fg};">{case.industry}</span>
<span class="kb-tag" style="background:#f1f5f9;color:#475569;margin-left:4px;">{case.scenario}</span>
""", unsafe_allow_html=True)

            st.markdown("**表面痛点**")
            st.markdown(case.pain_points.surface)

            st.markdown("**深层痛点**")
            st.markdown(case.pain_points.deep)

            st.markdown("**解决方案**")
            st.markdown(f"- 方法: {case.solution.method}")
            st.markdown(f"- 产品: {case.solution.product}")
            for i, phase in enumerate(case.solution.phases, 1):
                st.markdown(f"- 阶段 {i}: {phase}")

            st.markdown("**话术要点**")
            st.markdown(f"- 开场: {case.talking_points.opening}")
            st.markdown(f"- 共情: {case.talking_points.empathy}")
            st.markdown(f"- 锚定: {case.talking_points.anchoring}")

            st.markdown("**追问清单**")
            for q in case.follow_up_questions:
                st.markdown(f"- [{q.dimension}] {q.question}")

            if case.reference_event:
                st.markdown("**参考事件**")
                st.info(case.reference_event)

# ── Methodologies ──────────────────────────────────────────────────────────
with tab_methods:
    st.caption(f"共 {len(kb.methodologies)} 个方法论")

    for method in kb.methodologies:
        with st.expander(f"**{method.name}** — {method.description}", expanded=False):
            scenarios = ", ".join(method.applicable_scenarios)
            industries = ", ".join(method.industry_match) if method.industry_match else "通用"
            st.markdown(f"- 适用场景: {scenarios}")
            st.markdown(f"- 适用行业: {industries}")

            st.markdown("**步骤**")
            for step in method.steps:
                st.markdown(f"**{step.order}. {step.title}** — {step.description}")
                for action in step.key_actions:
                    st.markdown(f"  - {action}")

# ── Sensitivities ──────────────────────────────────────────────────────────
with tab_sens:
    search_sens = st.text_input(
        "搜索敏感度", placeholder="输入行业...", key="search_sens",
        label_visibility="collapsed",
    )

    sensitivities = kb.sensitivities
    if search_sens:
        sl = search_sens.lower()
        sensitivities = [
            s for s in sensitivities
            if sl in s.industry.lower()
            or sl in s.primary_sensitivity.lower()
        ]

    st.caption(f"共 {len(sensitivities)} 个行业敏感度规则")

    for sens in sensitivities:
        with st.expander(f"**{sens.industry}** — {sens.primary_sensitivity}", expanded=False):
            st.markdown(f"**主要敏感度**: {sens.primary_sensitivity}")

            if sens.secondary_sensitivities:
                st.markdown("**次要敏感度**")
                for s in sens.secondary_sensitivities:
                    st.markdown(f"- {s}")

            st.markdown("**雷区（绝对避免）**")
            for lm in sens.landmines:
                st.markdown(f"- {lm}")

            if sens.empathy_phrases:
                st.markdown("**共情话术**")
                for ep in sens.empathy_phrases:
                    st.markdown(f"> {ep}")

# ── Products ───────────────────────────────────────────────────────────────
with tab_products:
    st.caption(f"共 {len(kb.products)} 个产品")

    for prod in kb.products:
        with st.expander(f"**{prod.name}** — {prod.category}", expanded=False):
            st.markdown(prod.description)

            if prod.key_features:
                st.markdown("**核心特性**")
                for f in prod.key_features:
                    st.markdown(f"- {f}")

            industries = ", ".join(prod.applicable_industries) if prod.applicable_industries else "通用"
            scenarios = ", ".join(prod.applicable_scenarios) if prod.applicable_scenarios else "通用"
            st.markdown(f"- 适用行业: {industries}")
            st.markdown(f"- 适用场景: {scenarios}")
