"""Optional password gate for the JARVIS Streamlit UI.

When the ``JARVIS_PASSWORD`` environment variable is set, users must enter
the password before accessing the application.  If the variable is empty or
unset, access is granted unconditionally.
"""

import os


def password_gate() -> bool:
    """Check password if ``JARVIS_PASSWORD`` is set.

    Returns ``True`` when access is granted.  When a password is configured
    and the user has not yet authenticated, a Streamlit password input is
    rendered and the script is stopped via ``st.stop()``.
    """
    import streamlit as st  # noqa: PLC0415 -- lazy import so the module is importable outside Streamlit

    password = os.environ.get("JARVIS_PASSWORD", "")
    if not password:
        return True  # No password configured -- open access

    # Already authenticated in this session
    if st.session_state.get("authenticated"):
        return True

    # Render password input
    st.markdown("### Access Protection")
    pwd = st.text_input("Please enter the access password", type="password")
    if pwd == password:
        st.session_state["authenticated"] = True
        st.rerun()
        return True

    if pwd:
        st.error("Incorrect password")

    st.stop()
    return False
