"""Pre- and post-simulation questionnaire pages."""

from sim_app.ui.components.quiz import all_answered, demographics_complete, randomize_section, render_question_section, render_quiz_chapter


def render_pre_questions_redirect_page(ctx):
    st = ctx.st
    if st.session_state.answers.get("consent_agreed") != "1 - Da":
        ctx.goto("consent")
    elif not demographics_complete(st.session_state.answers):
        ctx.goto("demographics")
    else:
        ctx.goto("pre_question_0")


def render_pre_question_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()
    if st.session_state.answers.get("consent_agreed") != "1 - Da":
        ctx.goto("consent")
    if not demographics_complete(st.session_state.answers):
        ctx.goto("demographics")

    pre_sections = ctx.get_display_pre_sections()

    try:
        pre_index = int(st.session_state.page.rsplit("_", 1)[1])
    except Exception:
        ctx.goto("pre_question_0")

    if pre_index >= len(pre_sections):
        ctx.goto("instructions")

    next_page = "instructions" if pre_index + 1 >= len(pre_sections) else f"pre_question_{pre_index + 1}"
    render_quiz_chapter(
        ctx,
        pre_sections[pre_index],
        pre_index,
        len(pre_sections),
        next_page,
        t("quiz.dev_randomize"),
        t("quiz.pre_title"),
        question_offset=sum(len(section["questions"]) for section in pre_sections[:pre_index]),
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

    if post_index >= len(post_sections):
        ctx.goto("final_score")

    section = post_sections[post_index]
    next_page = "final_score" if post_index + 1 >= len(post_sections) else f"post_question_{post_index + 1}"
    question_offset = sum(len(post_section["questions"]) for post_section in post_sections[:post_index])

    st.title(t("quiz.post_title"))
    st.caption(t("quiz.chapter_label", current=post_index + 1, total=len(post_sections)))
    st.progress((post_index + 1) / len(post_sections))
    render_question_section(st, t, section, post_index + 1, question_offset)

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
            ctx.goto(next_page)

    button_label = t("quiz.post_finish_button") if post_index + 1 >= len(post_sections) else t("quiz.continue_button")
    if st.button(button_label, type="primary", key=f"continue_post_question_{post_index}"):
        if all_answered([section], st.session_state.answers):
            st.session_state.scroll_to_top = True
            ctx.goto(next_page)
        else:
            st.error(t("quiz.chapter_missing_error"))


__all__ = [
    "render_post_question_page",
    "render_pre_question_page",
    "render_pre_questions_redirect_page",
]

