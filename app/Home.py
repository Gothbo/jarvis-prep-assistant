"""JARVIS - Streamlit Home Page."""

import streamlit as st

st.set_page_config(
    page_title="JARVIS - 智能 Prep 助手",
    page_icon="🛡️",
    layout="wide",
)

st.title("JARVIS")
st.markdown("**AI 驱动的销售拜访准备助手**")

st.divider()

st.markdown(
    """
    JARVIS 帮助销售准备团队快速生成结构化的 **Prep 包**，
    融合行业知识库、威胁情报和 AI 洞察，为客户拜访做好充分准备。
    """
)

# ---------------------------------------------------------------------------
# Feature overview
# ---------------------------------------------------------------------------
st.markdown("### 核心功能")

feat_col1, feat_col2, feat_col3 = st.columns(3)

with feat_col1:
    st.markdown(
        """
        #### 智能 Prep
        - 场景识别与意图分析
        - 自动匹配行业案例
        - 敏感度提醒与话术建议
        - 一键生成 PPT 大纲
        """
    )

with feat_col2:
    st.markdown(
        """
        #### 知识库引擎
        - YAML 驱动的模块化知识库
        - 案例、方法论、产品数据
        - 规则引擎兜底保障
        - LLM 增强内容生成
        """
    )

with feat_col3:
    st.markdown(
        """
        #### 威胁情报
        - 实时行业威胁事件抓取
        - 安全态势感知
        - 客户拜访前风险预判
        - 来源链接追溯
        """
    )

st.divider()

# ---------------------------------------------------------------------------
# Navigation buttons
# ---------------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    if st.button("智能 Prep", use_container_width=True):
        st.switch_page("pages/1_智能Prep.py")
    st.caption("为你的下一次客户拜访生成 Prep 包")

with col2:
    if st.button("模拟训练", use_container_width=True):
        st.switch_page("pages/2_模拟训练.py")
    st.caption("练习你的销售话术（即将推出）")
