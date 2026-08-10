"""Questionnaire rendering helpers."""

import random

DEMOGRAPHIC_KEYS = [
    "demo_age",
    "demo_gender",
    "demo_education",
    "demo_field",
    "demo_occupation",
    "demo_income",
    "demo_financial_decisions",
    "demo_credit_experience",
    "demo_financial_familiarity",
    "demo_living_situation",
    "demo_recurring_responsibilities",
    "demo_country",
]


def randomize_sections(sections, answers):
    for section in sections:
        randomize_section(section, answers)


def randomize_section(section, answers):
    for i in range(len(section["questions"])):
        key = f"{section['key_prefix']}_{i}"
        answers[key] = random.choice(section["scale"])


def render_question_section(st, t, section, chapter_number, question_offset=0):
    st.markdown(f"### {t('quiz.chapter_heading', number=chapter_number)}")
    st.caption(section["instruction"])
    for i, q in enumerate(section["questions"]):
        key = f"{section['key_prefix']}_{i}"
        current = st.session_state.answers.get(key)
        idx = section["scale"].index(current) if current in section["scale"] else None
        st.session_state.answers[key] = st.radio(
            f"{question_offset + i + 1}. {q}",
            options=section["scale"],
            index=idx,
            horizontal=True,
            key=f"radio_{key}",
        )


def all_answered(sections, answers):
    for section in sections:
        for i in range(len(section["questions"])):
            key = f"{section['key_prefix']}_{i}"
            if answers.get(key) is None:
                return False
    return True


def demographics_complete(answers):
    return all(answers.get(key) not in (None, "") for key in DEMOGRAPHIC_KEYS)


def render_quiz_chapter(
    ctx,
    section,
    chapter_index,
    total_chapters,
    next_page,
    dev_label,
    title,
    question_offset=0,
    before_continue=None,
    validate_extra=None,
    on_valid_continue=None,
    on_complete=None,
):
    st = ctx.st
    t = ctx.t
    st.title(title)
    st.caption(t("quiz.chapter_label", current=chapter_index + 1, total=total_chapters))
    st.markdown(t("quiz.chapter_continue_help"))
    st.progress((chapter_index + 1) / total_chapters)
    render_question_section(st, t, section, chapter_index + 1, question_offset)

    if ctx.dev:
        if st.button(dev_label, type="secondary", key=f"dev_{section['key_prefix']}_{chapter_index}"):
            randomize_section(section, st.session_state.answers)
            st.session_state.scroll_to_top = True
            if on_complete:
                on_complete()
            else:
                ctx.goto(next_page)

    if not all_answered([section], st.session_state.answers):
        st.warning(t("quiz.chapter_required_warning"))

    extra_value = before_continue() if before_continue else None

    if st.button(t("quiz.continue_button"), type="primary", key=f"continue_{section['key_prefix']}_{chapter_index}"):
        if validate_extra and not validate_extra(extra_value):
            st.error(t("prolific.attention_missing"))
            st.stop()
        if all_answered([section], st.session_state.answers):
            if on_valid_continue:
                on_valid_continue(extra_value)
            st.session_state.scroll_to_top = True
            if on_complete:
                on_complete()
            else:
                ctx.goto(next_page)
        else:
            st.error(t("quiz.chapter_missing_error"))


__all__ = [
    "DEMOGRAPHIC_KEYS",
    "all_answered",
    "demographics_complete",
    "randomize_section",
    "randomize_sections",
    "render_question_section",
    "render_quiz_chapter",
]

