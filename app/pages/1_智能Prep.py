"""Smart Prep page - main Prep package generation UI."""

import streamlit as st

st.set_page_config(
    page_title="JARVIS - Smart Prep",
    page_icon="🛡️",
    layout="wide",
)

st.title("Smart Prep")
st.markdown("Generate a structured Prep package for your client meeting.")

st.divider()

# Input section
user_input = st.text_area(
    "Describe your meeting scenario",
    placeholder="e.g. Visiting a manufacturing client tomorrow, their production line was hit by ransomware",
    height=100,
)

# Quick-fill examples
if st.button("Fill Example"):
    user_input = "Visiting a manufacturing client tomorrow, their production line was hit by ransomware"
    st.rerun()

# Industry quick tags
st.markdown("**Industry shortcuts:**")
cols = st.columns(3)
industries = {"Manufacturing": "manufacturing", "Finance": "finance", "Healthcare": "healthcare"}
for col, (label, _) in zip(cols, industries.items()):
    if col.button(label):
        user_input = f"Meeting with a {label.lower()} client about security challenges"

st.divider()

# Generate button
if st.button("Generate Prep Package", type="primary", disabled=not user_input):
    with st.spinner("Generating Prep package..."):
        try:
            from jarvis.engine.intent import recognize
            from jarvis.engine.llm_engine import generate_prep, LLMUnavailableError
            from jarvis.engine.rule_engine import generate_prep_fallback
            from jarvis.generators.ppt_outline import generate_outline
            from jarvis.intelligence.threat_feed import fetch_threats
            from jarvis.knowledge.loader import load_all

            # Load knowledge base
            kb = load_all()

            # Recognize intent
            intent = recognize(user_input)
            st.info(f"Detected: industry={intent.industry}, scenario={intent.scenario}")

            # Try LLM generation, fallback to rules
            fallback_used = False
            try:
                pkg = generate_prep(intent, kb)
            except LLMUnavailableError as e:
                st.warning(f"Switched to basic mode ({e})")
                pkg = generate_prep_fallback(intent, kb)
                fallback_used = True

            # Enrich with threat intel
            pkg.threat_intel = fetch_threats(intent.industry)

            # Display results
            st.success("Prep package generated!" + (" (Basic mode)" if fallback_used else ""))

            with st.expander("Scenario Assessment"):
                st.markdown(pkg.scenario_assessment)

            with st.expander("Sensitivity Alerts"):
                for alert in pkg.sensitivity_alerts:
                    st.markdown(f"- {alert}")

            with st.expander("Matched Cases"):
                if pkg.matched_cases:
                    for case_id in pkg.matched_cases:
                        st.markdown(f"- `{case_id}`")
                else:
                    st.markdown("_No specific cases matched_")

            with st.expander("Follow-up Questions"):
                for q in pkg.follow_up_questions:
                    st.markdown(f"- {q}")

            with st.expander("Solution Direction"):
                st.markdown(pkg.solution_direction)

            with st.expander("Talking Points"):
                st.markdown(pkg.talking_points)

            if pkg.threat_intel:
                with st.expander("Threat Intelligence"):
                    for event in pkg.threat_intel:
                        st.markdown(f"**{event.title}** ({event.date})")
                        st.markdown(event.description)
                        if event.source_url:
                            st.markdown(f"[Source]({event.source_url})")

            # PPT Outline
            st.divider()
            if st.button("Generate PPT Outline"):
                outline = generate_outline(pkg)
                st.markdown(outline)
                st.code(outline, language="markdown")

        except Exception as e:
            st.error(f"Error: {e}")
