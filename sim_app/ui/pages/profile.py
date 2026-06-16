"""Participant profile page."""

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
        st.session_state.scroll_to_top = True
        ctx.goto("simulation")


__all__ = [
    "render_profile_page",
]

