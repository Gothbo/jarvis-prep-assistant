"""Smart Prep page — Redesigned with design system.

Features:
- Template selection + free input (5 scenarios, 7 industries)
- Step progress bar (4 steps)
- Sectioned result cards (core prep / reference / threat intel)
- Export toolbar (PPT outline)
"""

import streamlit as st

from jarvis.config import load_config
from jarvis.ui.icons import icon
from jarvis.ui.styles import (
    badge,
    inject_css,
    result_section,
    section_header,
    step_item,
)

load_config()

# ---------------------------------------------------------------------------
# Imports (wrapped for graceful degradation)
# ---------------------------------------------------------------------------
try:
    from jarvis.engine.intent import recognize
    from jarvis.engine.hybrid_engine import generate_prep_hybrid
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
    page_icon="../favicon.svg",
    layout="wide",
)
inject_css()

# Prep page: transparent button overlay on template card columns only.
# Strategy: template buttons have help="tpl" which wraps them in
# <div class="stTooltipIcon"> — a unique CSS hook. Industry buttons and
# the generate button have no help param, so :has(.stTooltipIcon) targets
# ONLY the template card columns.
st.markdown(
    """
<style>
div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:has(.stTooltipIcon) {
    position: relative;
    gap: 0 !important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:has(.stTooltipIcon)
    div[data-testid="element-container"]:has(.stTooltipIcon) {
    position: absolute; inset: 0; z-index: 10;
    margin: 0 !important; padding: 0 !important; height: 100% !important;
}
div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:has(.stTooltipIcon)
    button {
    position: absolute; inset: 0;
    width: 100% !important; height: 100% !important;
    opacity: 0 !important; background: transparent !important;
    border: none !important; box-shadow: none !important;
    cursor: pointer !important; margin: 0 !important; padding: 0 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;padding:8px 0;">'
        f'{icon("shield_check", size=28, color="var(--jarvis-primary)")}'
        f'<span style="font-size:20px;font-weight:700;color:var(--jarvis-text);">JARVIS</span>'
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-size:13px;color:var(--jarvis-text-secondary);margin-top:-8px;">AI 驱动的销售拜访准备助手</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("### 知识库概览")
    try:
        _kb = load_all()
        c1, c2 = st.columns(2)
        c1.metric("案例", len(_kb.cases))
        c2.metric("方法论", len(_kb.methodologies))
        c3, c4 = st.columns(2)
        c3.metric("敏感度", len(_kb.sensitivities))
        c4.metric("产品", len(_kb.products))
    except Exception:
        st.caption("知识库加载失败，请检查数据目录。")

    st.divider()
    st.caption("JARVIS v0.3 · Prep Assistant")

# ---------------------------------------------------------------------------
# Page Header
# ---------------------------------------------------------------------------
st.markdown(
    f"""
<div style="display:flex;align-items:center;gap:12px;padding:8px 0 4px;">
    {icon("shield_check", size=32, color="var(--jarvis-primary)")}
    <div>
        <h2 style="margin:0;font-size:24px;font-weight:700;color:var(--jarvis-text);">智能 Prep</h2>
        <p style="margin:4px 0 0;font-size:14px;color:var(--jarvis-text-secondary);">为你的客户拜访生成结构化 Prep 包</p>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

st.divider()

# ---------------------------------------------------------------------------
# Template Selection
# ---------------------------------------------------------------------------
st.markdown(
    f'<p class="jarvis-section-label">'
    f'{icon("compass", size=16, color="var(--jarvis-primary)")} 选择场景模板或自由描述</p>',
    unsafe_allow_html=True,
)

TEMPLATES = [
    {
        "key": "manufacturing_ransomware",
        "title": "制造业 · 勒索事件",
        "desc": "产线遭受勒索软件攻击",
        "text": "明天拜访一家制造业客户，他们的产线刚遭受勒索软件攻击",
    },
    {
        "key": "finance_compliance",
        "title": "金融 · 合规建设",
        "desc": "等保 2.0 合规方案",
        "text": "拜访一家城商行客户，讨论等保 2.0 合规建设方案",
    },
    {
        "key": "healthcare_breach",
        "title": "医疗 · 数据泄露",
        "desc": "患者数据泄露事件",
        "text": "拜访一家三甲医院，他们近期发生了患者数据泄露事件",
    },
    {
        "key": "government_security",
        "title": "政府 · 等保三级",
        "desc": "政务系统安全建设",
        "text": "拜访某市教育局，讨论政务系统等保三级建设方案",
    },
    {
        "key": "custom",
        "title": "自由输入",
        "desc": "自定义拜访场景",
        "text": "",
    },
]

template_cols = st.columns(5, gap="medium")
selected_template = st.session_state.get("selected_template", "")

for i, (col, tmpl) in enumerate(zip(template_cols, TEMPLATES)):
    with col:
        is_active = selected_template == tmpl["key"]
        active_class = " active" if is_active else ""
        st.markdown(
            f"""
<div class="jarvis-template{active_class}">
    <h5>{tmpl["title"]}</h5>
    <p>{tmpl["desc"]}</p>
</div>
""",
            unsafe_allow_html=True,
        )
        # Transparent overlay button — help="tpl" wraps it in
        # <div class="stTooltipIcon">, giving CSS a unique selector hook.
        # The overlay CSS makes it invisible and stretched over the card.
        if st.button(
            tmpl["title"],
            key=f"tmpl_{tmpl['key']}",
            use_container_width=True,
            help="tpl",
        ):
            st.session_state["selected_template"] = tmpl["key"]
            st.session_state["prep_input"] = tmpl["text"]
            st.rerun()

# ---------------------------------------------------------------------------
# Input Area
# ---------------------------------------------------------------------------
st.markdown(
    f'<p class="jarvis-section-label">'
    f'{icon("target", size=16, color="var(--jarvis-primary)")} 描述拜访场景</p>',
    unsafe_allow_html=True,
)

default_text = st.session_state.get("prep_input", "")
user_input = st.text_area(
    "描述拜访场景",
    value=default_text,
    placeholder="例如：明天拜访一家制造业客户，他们的产线刚遭受勒索软件攻击",
    height=120,
    label_visibility="collapsed",
)
# Sync template selection with text area changes
if user_input != default_text:
    st.session_state["prep_input"] = user_input
    st.session_state["selected_template"] = "custom"

# Industry quick tags
st.markdown(
    f'<p class="jarvis-section-label">'
    f'{icon("database", size=16, color="var(--jarvis-primary)")} 快速选择行业</p>',
    unsafe_allow_html=True,
)

industry_cols = st.columns(7, gap="small")
industries = ["制造业", "金融", "医疗", "政府", "教育", "能源", "零售"]
for col, label in zip(industry_cols, industries):
    with col:
        if st.button(label, key=f"ind_{label}", use_container_width=True):
            st.session_state["prep_input"] = f"拜访一家{label}客户，讨论安全挑战"
            st.session_state["selected_template"] = "custom"
            st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Generate Button
# ---------------------------------------------------------------------------
gen_left, gen_center, gen_right = st.columns([1, 2, 1])
with gen_center:
    generate_clicked = st.button(
        "生成 Prep 包",
        type="primary",
        disabled=not user_input,
        use_container_width=True,
    )

if generate_clicked:
    if not _IMPORTS_OK:
        st.error(f"模块导入失败：{_IMPORT_ERROR}")
    else:
        # Use st.status for step-by-step progress
        with st.status("正在生成 Prep 包…", expanded=True) as status:

            # Step 1: Intent recognition
            st.write(
                f"{icon('lightning', size=14, color='var(--jarvis-primary)')} 识别行业与场景…"
            )
            try:
                kb = load_all()
                intent = recognize(user_input)
                st.write(
                    f"    行业={intent.industry}，场景={intent.scenario}"
                )
            except Exception as e:
                status.update(label="意图识别失败", state="error")
                st.error(f"意图识别出错：{e}")
                st.stop()

            # Step 2: Knowledge retrieval
            st.write(
                f"{icon('database', size=14, color='var(--jarvis-primary)')} 检索知识库…"
            )
            matched_count = "匹配中"
            try:
                # Pre-check to show count
                st.write(f"    知识库已加载（{len(kb.cases)} 案例）")
            except Exception:
                pass

            # Step 3: Generate Prep package (hybrid: rule + LLM in parallel)
            st.write(
                f"{icon('rocket', size=14, color='var(--jarvis-primary)')} 双引擎并行生成…"
            )
            try:
                pkg, engine_mode = generate_prep_hybrid(intent, kb, llm_timeout=30.0)
                if engine_mode == "hybrid":
                    st.write("    规则引擎 + LLM 融合完成")
                else:
                    st.warning("    LLM 不可用，已使用规则引擎生成结果")
            except Exception as e:
                status.update(label="生成失败", state="error")
                st.error(f"生成出错：{e}")
                st.stop()

            # Step 4: Threat intel
            st.write(
                f"{icon('magnifying_glass', size=14, color='var(--jarvis-primary)')} 拉取威胁情报…"
            )
            try:
                pkg.threat_intel = fetch_threats(intent.industry)
                threat_count = len(pkg.threat_intel) if pkg.threat_intel else 0
                st.write(f"    获取到 {threat_count} 条威胁事件")
            except Exception:
                pkg.threat_intel = []
                st.write("    威胁情报暂不可用")

            # Save to session
            st.session_state["pkg"] = pkg
            st.session_state["engine_mode"] = engine_mode

            label = "Prep 包已生成"
            if engine_mode == "hybrid":
                label += "（双引擎融合）"
            else:
                label += "（规则引擎）"
            status.update(label=label, state="complete")

# ---------------------------------------------------------------------------
# Render Results
# ---------------------------------------------------------------------------
pkg = st.session_state.get("pkg")

if pkg is not None:
    engine_mode = st.session_state.get("engine_mode", "rule_only")

    # Export toolbar (top-right)
    toolbar_col1, toolbar_col2, toolbar_col3 = st.columns([6, 1, 1])
    with toolbar_col2:
        if st.button(
            f"  PPT 大纲",
            key="btn_ppt_toolbar",
            use_container_width=True,
            help="生成 PPT 演示大纲",
        ):
            try:
                outline = generate_outline(pkg)
                st.session_state["ppt_outline"] = outline
            except Exception as e:
                st.error(f"PPT 大纲生成失败：{e}")
    with toolbar_col3:
        outline = st.session_state.get("ppt_outline")
        if outline:
            st.download_button(
                f"  下载 .md",
                data=outline.encode("utf-8"),
                file_name="prep_outline.md",
                mime="text/markdown",
                key="btn_download_outline",
                use_container_width=True,
            )

    # Engine mode badge
    if engine_mode == "hybrid":
        st.success(
            f" {badge('双引擎融合', 'success')}  规则引擎 + LLM 联合生成，结果已融合优化。"
        )
    else:
        st.warning(
            f" {badge('规则引擎', 'warning')}  LLM 不可用，已使用规则引擎生成结果。"
        )

    st.markdown("---")

    # ── Section 1: Core Prep (expanded) ────────────────────────────────
    core_content = f"""
<div style="margin-bottom:16px;">
    <p style="font-size:13px;font-weight:600;color:var(--jarvis-text-secondary);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">场景判断</p>
    <p style="font-size:14px;line-height:1.7;color:var(--jarvis-text);">{pkg.scenario_assessment}</p>
</div>
<div style="margin-bottom:16px;">
    <p style="font-size:13px;font-weight:600;color:var(--jarvis-text-secondary);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">方案方向</p>
    <p style="font-size:14px;line-height:1.7;color:var(--jarvis-text);">{pkg.solution_direction}</p>
</div>
<div>
    <p style="font-size:13px;font-weight:600;color:var(--jarvis-text-secondary);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">话术要点</p>
    <p style="font-size:14px;line-height:1.7;color:var(--jarvis-text);">{pkg.talking_points}</p>
</div>
"""
    st.markdown(
        result_section("核心准备", "target", core_content),
        unsafe_allow_html=True,
    )

    # ── Section 1b: Solution Outline (expanded) ────────────────────────
    if pkg.solution_outline:
        outline_items = ""
        for idx, step in enumerate(pkg.solution_outline, 1):
            outline_items += (
                f'<div style="display:flex;gap:12px;align-items:flex-start;'
                f'margin-bottom:12px;padding:10px 14px;'
                f'background:var(--jarvis-bg);border-radius:8px;'
                f'border-left:3px solid var(--jarvis-primary);">'
                f'<span style="font-size:13px;font-weight:700;color:var(--jarvis-primary);'
                f'min-width:20px;padding-top:1px;">{idx}</span>'
                f'<span style="font-size:14px;line-height:1.6;color:var(--jarvis-text);">{step}</span>'
                f"</div>"
            )
        outline_content = f'<div style="padding:4px 0;">{outline_items}</div>'
        st.markdown(
            result_section("方案框架", "presentation", outline_content),
            unsafe_allow_html=True,
        )

    # ── Section 2: Reference Materials (collapsed by default) ──────────
    with st.expander(
        f"  参考素材",
        expanded=False,
    ):
        # Cases
        st.markdown("**案例匹配**")
        if pkg.matched_cases:
            for case_id in pkg.matched_cases:
                st.markdown(f"- `{case_id}`")
        else:
            st.caption("未匹配到具体案例，尝试更换行业标签或更通用的关键词。")

        # Follow-up questions
        st.markdown("**追问清单**")
        for q in pkg.follow_up_questions:
            st.markdown(f"- {q}")

        # Sensitivity alerts
        st.markdown("**敏感度提醒**")
        for alert in pkg.sensitivity_alerts:
            st.markdown(f"- {alert}")

    # ── Section 3: Threat Intelligence (collapsed by default) ──────────
    if pkg.threat_intel:
        threat_badge = badge(f"{len(pkg.threat_intel)} 条", "danger")
        with st.expander(
            f"  威胁情报  {threat_badge}",
            expanded=False,
        ):
            for event in pkg.threat_intel:
                st.markdown(f"**{event.title}** ({event.date})")
                st.markdown(event.description)
                if event.source_url:
                    st.markdown(f"[来源]({event.source_url})")
                st.divider()

    # ── PPT Outline (if generated) ─────────────────────────────────────
    outline = st.session_state.get("ppt_outline")
    if outline:
        with st.expander("  PPT 大纲预览", expanded=True):
            st.markdown(outline)
