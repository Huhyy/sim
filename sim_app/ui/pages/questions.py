"""Pre- and post-simulation questionnaire pages."""

from sim_app.application.commands import (
    complete_post_question,
    complete_pre_question,
    record_attention_result,
)
from sim_app.application.progression import (
    page_after_post_question,
    page_after_pre_question,
    redirect_for_post_question_index,
    redirect_for_pre_question_index,
    required_page_before_pre_questions,
)
from sim_app.session.streamlit_state import read_participant_state
from sim_app.ui.components.quiz import all_answered, randomize_section, render_question_section, render_quiz_chapter


def _render_attention_check(st, t, key, prompt_key):
    if not st.session_state.get("prolific_mode"):
        return None
    return st.radio(
        t(prompt_key),
        options=t("prolific.attention_number_options"),
        index=None,
        horizontal=True,
        key=key,
    )


def _attention_passed(value):
    return str(value or "").startswith("3")


def _attention_transition(state, check_id, response_value, page_id):
    passed = _attention_passed(response_value)
    participant_state = record_attention_result(
        state,
        passed=passed,
    )
    event = {
        "check_type": "attention",
        "check_id": check_id,
        "attempt_number": 1,
        "passed": passed,
        "response_value": response_value,
        "response_time_ms": None,
        "page_id": page_id,
    }
    return participant_state, event


def _complete_pre_question(ctx, section_index, section_count, attention=None):
    participant_state = read_participant_state(ctx.st.session_state)
    quality_event = None
    if attention is not None:
        participant_state, quality_event = _attention_transition(participant_state, *attention)
    command = complete_pre_question(
        participant_state,
        section_index=section_index,
        section_count=section_count,
    )
    if quality_event is not None:
        ctx.commit_quality_state(
            command.state,
            [quality_event],
            operation=f"quality:pre:{section_index}:{quality_event['check_id']}",
        )
        return
    ctx.commit_command(command, operation=f"questionnaire:pre:{section_index}")


def _complete_post_question(ctx, section_index, section_count, attention=None):
    participant_state = read_participant_state(ctx.st.session_state)
    quality_event = None
    if attention is not None:
        participant_state, quality_event = _attention_transition(participant_state, *attention)
    command = complete_post_question(
        participant_state,
        section_index=section_index,
        section_count=section_count,
    )
    if quality_event is not None:
        ctx.commit_quality_state(
            command.state,
            [quality_event],
            operation=f"quality:post:{section_index}:{quality_event['check_id']}",
        )
        return
    ctx.commit_command(command, operation=f"questionnaire:post:{section_index}")


def render_pre_questions_redirect_page(ctx):
    required_page = required_page_before_pre_questions(read_participant_state(ctx.st.session_state))
    ctx.goto(required_page or "pre_question_0")


def render_pre_question_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()
    required_page = required_page_before_pre_questions(read_participant_state(st.session_state))
    if required_page:
        ctx.goto(required_page)

    pre_sections = ctx.get_display_pre_sections()

    try:
        pre_index = int(st.session_state.page.rsplit("_", 1)[1])
    except Exception:
        ctx.goto("pre_question_0")

    redirect_page = redirect_for_pre_question_index(pre_index, len(pre_sections))
    if redirect_page:
        ctx.goto(redirect_page)

    next_page = page_after_pre_question(pre_index, len(pre_sections))
    attention_submission = {}
    render_quiz_chapter(
        ctx,
        pre_sections[pre_index],
        pre_index,
        len(pre_sections),
        next_page,
        t("quiz.dev_randomize"),
        t("quiz.pre_title"),
        question_offset=sum(len(section["questions"]) for section in pre_sections[:pre_index]),
        before_continue=(
            lambda: _render_attention_check(st, t, "attention_pre_1", "prolific.attention_1")
            if st.session_state.get("prolific_mode") and pre_index == 0
            else None
        ),
        validate_extra=(
            lambda value: value is not None
            if st.session_state.get("prolific_mode") and pre_index == 0
            else None
        ),
        on_valid_continue=(
            lambda value: attention_submission.__setitem__("value", value)
            if st.session_state.get("prolific_mode") and pre_index == 0
            else None
        ),
        on_complete=lambda: _complete_pre_question(
            ctx,
            pre_index,
            len(pre_sections),
            attention=("attention_pre_1", attention_submission["value"], "pre_question_0")
            if "value" in attention_submission
            else None,
        ),
    )


def render_post_question_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()
    post_sections = ctx.get_display_post_sections()
    try:
        post_index = int(st.session_state.page.rsplit("_", 1)[1])
    except Exception:
        ctx.goto("post_question_0")

    redirect_page = redirect_for_post_question_index(post_index, len(post_sections))
    if redirect_page:
        ctx.goto(redirect_page)

    section = post_sections[post_index]
    next_page = page_after_post_question(post_index, len(post_sections))
    question_offset = sum(len(post_section["questions"]) for post_section in post_sections[:post_index])

    st.title(t("quiz.post_title"))
    st.caption(t("quiz.chapter_label", current=post_index + 1, total=len(post_sections)))
    st.progress((post_index + 1) / len(post_sections))
    render_question_section(st, t, section, post_index + 1, question_offset)
    attention_value = None
    if st.session_state.get("prolific_mode") and post_index + 1 >= len(post_sections):
        attention_value = _render_attention_check(st, t, "attention_post_1", "prolific.attention_2")

    if not all_answered([section], st.session_state.answers):
        st.warning(t("quiz.chapter_required_warning"))

    if post_index + 1 >= len(post_sections):
        st.markdown(t("quiz.post_optional_feedback_title"))
        st.session_state.answers["feedback"] = st.text_area(
            t("quiz.post_optional_feedback_prompt"),
            value=st.session_state.answers.get("feedback", ""),
        )
        st.session_state.answers["strategy_feedback"] = st.text_area(
            t("quiz.post_strategy_prompt"),
            value=st.session_state.answers.get("strategy_feedback", ""),
        )

    if ctx.dev:
        if st.button(t("quiz.dev_randomize"), type="secondary", key=f"dev_post_question_{post_index}"):
            randomize_section(section, st.session_state.answers)
            st.session_state.scroll_to_top = True
            _complete_post_question(ctx, post_index, len(post_sections))

    button_label = t("quiz.post_finish_button") if post_index + 1 >= len(post_sections) else t("quiz.continue_button")
    if st.button(button_label, type="primary", key=f"continue_post_question_{post_index}"):
        if st.session_state.get("prolific_mode") and post_index + 1 >= len(post_sections) and attention_value is None:
            st.error(t("prolific.attention_missing"))
            st.stop()
        if all_answered([section], st.session_state.answers):
            if st.session_state.get("prolific_mode") and post_index + 1 >= len(post_sections):
                _complete_post_question(
                    ctx,
                    post_index,
                    len(post_sections),
                    attention=("attention_post_1", attention_value, st.session_state.page),
                )
            else:
                _complete_post_question(ctx, post_index, len(post_sections))
        else:
            st.error(t("quiz.chapter_missing_error"))


__all__ = [
    "render_post_question_page",
    "render_pre_question_page",
    "render_pre_questions_redirect_page",
]

