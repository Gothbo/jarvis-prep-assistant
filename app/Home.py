"""JARVIS - Streamlit Home Page."""

import streamlit as st

st.set_page_config(
    page_title="JARVIS - Smart Prep Assistant",
    page_icon="🛡️",
    layout="wide",
)

st.title("JARVIS")
st.markdown("**AI-powered Sales Preparation Assistant**")

st.divider()

st.markdown(
    """
    JARVIS helps sales preparation teams quickly generate structured
    **Prep packages** for client meetings, combining industry knowledge,
    threat intelligence, and AI-powered insights.
    """
)

col1, col2 = st.columns(2)

with col1:
    if st.button("Smart Prep", use_container_width=True):
        st.switch_page("pages/1_智能Prep.py")
    st.caption("Generate a Prep package for your next client meeting")

with col2:
    if st.button("Mock Training", use_container_width=True):
        st.switch_page("pages/2_模拟训练.py")
    st.caption("Practice your sales pitch (coming soon)")
