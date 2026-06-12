"""Mock Training page - placeholder for future role-play feature."""

import streamlit as st

st.set_page_config(
    page_title="JARVIS - 模拟训练",
    page_icon="🎭",
    layout="wide",
)

st.title("模拟训练")

st.info("即将推出 · Coming Soon")

st.markdown(
    """
    ### 什么是模拟训练？

    灵感来源于 **Seismic Role-Play Agent**，该功能让你在一个模拟的客户拜访
    环境中练习你的销售话术。

    **运作方式：**
    - LLM 扮演客户角色
    - 你扮演销售代表
    - 练习需求挖掘问题、异议处理和促成签单
    """
)

st.divider()

# ---------------------------------------------------------------------------
# Feature roadmap
# ---------------------------------------------------------------------------
st.markdown("### 功能路线图")

roadmap_col1, roadmap_col2 = st.columns(2)

with roadmap_col1:
    st.markdown("#### 第一阶段 — MVP")
    st.markdown(
        """
        - [ ] 基础对话引擎（LLM 扮演客户）
        - [ ] 支持选择行业和场景模板
        - [ ] 实时文字对话界面
        - [ ] 会话结束后生成表现评分
        """
    )

with roadmap_col2:
    st.markdown("#### 第二阶段 — 增强")
    st.markdown(
        """
        - [ ] 语音输入 / 输出支持
        - [ ] 多轮异议处理模拟
        - [ ] 与智能 Prep 包联动（自动导入拜访场景）
        - [ ] 团队排行榜和历史回放
        """
    )

st.divider()

# ---------------------------------------------------------------------------
# Planned features checklist
# ---------------------------------------------------------------------------
st.markdown("### 计划功能清单")

st.markdown(
    """
    | 功能 | 优先级 | 状态 |
    |------|--------|------|
    | 对话式角色扮演 | P0 | 规划中 |
    | 行业场景选择 | P0 | 规划中 |
    | 表现评分报告 | P1 | 规划中 |
    | Prep 包场景导入 | P1 | 规划中 |
    | 语音交互 | P2 | 待评估 |
    | 团队排行榜 | P2 | 待评估 |
    | 历史会话回放 | P2 | 待评估 |
    """
)

st.divider()
st.caption("敬请期待后续更新！")
