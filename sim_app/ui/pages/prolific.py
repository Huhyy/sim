"""Prolific-specific pages."""

from sim_app.application.commands import begin_comprehension_attempt, complete_comprehension_attempt
from sim_app.infra.time import _utcnow
from sim_app.session.streamlit_state import read_participant_state


COMPREHENSION_QUESTIONS = [
    {
        "id": "who_completes",
        "prompt_key": "prolific.comprehension_q1",
        "options_key": "prolific.comprehension_q1_options",
        "correct": "A",
    },
    {
        "id": "monthly_task",
        "prompt_key": "prolific.comprehension_q2",
        "options_key": "prolific.comprehension_q2_options",
        "correct": "A",
    },
]


def render_prolific_error_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()
    message_key = st.session_state.get("prolific_access_error") or "prolific.error_missing_params"
    st.error(t(message_key))


def render_prolific_return_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()
    st.error(t("prolific.return_message"))


def render_comprehension_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()
    st.title(t("prolific.comprehension_title"))
    st.markdown(t("prolific.comprehension_intro"))

    responses = {}
    for question in COMPREHENSION_QUESTIONS:
        options = t(question["options_key"])
        value = st.radio(
            t(question["prompt_key"]),
            options=options,
            index=None,
            key=f"comprehension_{question['id']}",
        )
        responses[question["id"]] = value

    if st.button(t("prolific.comprehension_button"), type="primary"):
        if any(value is None for value in responses.values()):
            st.warning(t("prolific.comprehension_missing"))
            st.stop()

        participant_state = begin_comprehension_attempt(read_participant_state(st.session_state))
        attempts = participant_state.comprehension_attempts
        passed = _responses_pass(t, responses)
        command = complete_comprehension_attempt(
            participant_state,
            passed=passed,
            passed_at=_utcnow() if passed else None,
        )
        ctx.commit_quality_state(
            command.state,
            _comprehension_events(responses, attempts, passed),
            operation=f"quality:comprehension_attempt:{attempts}:{passed}",
            rerun=bool(command.next_page),
        )
        if not command.next_page:
            st.warning(t("prolific.comprehension_retry"))


def _responses_pass(t, responses):
    for question in COMPREHENSION_QUESTIONS:
        selected = responses.get(question["id"])
        if not str(selected or "").startswith(question["correct"]):
            return False
    return True


def _comprehension_events(responses, attempt, passed):
    return [
        {
            "check_type": "comprehension",
            "check_id": question["id"],
            "attempt_number": attempt,
            "passed": passed and str(responses.get(question["id"]) or "").startswith(question["correct"]),
            "response_value": responses.get(question["id"]),
            "response_time_ms": None,
            "page_id": "comprehension",
        }
        for question in COMPREHENSION_QUESTIONS
    ]


__all__ = [
    "render_comprehension_page",
    "render_prolific_error_page",
    "render_prolific_return_page",
]
