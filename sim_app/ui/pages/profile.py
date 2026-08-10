"""Participant profile page."""

from sim_app.application.commands import complete_profile
from sim_app.session.streamlit_state import read_participant_state
from sim_app.ui.styles import PROFILE_CSS, apply_css


def render_profile_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()
    apply_css(st, PROFILE_CSS)

    st.title(t("profile.title"))
    st.markdown(t("profile.intro"))

    st.markdown('<div class="profile-text">', unsafe_allow_html=True)
    for section in t("profile.sections"):
        st.subheader(section["title"])
        st.markdown(section["body"])

    st.markdown('</div>', unsafe_allow_html=True)

    if st.button(t("profile.button"), type="primary"):
        command = complete_profile(read_participant_state(st.session_state))
        ctx.commit_command(command, operation="profile:complete")


__all__ = [
    "render_profile_page",
]

