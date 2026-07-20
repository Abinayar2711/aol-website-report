"""Google sign-in gate.

Drop this file into each report repo unchanged and call require_login() once, right
after st.set_page_config(). Everything that varies between apps lives in secrets.toml,
not here.

Why the domain check exists: st.login() only proves WHO someone is, not that they are
allowed in. If the Google consent screen is configured as "External", any Google account
on earth completes the OAuth round-trip successfully. ALLOWED_DOMAINS is therefore the
actual security boundary, not a convenience filter -- do not remove it on the assumption
that the consent screen is doing the work.
"""
import streamlit as st

# Anyone whose verified Google email ends in one of these may view the report.
ALLOWED_DOMAINS = ("in.artofliving.org", "artofliving.org")

# Individual exceptions for people outside the domains above (e.g. a consultant).
# Full lowercase email addresses.
ALLOWED_EMAILS = ()


def _is_allowed(email: str) -> bool:
    if not email:
        return False
    email = email.lower().strip()
    if email in ALLOWED_EMAILS:
        return True
    return email.endswith(tuple("@" + d for d in ALLOWED_DOMAINS))


def require_login(title: str = "Website Registrations Report"):
    """Halt the script unless a signed-in, allow-listed user is viewing.

    Returns the viewer's email once access is granted, so callers can show it or log it.
    """
    if not st.user.is_logged_in:
        st.markdown(f"### {title}")
        st.write(
            "This report contains internal Art of Living data and is visible only to "
            "staff. Please sign in with your Art of Living Google account."
        )
        st.button("Sign in with Google", type="primary", on_click=st.login)
        st.stop()

    email = (st.user.email or "").lower().strip()

    # Google sets email_verified=False for some account types; an unverified address
    # is not evidence of domain membership, so treat it as a failed check.
    if not st.user.get("email_verified", False) or not _is_allowed(email):
        st.markdown(f"### {title}")
        st.error(
            f"**{email or 'This account'}** cannot open this report.\n\n"
            "This data is internal to the Art of Living organisation and is only "
            "visible to signed-in staff accounts. Please sign out and sign back in "
            "with your Art of Living email, or ask the report owner for access."
        )
        st.button("Sign out", on_click=st.logout)
        st.stop()

    return email


def sidebar_account():
    """Show who is signed in, with a sign-out button. Call after require_login()."""
    with st.sidebar:
        st.caption(f"Signed in as **{st.user.email}**")
        st.button("Sign out", on_click=st.logout, use_container_width=True)
