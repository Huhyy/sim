"""Home page."""

from sim_app.application.commands import go_to_page
from sim_app.session.streamlit_state import read_participant_state
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
    if st.session_state.get("score_frame") == "loss_frame":
        st.info(t("home.loss_frame_notice"))
    else:
        st.info(t("home.gain_frame_notice"))
    st.markdown(t("home.note"))
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button(t("home.button"), type="primary"):
        command = go_to_page(read_participant_state(st.session_state), "consent")
        ctx.commit_command(command, operation="home:start")
    if st.button(t("study_session.optional_button"), type="secondary"):
        command = go_to_page(read_participant_state(st.session_state), "enter_session_code")
        ctx.commit_command(command, operation="home:study_session")


__all__ = [
    "render_home_page",
]

