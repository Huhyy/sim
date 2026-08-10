"""Participant instructions page."""

from sim_app.application.commands import complete_instructions
from sim_app.session.streamlit_state import read_participant_state
from sim_app.ui.styles import INSTRUCTIONS_CSS, apply_css


def render_instructions_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()
    apply_css(st, INSTRUCTIONS_CSS)

    st.markdown(
        '<div class="participant-instructions">',
        unsafe_allow_html=True,
    )
    st.markdown(t("instructions.body"), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button(t("instructions.button"), type="primary"):
        command = complete_instructions(read_participant_state(st.session_state))
        ctx.commit_command(command, operation="instructions:complete")


__all__ = [
    "render_instructions_page",
]

