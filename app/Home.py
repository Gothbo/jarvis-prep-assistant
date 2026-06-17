"""JARVIS - Streamlit Home Page."""

import streamlit as st

from jarvis.auth import password_gate
from jarvis.config import load_config

load_config()

st.set_page_config(
    page_title="JARVIS - 智能 Prep 助手",
    page_icon="🛡️",
    layout="wide",
)

password_gate()

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
.hero-section {
    text-align: center;
    padding: 40px 20px 30px;
}
.feature-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 24px;
    text-align: center;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.feature-card:hover {
    border-color: #6366f1;
    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
}
.feature-icon {
    font-size: 36px;
    margin-bottom: 12px;
}
.nav-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 20px 24px;
    cursor: pointer;
    transition: all 0.2s;
}
.nav-card:hover {
    border-color: #6366f1;
    box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    transform: translateY(-2px);
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## JARVIS")
    st.markdown("AI 驱动的销售拜访准备助手")
    st.divider()

    st.markdown("### 快速导航")
    if st.button("🛡️  智能 Prep", use_container_width=True):
        st.switch_page("pages/1_智能Prep.py")
    if st.button("🎭  模拟训练", use_container_width=True):
        st.switch_page("pages/2_模拟训练.py")
    if st.button("📚  知识库", use_container_width=True):
        st.switch_page("pages/3_知识库.py")

    st.divider()

    # Quick KB stats
    st.markdown("### 知识库概览")
    try:
        from jarvis.knowledge.loader import load_all
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
# Hero section
# ---------------------------------------------------------------------------
st.markdown("""
<div class="hero-section">
<h1 style="font-size:42px; font-weight:800; margin-bottom:8px;">🛡️ JARVIS</h1>
<p style="font-size:18px; color:#64748b; margin-bottom:4px;">
AI 驱动的销售拜访准备助手
</p>
<p style="font-size:14px; color:#94a3b8;">
融合行业知识库、威胁情报和 AI 洞察，为客户拜访做好充分准备
</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# Feature cards
# ---------------------------------------------------------------------------
st.markdown("### 核心功能")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
<div class="feature-card">
<div class="feature-icon">🛡️</div>
<h4>智能 Prep</h4>
<p style="font-size:13px;color:#64748b;">
场景识别 · 意图分析<br>
自动匹配行业案例<br>
敏感度提醒与话术建议
</p>
</div>
""", unsafe_allow_html=True)

with col2:
    st.markdown("""
<div class="feature-card">
<div class="feature-icon">🎭</div>
<h4>模拟训练</h4>
<p style="font-size:13px;color:#64748b;">
AI 客户角色扮演<br>
多轮对话练习<br>
五维评分报告
</p>
</div>
""", unsafe_allow_html=True)

with col3:
    st.markdown("""
<div class="feature-card">
<div class="feature-icon">📚</div>
<h4>知识库</h4>
<p style="font-size:13px;color:#64748b;">
YAML 驱动模块化知识库<br>
案例 / 方法论 / 产品<br>
搜索与筛选
</p>
</div>
""", unsafe_allow_html=True)

with col4:
    st.markdown("""
<div class="feature-card">
<div class="feature-icon">🔍</div>
<h4>威胁情报</h4>
<p style="font-size:13px;color:#64748b;">
实时行业威胁事件<br>
安全态势感知<br>
风险预判与来源追溯
</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# Quick actions
# ---------------------------------------------------------------------------
st.markdown("### 快速开始")

nav1, nav2, nav3 = st.columns(3)

with nav1:
    st.markdown("""
<div class="nav-card">
<h4>🛡️ 智能 Prep</h4>
<p style="font-size:13px;color:#64748b;">
为你的下一次客户拜访生成完整的 Prep 包，包含场景评估、敏感度提醒、
追问清单和话术要点。
</p>
</div>
""", unsafe_allow_html=True)
    if st.button("开始准备 →", key="btn_prep", use_container_width=True):
        st.switch_page("pages/1_智能Prep.py")

with nav2:
    st.markdown("""
<div class="nav-card">
<h4>🎭 模拟训练</h4>
<p style="font-size:13px;color:#64748b;">
与 AI 客户进行角色扮演训练，练习需求挖掘、异议处理
和方案呈现技巧，获取五维评分报告。
</p>
</div>
""", unsafe_allow_html=True)
    if st.button("开始训练 →", key="btn_train", use_container_width=True):
        st.switch_page("pages/2_模拟训练.py")

with nav3:
    st.markdown("""
<div class="nav-card">
<h4>📚 知识库</h4>
<p style="font-size:13px;color:#64748b;">
浏览案例研究、销售方法论、行业敏感度分析和产品资料，
支持关键词搜索和分类筛选。
</p>
</div>
""", unsafe_allow_html=True)
    if st.button("浏览知识库 →", key="btn_kb", use_container_width=True):
        st.switch_page("pages/3_知识库.py")

st.divider()

# ---------------------------------------------------------------------------
# Tech stack
# ---------------------------------------------------------------------------
with st.expander("技术架构"):
    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        st.markdown("**知识引擎**")
        st.markdown("- YAML 数据驱动")
        st.markdown("- Pydantic v2 验证")
        st.markdown("- jieba 中文分词")
    with tc2:
        st.markdown("**生成引擎**")
        st.markdown("- LLM (OpenAI) 主生成")
        st.markdown("- 规则引擎兜底")
        st.markdown("- JSON 结构化输出")
    with tc3:
        st.markdown("**情报引擎**")
        st.markdown("- 实时威胁事件抓取")
        st.markdown("- 行业关联分析")
        st.markdown("- 来源链接追溯")
