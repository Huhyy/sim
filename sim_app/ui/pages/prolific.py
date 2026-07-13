"""Prolific-specific pages."""

from sim_app.infra.time import _utcnow


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

        attempts = int(st.session_state.get("comprehension_attempts") or 0) + 1
        st.session_state.comprehension_attempts = attempts
        passed = _responses_pass(t, responses)
        _record_comprehension_checks(ctx, responses, attempts, passed)

        if passed:
            st.session_state.comprehension_passed = True
            st.session_state.answers["comprehension_passed"] = True
            st.session_state.answers["comprehension_passed_at"] = _utcnow()
            ctx.goto("profile")
        elif attempts >= 2:
            st.session_state.comprehension_passed = False
            ctx.goto("prolific_return")
        else:
            st.warning(t("prolific.comprehension_retry"))


def _responses_pass(t, responses):
    for question in COMPREHENSION_QUESTIONS:
        selected = responses.get(question["id"])
        if not str(selected or "").startswith(question["correct"]):
            return False
    return True


def _record_comprehension_checks(ctx, responses, attempt, passed):
    if not hasattr(ctx, "save_quality_check"):
        return
    for question in COMPREHENSION_QUESTIONS:
        ctx.save_quality_check(
            check_type="comprehension",
            check_id=question["id"],
            attempt_number=attempt,
            passed=passed and str(responses.get(question["id"]) or "").startswith(question["correct"]),
            response_value=responses.get(question["id"]),
            page_id="comprehension",
        )


__all__ = [
    "render_comprehension_page",
    "render_prolific_error_page",
    "render_prolific_return_page",
]
