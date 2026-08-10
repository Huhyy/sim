"""Consent pages."""

from sim_app.application.commands import accept_consent, decline_consent, go_to_page
from sim_app.session.streamlit_state import read_participant_state
from sim_app.ui.styles import CONSENT_CSS, apply_css


def render_consent_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()
    apply_css(st, CONSENT_CSS)

    if st.session_state.get("score_frame") == "loss_frame":
        st.info(t("home.loss_frame_notice"))
    else:
        st.info(t("home.gain_frame_notice"))
    st.markdown('<div class="consent-page">', unsafe_allow_html=True)
    st.markdown(t("consent.markdown"))
    st.markdown('</div>', unsafe_allow_html=True)

    consent_items = t("consent.items")
    consent_values = [
        st.checkbox(item, key=f"consent_item_{index}")
        for index, item in enumerate(consent_items)
    ]
    anti_ai_value = True
    if st.session_state.get("prolific_mode"):
        anti_ai_value = st.checkbox(
            t("prolific.anti_ai_declaration"),
            key="anti_ai_declaration_input",
            value=st.session_state.answers.get("anti_ai_declaration", False),
        )
    consent_complete = all(consent_values)

    col_accept, col_decline = st.columns([2, 1])
    with col_accept:
        accept_clicked = st.button(
            t("consent.accept_button"),
            type="primary",
            use_container_width=True,
            key="consent_accept",
        )
    with col_decline:
        decline_clicked = st.button(
            t("consent.decline_button"),
            type="secondary",
            use_container_width=True,
            key="consent_decline",
        )

    if accept_clicked:
        if not consent_complete or not anti_ai_value:
            st.warning(t("consent.warning"))
            st.stop()
        command = accept_consent(
            read_participant_state(st.session_state),
            anti_ai_declaration=anti_ai_value,
        )
        ctx.commit_command(command, operation="consent:accept")

    if decline_clicked:
        command = decline_consent(read_participant_state(st.session_state))
        ctx.commit_command(command, operation="consent:decline")


def render_consent_declined_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()
    st.title(t("consent_declined.title"))
    st.markdown(t("consent_declined.body"))
    if st.button(t("consent_declined.button"), type="primary"):
        command = go_to_page(read_participant_state(st.session_state), "consent")
        ctx.commit_command(command, operation="consent:return")


__all__ = [
    "render_consent_declined_page",
    "render_consent_page",
]

