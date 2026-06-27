"""Knowledge Base browsing page -- explore cases, methodologies, sensitivities, products."""

import streamlit as st

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
try:
    from jarvis.engine.training import INDUSTRY_LABELS
    from jarvis.knowledge.loader import KnowledgeBase, load_all
    from jarvis.search.fulltext import SearchResult, search_knowledge_base
    from jarvis.ui.icons import icon
    from jarvis.ui.styles import inject_css

    _IMPORTS_OK = True
except Exception as _import_err:
    _IMPORTS_OK = False
    _IMPORT_ERROR = _import_err

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="JARVIS - 知识库",
    page_icon="../favicon.svg",
    layout="wide",
)
if _IMPORTS_OK:
    inject_css()

# Page-specific CSS
st.markdown("""
<style>
/* -- Search area wrapper -- */
.kb-search-card {
    background: var(--jarvis-surface);
    border: 1px solid var(--jarvis-border);
    border-radius: var(--radius-md);
    padding: 20px 24px;
    margin-bottom: 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

/* -- Search input styling -- */
div[data-testid="stTextInput"] input {
    border: 1.5px solid var(--jarvis-border) !important;
    border-radius: 10px !important;
    padding: 10px 16px !important;
    font-size: 14px !important;
    transition: border-color 200ms ease, box-shadow 200ms ease !important;
}
div[data-testid="stTextInput"] input:focus {
    border-color: var(--jarvis-primary) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.1) !important;
}

/* -- Tab styling -- */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: var(--jarvis-background);
    border-radius: 12px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 500;
    color: var(--jarvis-text-secondary);
    background: transparent;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    color: var(--jarvis-primary) !important;
    font-weight: 600;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.stTabs [data-baseweb="tab-highlight"] {
    display: none;
}
.stTabs [data-baseweb="tab-border"] {
    display: none;
}

/* -- Expander styling -- */
.streamlit-expanderHeader {
    font-size: 14px !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
}
.streamlit-expanderHeader:hover {
    background: var(--jarvis-background) !important;
}

/* -- Category tag styling -- */
.kb-category-label {
    font-size: 14px;
    font-weight: 600;
    color: var(--jarvis-text);
    margin: 12px 0 8px 0;
    display: flex;
    align-items: center;
    gap: 8px;
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
st.markdown(
    f"""
<div style="display:flex;align-items:center;gap:12px;padding:8px 0 4px;">
    {icon("database", size=32, color="var(--jarvis-primary)")}
    <div>
        <h2 style="margin:0;font-size:24px;font-weight:700;color:var(--jarvis-text);">知识库</h2>
        <p style="margin:4px 0 0;font-size:14px;color:var(--jarvis-text-secondary);">浏览和搜索 JARVIS 内置的行业知识库，包含案例研究、销售方法论、行业敏感度分析和产品资料</p>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

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
# Unified search section
# ---------------------------------------------------------------------------
_TYPE_LABELS: dict[str, str] = {
    "cases": "案例",
    "methodologies": "方法论",
    "sensitivities": "敏感度",
    "products": "产品",
}

_TYPE_TAG_COLORS: dict[str, tuple[str, str]] = {
    "cases": ("#e0e7ff", "#4338ca"),
    "methodologies": ("#fef3c7", "#92400e"),
    "sensitivities": ("#fce7f3", "#9d174d"),
    "products": ("#d1fae5", "#065f46"),
}

st.markdown(
    f'<p class="kb-category-label">{icon("magnifying_glass", size=16, color="var(--jarvis-primary)")} 搜索知识库</p>',
    unsafe_allow_html=True,
)

with st.container():
    search_query = st.text_input(
        "全局搜索",
        placeholder="输入关键词搜索全部知识库...",
        key="kb_global_search",
        label_visibility="collapsed",
    )

    col_cat, col_ind, _spacer = st.columns([1, 1, 3])
    with col_cat:
        cat_opt = st.selectbox(
            "类型",
            ["全部", "案例", "方法论", "敏感度", "产品"],
            key="kb_search_cat",
        )
    with col_ind:
        ind_opt = st.selectbox(
            "行业",
            ["全部", *INDUSTRY_LABELS.values()],
            key="kb_search_ind",
        )

    _CAT_MAP: dict[str, str | None] = {
        "全部": None,
        "案例": "cases",
        "方法论": "methodologies",
        "敏感度": "sensitivities",
        "产品": "products",
    }
    _IND_MAP: dict[str, str | None] = {
        "全部": None,
        **{v: k for k, v in INDUSTRY_LABELS.items()},
    }

    search_category = _CAT_MAP.get(cat_opt)
    search_industry = _IND_MAP.get(ind_opt)

    # Execute search
    search_results: list[SearchResult] = []
    if search_query:
        search_results = search_knowledge_base(
            kb,
            search_query,
            category=search_category,
            industry=search_industry,
        )

show_search = bool(search_query)

# ---------------------------------------------------------------------------
# Search results view
# ---------------------------------------------------------------------------
if show_search:
    st.markdown(f"### 搜索结果 ({len(search_results)} 条)")

    if not search_results:
        st.warning("未找到匹配的内容，请尝试其他关键词或调整筛选条件。")
    else:
        for result in search_results:
            tag_bg, tag_fg = _TYPE_TAG_COLORS.get(result.type, ("#f1f5f9", "#475569"))
            type_label = _TYPE_LABELS.get(result.type, result.type)

            with st.expander(result.title, expanded=False):
                st.markdown(
                    f'<span class="kb-tag" style="background:{tag_bg};color:{tag_fg};">'
                    f"{type_label}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(result.snippet, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tab browsing view (when no search is active)
# ---------------------------------------------------------------------------
else:
    tab_cases, tab_methods, tab_sens, tab_products = st.tabs(
        ["案例研究", "方法论", "行业敏感度", "产品"]
    )

    # -- Cases ---------------------------------------------------------------
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
            tag_bg = (
                "#e0e7ff" if case.industry == "finance"
                else ("#d1fae5" if case.industry == "healthcare" else "#fef3c7")
            )
            tag_fg = (
                "#4338ca" if case.industry == "finance"
                else ("#065f46" if case.industry == "healthcare" else "#92400e")
            )

            with st.expander(
                f"**{case.id}** -- {case.industry} / {case.scenario}", expanded=False,
            ):
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

    # -- Methodologies -------------------------------------------------------
    with tab_methods:
        st.caption(f"共 {len(kb.methodologies)} 个方法论")

        for method in kb.methodologies:
            with st.expander(
                f"**{method.name}** -- {method.description}", expanded=False,
            ):
                scenarios = ", ".join(method.applicable_scenarios)
                industries = (
                    ", ".join(method.industry_match) if method.industry_match else "通用"
                )
                st.markdown(f"- 适用场景: {scenarios}")
                st.markdown(f"- 适用行业: {industries}")

                st.markdown("**步骤**")
                for step in method.steps:
                    st.markdown(f"**{step.order}. {step.title}** -- {step.description}")
                    for action in step.key_actions:
                        st.markdown(f"  - {action}")

    # -- Sensitivities -------------------------------------------------------
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
            with st.expander(
                f"**{sens.industry}** -- {sens.primary_sensitivity}", expanded=False,
            ):
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

    # -- Products ------------------------------------------------------------
    with tab_products:
        st.caption(f"共 {len(kb.products)} 个产品")

        for prod in kb.products:
            with st.expander(f"**{prod.name}** -- {prod.category}", expanded=False):
                st.markdown(prod.description)

                if prod.key_features:
                    st.markdown("**核心特性**")
                    for f in prod.key_features:
                        st.markdown(f"- {f}")

                industries = (
                    ", ".join(prod.applicable_industries)
                    if prod.applicable_industries
                    else "通用"
                )
                scenarios = (
                    ", ".join(prod.applicable_scenarios)
                    if prod.applicable_scenarios
                    else "通用"
                )
                st.markdown(f"- 适用行业: {industries}")
                st.markdown(f"- 适用场景: {scenarios}")
