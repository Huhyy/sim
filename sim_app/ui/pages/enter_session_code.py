"""Study-session code entry page."""

import re


def normalize_study_session_code(value):
    return re.sub(r"\D", "", str(value or ""))[:6]


def render_enter_session_code_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()
    st.title(t("study_session.title"))
    st.markdown(t("study_session.body"))
    code_value = st.text_input(
        t("study_session.input_label"),
        value=st.session_state.get("study_session_code", ""),
        max_chars=6,
        help=t("study_session.input_help"),
    )
    if st.button(t("study_session.button"), type="primary"):
        session_code = normalize_study_session_code(code_value)
        if len(session_code) != 6:
            st.warning(t("study_session.missing"))
            st.stop()
        record = ctx.load_admin_study_session_by_code(session_code)
        if not record:
            st.error(t("study_session.invalid"))
            st.stop()
        st.session_state.study_session_id = record["id"]
        st.session_state.study_session_code = record["session_code"]
        st.session_state.scroll_to_top = True
        ctx.goto("home")
    if st.button(t("study_session.skip_button"), type="secondary"):
        st.session_state.study_session_id = None
        st.session_state.study_session_code = None
        st.session_state.scroll_to_top = True
        ctx.goto("home")


__all__ = [
    "normalize_study_session_code",
    "render_enter_session_code_page",
]

