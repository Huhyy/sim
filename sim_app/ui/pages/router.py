"""Page routing helpers for the Streamlit UI."""

from sim_app.ui.pages.admin import render_admin_page
from sim_app.ui.pages.admin_sessions import render_admin_sessions_page
from sim_app.ui.pages.already_completed import render_already_completed_page
from sim_app.ui.pages.consent import render_consent_declined_page, render_consent_page
from sim_app.ui.pages.demographics import render_demographics_page
from sim_app.ui.pages.done import render_done_page
from sim_app.ui.pages.enter_session_code import render_enter_session_code_page
from sim_app.ui.pages.final_score import render_final_score_page
from sim_app.ui.pages.home import render_home_page
from sim_app.ui.pages.instructions import render_instructions_page
from sim_app.ui.pages.month_feedback import render_month_feedback_page
from sim_app.ui.pages.profile import render_profile_page
from sim_app.ui.pages.questions import render_post_question_page, render_pre_question_page, render_pre_questions_redirect_page
from sim_app.ui.pages.simulation import render_simulation_page


STATIC_PAGE_RENDERERS = {
    "enter_session_code": render_enter_session_code_page,
    "admin": render_admin_page,
    "admin_sessions": render_admin_sessions_page,
    "already_completed": render_already_completed_page,
    "home": render_home_page,
    "consent": render_consent_page,
    "consent_declined": render_consent_declined_page,
    "demographics": render_demographics_page,
    "pre_questions": render_pre_questions_redirect_page,
    "instructions": render_instructions_page,
    "profile": render_profile_page,
    "simulation": render_simulation_page,
    "month_feedback": render_month_feedback_page,
    "final_score": render_final_score_page,
    "done": render_done_page,
}


def get_page_renderer(page):
    if page.startswith("pre_question_"):
        return render_pre_question_page
    if page.startswith("post_question_"):
        return render_post_question_page
    return STATIC_PAGE_RENDERERS.get(page)


def render_current_page(ctx):
    page = ctx.st.session_state.page
    renderer = get_page_renderer(page)
    if renderer is None:
        raise ValueError(f"Unknown page: {page}")
    return renderer(ctx)


__all__ = [
    "STATIC_PAGE_RENDERERS",
    "get_page_renderer",
    "render_current_page",
]

