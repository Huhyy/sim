"""Consent pages."""

from sim_app.ui.styles import CONSENT_CSS, apply_css


def render_consent_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()
    apply_css(st, CONSENT_CSS)

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
        st.session_state.answers["consent_agreed"] = "1 - Da"
        if st.session_state.get("prolific_mode"):
            st.session_state.answers["anti_ai_declaration"] = True
        st.session_state.scroll_to_top = True
        ctx.goto("demographics")

    if decline_clicked:
        st.session_state.answers["consent_agreed"] = "0 - Nu"
        st.session_state.scroll_to_top = True
        ctx.goto("consent_declined")


def render_consent_declined_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()
    st.title(t("consent_declined.title"))
    st.markdown(t("consent_declined.body"))
    if st.button(t("consent_declined.button"), type="primary"):
        st.session_state.scroll_to_top = True
        ctx.goto("consent")


__all__ = [
    "render_consent_declined_page",
    "render_consent_page",
]

