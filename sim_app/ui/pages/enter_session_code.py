"""Study-session code entry page."""

import re

from sim_app.application.commands import assign_study_session, clear_study_session_assignment
from sim_app.session.streamlit_state import read_participant_state


def normalize_study_session_code(value):
    return re.sub(r"\D", "", str(value or ""))[:6]


def normalize_participant_code(value):
    raw = str(value or "").strip().upper()
    digits = re.sub(r"\D", "", raw)
    if digits:
        return f"P{digits[:3].zfill(3)}"
    cleaned = re.sub(r"[^A-Z0-9]", "", raw)
    return cleaned[:4]


def is_valid_participant_code(value):
    return bool(re.fullmatch(r"P[0-9]{3}", str(value or "").strip().upper()))


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
    participant_value = st.text_input(
        t("study_session.participant_label"),
        value=st.session_state.get("participant_code", ""),
        max_chars=4,
        help=t("study_session.participant_help"),
    )
    if st.button(t("study_session.button"), type="primary"):
        session_code = normalize_study_session_code(code_value)
        participant_code = normalize_participant_code(participant_value)
        if len(session_code) != 6:
            st.warning(t("study_session.missing"))
            st.stop()
        if not is_valid_participant_code(participant_code):
            st.warning(t("study_session.participant_missing"))
            st.stop()
        record = ctx.load_admin_study_session_by_code(session_code)
        if not record:
            st.error(t("study_session.invalid"))
            st.stop()
        command = assign_study_session(
            read_participant_state(st.session_state),
            record,
            participant_code,
        )
        ctx.commit_command(command, operation="treatment:bind_admin")
    if st.button(t("study_session.skip_button"), type="secondary"):
        command = clear_study_session_assignment(read_participant_state(st.session_state))
        ctx.commit_command(command, operation="treatment:bind_default")


__all__ = [
    "normalize_study_session_code",
    "normalize_participant_code",
    "is_valid_participant_code",
    "render_enter_session_code_page",
]
