"""Home page."""

from sim_app.ui.styles import HOME_CSS, apply_css


def render_home_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()
    apply_css(st, HOME_CSS)
    st.markdown(f'<div class="home-title">{t("home.title")}</div>', unsafe_allow_html=True)
    st.markdown('<div class="home-body">', unsafe_allow_html=True)
    st.markdown(t("home.body"))
    st.info(t("home.info"))
    st.markdown(t("home.note"))
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button(t("home.button"), type="primary"):
        st.session_state.scroll_to_top = True
        ctx.goto("consent")
    if st.button(t("study_session.optional_button"), type="secondary"):
        st.session_state.scroll_to_top = True
        ctx.goto("enter_session_code")


__all__ = [
    "render_home_page",
]

