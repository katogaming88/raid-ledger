"""Password gate via st.secrets.

Single shared password for all officers. On Streamlit Community Cloud,
secrets are configured in the deployment settings (never in the repo).
"""

from __future__ import annotations

import streamlit as st


def check_password() -> bool:
    """Return True if the user has entered the correct password.

    Uses st.secrets["auth"]["password"]. If no secret is configured,
    access is granted (local dev without auth).
    """
    try:
        expected = st.secrets["auth"]["password"]
    except (KeyError, FileNotFoundError):
        # No secret configured — allow access (local dev)
        return True

    if not expected:
        return True

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    st.markdown("## Raid Ledger")
    st.markdown("Enter the officer password to continue.")
    password = st.text_input("Password", type="password", key="auth_password_input")

    if st.button("Log in", key="auth_login_btn"):
        if password == expected:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    return False
