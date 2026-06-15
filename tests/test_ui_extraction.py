from types import SimpleNamespace


def test_page_router_resolves_static_and_dynamic_pages():
    from sim_app.ui.pages import get_page_renderer
    from sim_app.ui.pages.questions import render_post_question_page, render_pre_question_page

    assert get_page_renderer("home").__name__ == "render_home_page"
    assert get_page_renderer("simulation").__name__ == "render_simulation_page"
    assert get_page_renderer("done").__name__ == "render_done_page"
    assert get_page_renderer("pre_question_0") is render_pre_question_page
    assert get_page_renderer("post_question_3") is render_post_question_page
    assert get_page_renderer("missing") is None


def test_all_page_modules_import():
    import sim_app.ui.pages.admin
    import sim_app.ui.pages.already_completed
    import sim_app.ui.pages.consent
    import sim_app.ui.pages.demographics
    import sim_app.ui.pages.done
    import sim_app.ui.pages.enter_session_code
    import sim_app.ui.pages.final_score
    import sim_app.ui.pages.home
    import sim_app.ui.pages.instructions
    import sim_app.ui.pages.login
    import sim_app.ui.pages.month_feedback
    import sim_app.ui.pages.profile
    import sim_app.ui.pages.questions
    import sim_app.ui.pages.simulation


def test_ui_formatting_helpers():
    from sim_app.ui.formatting import display_euro, display_number, month_sum, money

    assert money("12.345") == 12.35
    assert display_number(12.0) == "12"
    assert display_number(12.3) == "12.30"
    assert display_euro(12.3) == "12.30 €"
    assert month_sum({"a": 1, "b": 2.345}) == 3.35


def test_normalize_study_session_code():
    from sim_app.ui.pages.enter_session_code import normalize_study_session_code

    assert normalize_study_session_code("ab12 34-567") == "123456"


def test_quiz_helpers_with_plain_answers():
    from sim_app.ui.components.quiz import all_answered, demographics_complete

    section = {"key_prefix": "pre", "questions": ["a", "b"]}
    assert all_answered([section], {"pre_0": "x", "pre_1": "y"})
    assert not all_answered([section], {"pre_0": "x"})

    complete_answers = {
        "demo_age": 30,
        "demo_gender": "x",
        "demo_education": "x",
        "demo_field": "x",
        "demo_occupation": "x",
        "demo_financial_decisions": "x",
        "demo_credit_experience": "x",
        "demo_financial_familiarity": "x",
        "demo_living_situation": "x",
        "demo_recurring_responsibilities": "x",
        "demo_country": "x",
    }
    assert demographics_complete(complete_answers)
    assert not demographics_complete({**complete_answers, "demo_country": ""})


def test_render_current_page_uses_registered_renderer(monkeypatch):
    import sim_app.ui.pages.router as router

    calls = []
    monkeypatch.setitem(router.STATIC_PAGE_RENDERERS, "home", lambda ctx: calls.append(ctx.st.session_state.page))

    ctx = SimpleNamespace(st=SimpleNamespace(session_state=SimpleNamespace(page="home")))
    router.render_current_page(ctx)

    assert calls == ["home"]
