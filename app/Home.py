"""JARVIS - Streamlit Home Page (Redesigned).

Design: Hero + 4 clickable entry cards, brand-quality visual style.
"""

import streamlit as st

from jarvis.auth import password_gate
from jarvis.config import load_config
from jarvis.ui.icons import icon
from jarvis.ui.styles import card, inject_css

load_config()

st.set_page_config(
    page_title="JARVIS - 智能 Prep 助手",
    page_icon="🛡️",
    layout="wide",
)

password_gate()
inject_css()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:10px;padding:8px 0;">'
        f'{icon("shield_check", size=28, color="#6366f1")}'
        f'<span style="font-size:20px;font-weight:700;color:#1e293b;">JARVIS</span>'
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-size:13px;color:#64748b;margin-top:-8px;">AI 驱动的销售拜访准备助手</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    # Knowledge base stats
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
hero_icon = icon("shield_check", size=48, color="#6366f1")

st.markdown(
    f"""
<div style="text-align:center; padding:48px 20px 32px;">
    <div style="margin-bottom:12px;">{hero_icon}</div>
    <h1 style="font-size:36px; font-weight:800; margin-bottom:8px; color:#1e293b;">
        JARVIS
    </h1>
    <p style="font-size:18px; color:#64748b; margin-bottom:4px;">
        AI 驱动的销售拜访准备助手
    </p>
    <p style="font-size:14px; color:#94a3b8;">
        融合行业知识库、威胁情报和 AI 洞察，为客户拜访做好充分准备
    </p>
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 4 Entry Cards
# ---------------------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4, gap="medium")

with col1:
    st.markdown(
        card(
            title="智能 Prep",
            description="为你的客户拜访生成结构化 Prep 包：场景评估、敏感度提醒、追问清单和话术要点。",
            icon_name="shield_check",
            link_text="开始准备 →",
        ),
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        card(
            title="模拟训练",
            description="与 AI 客户进行角色扮演训练，练习需求挖掘和方案呈现，获取五维评分。",
            icon_name="chat_dots",
            link_text="开始训练 →",
        ),
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        card(
            title="知识库",
            description="浏览案例、方法论、行业敏感度和产品资料，支持关键词搜索和分类筛选。",
            icon_name="database",
            link_text="浏览知识库 →",
        ),
        unsafe_allow_html=True,
    )

with col4:
    st.markdown(
        card(
            title="威胁情报",
            description="实时行业威胁事件追踪、安全态势感知、风险预判与来源追溯。",
            icon_name="magnifying_glass",
            link_text="查看情报 →",
        ),
        unsafe_allow_html=True,
    )
    st.caption("通过智能 Prep 自动获取")

# JS: read sidebar nav URLs and wire up card clicks
st.markdown(
    """
<script>
(function() {
    // Give Streamlit time to render the sidebar
    setTimeout(function() {
        var navLinks = {};
        // Streamlit sidebar renders <a> tags inside [data-testid="stSidebarNav"]
        var sidebarLinks = document.querySelectorAll(
            '[data-testid="stSidebarNav"] a, nav a, [data-testid="stSidebar"] a'
        );
        sidebarLinks.forEach(function(link) {
            var href = link.getAttribute('href');
            var text = (link.textContent || '').trim();
            if (text.indexOf('Prep') >= 0 || text.indexOf('prep') >= 0) navLinks.prep = href;
            if (text.indexOf('训练') >= 0) navLinks.train = href;
            if (text.indexOf('知识库') >= 0) navLinks.kb = href;
        });

        var cards = document.querySelectorAll('.jarvis-card');
        var mapping = ['prep', 'train', 'kb'];  // first 3 cards

        for (var i = 0; i < 3 && i < cards.length; i++) {
            var url = navLinks[mapping[i]];
            if (url) {
                cards[i].style.cursor = 'pointer';
                cards[i].setAttribute('data-nav-url', url);
                cards[i].addEventListener('click', function(e) {
                    var u = this.getAttribute('data-nav-url');
                    if (u) window.location.href = u;
                });
            }
        }
    }, 500);  // delay for sidebar to render
})();
</script>
""",
    unsafe_allow_html=True,
)
