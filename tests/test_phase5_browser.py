from __future__ import annotations

import socket
import threading
import time
import uuid
import re
from pathlib import Path
from contextlib import contextmanager

import pytest
import uvicorn

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright

from sim_app.api.app import create_app
from sim_app.application.admin_services import AdminService
from sim_app.application.principal import ParticipantPrincipal
from sim_app.application.services import ExperimentService
from sim_app.application.state import ParticipantState
from sim_app.auth.browser_session import BrowserSessionManager, SESSION_COOKIE
from sim_app.config import SCENARIO_VERSION
from sim_app.domain.experimental_conditions import condition_config
from sim_app.content.translations import get_display_pre_sections, get_display_post_sections
from sim_app.content.tables import get_month
from sim_app.application.commands import submit_month_decision
from sim_app.persistence.admin_memory import MemoryAdminRepository
from sim_app.persistence.memory import InMemoryExperimentRepository


@contextmanager
def live_app(*, repository=None, admin_repository=None):
    repository = repository or InMemoryExperimentRepository()
    service = ExperimentService(repository)
    manager = BrowserSessionManager("browser-e2e-secret", secure=False)
    app = create_app(
        service=service,
        admin_service=AdminService(admin_repository or MemoryAdminRepository()),
        browser_session_manager=manager,
        docs_enabled=False,
    )
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0)); port = probe.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True); thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline: time.sleep(.02)
    try: yield f"http://127.0.0.1:{port}", manager, service, repository
    finally: server.should_exit = True; thread.join(timeout=10)


def _context(browser, base, manager, principal, *, viewport=None):
    context = browser.new_context(viewport=viewport or {"width": 1280, "height": 900})
    context.add_cookies([{"name": SESSION_COOKIE, "value": manager.encode_principal(principal, csrf_token="csrf-e2e"), "url": base, "httpOnly": True, "sameSite": "Lax"}])
    return context


def test_romanian_pages_render_intact_diacritics():
    pages = [(name, 1) for name in (
        "home", "enter_session_code", "consent", "consent_declined", "demographics",
        "instructions", "comprehension", "profile", "final_score", "done",
    )]
    pages += [(f"pre_question_{i}", 1) for i in range(len(get_display_pre_sections("ro")))]
    pages += [(f"post_question_{i}", 25) for i in range(len(get_display_post_sections("ro")))]
    pages += [("simulation", month) for month in range(1, 25)]
    pages += [("month_feedback", 1), ("consent_no_battery", 1)]
    output = Path("artifacts/ui-review/diacritics")
    output.mkdir(parents=True, exist_ok=True)
    with live_app() as (base, manager, service, _repository), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for index, (name, month) in enumerate(pages):
            state = ParticipantState.initial(SCENARIO_VERSION)
            state.session_id = str(uuid.uuid4())
            state.language = "ro"
            state.page = "consent" if name == "consent_no_battery" else name
            state.month = month
            state.experimental_condition = "C5" if name == "consent_no_battery" else "C1"
            state.treatment_bound = True
            if name == "month_feedback":
                state.page = "simulation"
                state = submit_month_decision(state, month_data=get_month(1), payment=0).state
            key = f"unicode-{index}".ljust(64, "x")
            service.create_session(state, account_key=key, request_id=f"unicode-seed-{index}")
            principal = ParticipantPrincipal(key, bound_session_id=state.session_id)
            context = _context(browser, base, manager, principal)
            page = context.new_page()
            page.goto(base)
            page.wait_for_selector("#app[data-view]")
            text = page.locator("#app").inner_text()
            assert "\ufffd" not in text, name
            assert not re.search(r"\w\?\w", text), name
            assert not re.search(r"[ÃÄÈ][\x80-\xbf]", text), name
            assert page.locator("html").get_attribute("lang") == "ro"
            if name.startswith("consent") and name != "consent_declined":
                assert "consimțământ informat" in text
                assert "Nu ți se va cere" in text
            page.screenshot(path=str(output / f"{name}-{month}.png"), full_page=True)
            context.close()
        browser.close()


def test_login_homepage_has_no_prolific_access_denied_notice():
    with live_app() as (base, _manager, _service, _repository), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(base)
        page.get_by_role("link", name="Continue with Google").wait_for()
        assert "Access denied" not in page.locator("#app").inner_text()
        browser.close()


def test_page_changes_keep_keyboard_focus_and_language_control_usable():
    principal = ParticipantPrincipal("k" * 64)
    with live_app() as (base, manager, _service, _repository), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = _context(browser, base, manager, principal)
        page = context.new_page(); page.goto(base); page.wait_for_selector("#start")
        page.locator("#start").press("Enter"); page.wait_for_selector('[data-view="consent"]')
        assert page.locator("#app h1").count() == 1
        assert page.locator("#app h1").evaluate("el => el === document.activeElement")
        page.locator("#language").focus(); page.select_option("#language", "ro")
        page.wait_for_selector('html[lang="ro"]')
        assert page.locator("#language").evaluate("el => el === document.activeElement")
        page.locator(".skip-link").focus(); page.locator(".skip-link").press("Enter")
        assert page.locator("#app").evaluate("el => el === document.activeElement")
        assert page.locator(".skip-link").inner_text() == "Sari la conținut"
        context.close(); browser.close()


def test_mobile_decision_shortcut_and_header_touch_targets():
    repository = InMemoryExperimentRepository()
    state = ParticipantState.initial(SCENARIO_VERSION)
    state.session_id = str(uuid.uuid4()); state.page = "simulation"; state.treatment_bound = True
    ExperimentService(repository).create_session(state, account_key="j" * 64, request_id="mobile-seed")
    principal = ParticipantPrincipal("j" * 64, is_admin=True, bound_session_id=state.session_id)
    with live_app(repository=repository) as (base, manager, _service, _repository), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = _context(browser, base, manager, principal, viewport={"width": 320, "height": 844})
        page = context.new_page(); page.goto(base); page.wait_for_selector("#decision")
        for selector in ["#language", "#logout", '.account-bar a[href="/admin"]']:
            assert page.locator(selector).bounding_box()["height"] >= 44
        page.locator(".simulation-jump").press("Enter")
        assert page.locator("#decision-heading").evaluate("el => el === document.activeElement")
        bounds = page.locator("#decision-heading").bounding_box()
        assert bounds["y"] >= page.locator(".account-bar").bounding_box()["height"]
        assert bounds["y"] < 200
        page.locator("#payment").fill("0"); page.locator("#decision button").press("Enter")
        page.wait_for_selector('[data-view="month_feedback"]')
        assert page.locator("#app h1").evaluate("el => el === document.activeElement")
        context.close(); browser.close()


@pytest.mark.parametrize("language", ["en", "ro"])
def test_admin_condition_help_is_readable_and_preserves_condition_codes(language):
    admin_repository = MemoryAdminRepository()
    principal = ParticipantPrincipal("a" * 64, email="admin@example.test", is_admin=True)
    with live_app(admin_repository=admin_repository) as (base, manager, _service, _repository), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = _context(browser, base, manager, principal, viewport={"width": 320, "height": 844})
        context.add_init_script(f"sessionStorage.setItem('sim.language','{language}')")
        page = context.new_page(); page.goto(base + "/admin"); page.wait_for_selector("#create-admin")
        assert page.locator('label[for="condition"]').is_visible()
        page.select_option('[name="condition"]', "C8")
        assert page.locator("#condition-description").is_visible()
        assert ("without psychometric questionnaires" if language == "en" else "fără baterie psihometrică") in page.locator("#condition-description").inner_text()
        assert page.locator("html").get_attribute("lang") == language
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        page.locator("#create-admin button").click(); page.wait_for_selector(".admin-session")
        assert admin_repository.sessions[0]["experimental_condition"] == "C8"
        context.close(); browser.close()


def test_instruction_markup_is_hidden_and_wrapper_content_remains_readable():
    repository = InMemoryExperimentRepository()
    state = ParticipantState.initial(SCENARIO_VERSION)
    state.session_id = str(uuid.uuid4()); state.page = "instructions"; state.treatment_bound = True
    ExperimentService(repository).create_session(state, account_key="i" * 64, request_id="instructions-seed")
    principal = ParticipantPrincipal("i" * 64, bound_session_id=state.session_id)
    with live_app(repository=repository) as (base, manager, _service, _repository), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = _context(browser, base, manager, principal)
        page = context.new_page(); page.goto(base); page.wait_for_selector('[data-view="instructions"]')
        content = page.locator(".rich").inner_text()
        assert "<div" not in content and "border-radius:" not in content
        assert "Monthly decision steps" in content
        assert "Enter the amount you want to pay toward the loan for that month." in content
        assert page.locator(".rich h1").count() == 1
        context.close(); browser.close()


def test_mobile_account_bar_stays_compact_and_controls_remain_usable():
    principal = ParticipantPrincipal("8" * 64, email="participant@example.com", display_name="Nutzu 999", is_admin=True)
    with live_app() as (base, manager, _service, _repository), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = _context(browser, base, manager, principal, viewport={"width": 390, "height": 844})
        page = context.new_page(); page.goto(base)
        account = page.locator("#account-bar"); account.wait_for()
        assert account.bounding_box()["height"] < 80
        assert page.locator("#language").bounding_box()["width"] < 100
        assert page.locator("#logout").is_visible() and page.get_by_role("link", name="Admin").is_visible()
        context.close(); browser.close()


@pytest.mark.parametrize(
    ("condition", "expected_text"),
    [
        ("C1", "performance bonus starts from 0 points"),
        ("C2", "performance bonus starts from 0 points"),
        ("C3", "provisional performance bonus starts from 3 points"),
        ("C4", "provisional performance bonus starts from 3 points"),
    ],
)
def test_consent_restores_blue_treatment_framing_notice(condition, expected_text):
    principal = ParticipantPrincipal((condition.lower() * 32)[:64])
    repository = InMemoryExperimentRepository(); service = ExperimentService(repository)
    state = ParticipantState.initial(SCENARIO_VERSION); state.session_id = str(uuid.uuid4()); state.page = "consent"
    for key, value in condition_config(condition).items(): setattr(state, key, value)
    state.treatment_bound = True
    service.create_session(state, account_key=principal.account_key, request_id="seed-framing")
    principal = ParticipantPrincipal(principal.account_key, bound_session_id=state.session_id)
    with live_app(repository=repository) as (base, manager, _service, _repo), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True); context = _context(browser, base, manager, principal)
        page = context.new_page(); page.goto(base); page.wait_for_selector('[data-view="consent"]')
        notice = page.locator(".notice.info")
        assert notice.count() == 1 and expected_text in notice.inner_text()
        assert page.locator(".notice.success").count() == 0
        assert "rgb(220, 234, 243)" == notice.evaluate("node => getComputedStyle(node).backgroundColor")
        assert notice.evaluate("node => node.nextElementSibling?.classList.contains('consent-content')") is True
        assert notice.bounding_box()["y"] < page.locator(".consent-content").bounding_box()["y"]
        context.close(); browser.close()


def _answer_questionnaire(page, *, chapter, first_question):
    form = page.locator("#quiz")
    assert page.locator(".chapter-heading").inner_text() == f"Chapter {chapter}"
    prompts = page.locator("#quiz fieldset.question legend").all_inner_texts()
    assert prompts and prompts[0].startswith(f"{first_question}. ")
    for offset, prompt in enumerate(prompts):
        assert prompt.startswith(f"{first_question + offset}. ")
    version = page.locator("#app").get_attribute("data-version")
    names = form.locator('input[type="radio"]').evaluate_all("els => [...new Set(els.map(e => e.name))]")
    for name in names:
        if name == "attention_response": form.locator(f'input[name="{name}"][value="3"]').check()
        else: form.locator(f'input[name="{name}"]').first.check()
    for area in form.locator("textarea").all(): area.fill("Browser parity feedback")
    form.locator('button[type="submit"]').click()
    page.wait_for_function("version => document.querySelector('#app')?.dataset.version !== version", arg=version)
    return len(prompts)


def test_complete_24_month_participant_browser_journey_and_refresh_recovery():
    principal = ParticipantPrincipal("a" * 64, email="participant@example.com", display_name="Participant")
    with live_app() as (base, manager, _service, repository), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = _context(browser, base, manager, principal); page = context.new_page(); page.goto(base)
        page.locator("#start").click()
        page.wait_for_selector('[data-view="consent"]')
        for item in page.locator('#consent input[type="checkbox"]').all(): item.check()
        page.locator('#consent button[type="submit"]').click()
        page.wait_for_selector('[data-view="demographics"]')
        page.locator("#demo input[type=number]").fill("30")
        page.locator("#demo input[type=text]").fill("Romania")
        for select in page.locator("#demo select").all(): select.select_option(index=1)
        page.locator('#demo button[type="submit"]').click()
        page.wait_for_selector('[data-view="questionnaire_section"]')
        pre_chapter, pre_question = 1, 1
        while page.locator("#quiz").count():
            pre_question += _answer_questionnaire(page, chapter=pre_chapter, first_question=pre_question)
            pre_chapter += 1
        assert (pre_chapter, pre_question) == (23, 164)
        page.wait_for_selector('[data-view="instructions"]')
        page.locator(".card .actions button").click()  # instructions
        page.wait_for_selector('[data-view="profile"]')
        profile_text = page.locator(".card").inner_text()
        assert "|---|" not in profile_text and "**" not in profile_text
        assert page.locator(".rich-table").count() >= 1
        page.locator(".card .actions button").click()  # profile
        page.wait_for_selector('[data-view="simulation"]')
        for month in range(1, 25):
            assert page.locator(".available-before-payment").count() == 1
            assert "Money available before loan payment" in page.locator(".available-before-payment").inner_text()
            assert "initial available balance + total income - current expenses - loan interest - overdraft interest" in page.locator(".decision-row.formula").inner_text()
            assert page.locator(".opening-balance").count() == (1 if month == 1 else 0)
            if month == 1:
                assert "150.00" in page.locator(".opening-balance").inner_text()
            decision = page.locator("#decision")
            if decision.locator("input[name=payment]").count():
                decision.locator("input[name=payment]").fill("999999" if month == 1 else "0")
            decision.locator('button[type="submit"]').click()
            page.wait_for_selector('[data-view="month_feedback"]')
            feedback_text = page.locator(".card").inner_text()
            assert "**" not in feedback_text and "###" not in feedback_text and "{value}" not in feedback_text
            page.locator(".card .actions button").last.click()
            page.wait_for_selector('[data-view="simulation"]' if month < 24 else '[data-view="questionnaire_section"]')
        post_chapter, post_question = 1, 1
        while page.locator("#quiz").count():
            post_question += _answer_questionnaire(page, chapter=post_chapter, first_question=post_question)
            post_chapter += 1
        assert (post_chapter, post_question) == (3, 46)
        page.wait_for_selector('[data-view="final_score"]')
        assert "points" in page.locator(".score-card + .grid").inner_text()
        assert "GBP" not in page.locator("#app").inner_text()
        page.locator(".card .actions button").click()  # final score acknowledgement
        page.wait_for_selector('[data-view="completion"]')
        assert "points" in page.locator(".card .grid").inner_text()
        page.wait_for_selector("#finalize", state="detached")
        assert "Thank" in page.locator("h1").inner_text()
        assert len(repository.month_results(next(iter(repository._sessions)))) == 24
        page.reload(); page.wait_for_load_state("networkidle")
        assert "Thank" in page.locator("h1").inner_text()
        assert page.locator("#finalize").count() == 0
        context.close(); browser.close()


@pytest.mark.parametrize("condition,score_visible", [("C1", True), ("C2", False), ("C3", True), ("C4", False)])
def test_browser_feedback_respects_all_treatment_blindness(condition, score_visible):
    principal = ParticipantPrincipal((condition.lower() * 32)[:64])
    repository = InMemoryExperimentRepository(); service = ExperimentService(repository)
    state = ParticipantState.initial(SCENARIO_VERSION); state.session_id = str(uuid.uuid4()); state.page = "simulation"
    treatment = condition_config(condition)
    for key, value in treatment.items(): setattr(state, key, value)
    state.treatment_bound = True
    service.create_session(state, account_key=principal.account_key, request_id="seed")
    principal = ParticipantPrincipal(principal.account_key, bound_session_id=state.session_id)
    with live_app(repository=repository) as (base, manager, _service, _repo), sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True); context=_context(browser,base,manager,principal); page=context.new_page(); page.goto(base)
        page.wait_for_selector('[data-view="simulation"]')
        page.locator("#decision input[name=payment]").fill("0"); page.locator('#decision button[type="submit"]').click()
        page.wait_for_selector('[data-view="month_feedback"]')
        assert (page.locator(".score-card").count() == 1) is score_visible
        if score_visible:
            assert "Monthly score" in page.locator(".score-total").inner_text()
            assert "points lost" not in page.locator(".score-total").inner_text().lower()
        html = page.locator(".card").inner_html()
        assert condition not in html and "experimental_condition" not in html
        context.close(); browser.close()


def test_admin_browser_authorization_creation_and_polling_view():
    admin_repository = MemoryAdminRepository()
    principal = ParticipantPrincipal("d" * 64, email="admin@example.com", display_name="Admin", is_admin=True)
    with live_app(admin_repository=admin_repository) as (base, manager, _service, _repo), sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True); context=_context(browser,base,manager,principal); page=context.new_page(); page.goto(f"{base}/admin")
        page.locator("#create-admin select").select_option("C4"); page.locator('#create-admin button[type="submit"]').click()
        page.wait_for_selector(".admin-session")
        assert "C4" in page.locator(".admin-session").inner_text()
        page.on("dialog",lambda dialog:dialog.accept()); page.locator("[data-cancel]").click()
        context.close(); browser.close()


def test_admin_participant_results_show_each_saved_condition():
    admin_repository = MemoryAdminRepository()
    study = admin_repository.create_study_session("admin@example.com", "C8")
    admin_repository.participants[study["id"]] = [
        {"participant_code": f"P00{i}", "experimental_condition": f"C{i}"}
        for i in range(1, 5)
    ]
    principal = ParticipantPrincipal("d" * 64, email="admin@example.com", is_admin=True)
    with live_app(admin_repository=admin_repository) as (base, manager, _service, _repo), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = _context(browser, base, manager, principal)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(f"{base}/admin/participants")
        page.wait_for_selector(".admin-results tbody tr")
        assert "condition" in page.locator(".admin-results thead").inner_text().lower()
        for i in range(1, 5):
            row = page.locator(".admin-results tbody tr").filter(has_text=f"P00{i}")
            assert row.locator("td").nth(3).inner_text() == f"C{i}"
        assert not errors
        context.close()
        browser.close()


@pytest.mark.parametrize("phase, destination", [("pre", "instructions"), ("post", "final_score")])
def test_psychometrics_skip_is_visible_only_to_admin_and_skips_unanswered_form(phase, destination):
    repository = InMemoryExperimentRepository()
    service = ExperimentService(repository)
    state = ParticipantState.initial(SCENARIO_VERSION)
    state.session_id = str(uuid.uuid4())
    state.page = f"{phase}_question_0"
    state.language = "ro"
    for key, value in condition_config("C1").items(): setattr(state, key, value)
    state.treatment_bound = True
    service.create_session(state, account_key="s" * 64, request_id="skip-browser-seed")
    with live_app(repository=repository) as (base, manager, _service, _repo), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        participant = ParticipantPrincipal("s" * 64, bound_session_id=state.session_id)
        context = _context(browser, base, manager, participant)
        page = context.new_page(); page.goto(base)
        page.wait_for_selector("#quiz")
        assert page.locator("#skip-psychometrics").count() == 0
        context.close()
        admin = ParticipantPrincipal("s" * 64, is_admin=True, bound_session_id=state.session_id)
        context = _context(browser, base, manager, admin, viewport={"width": 390, "height": 844})
        page = context.new_page(); page.goto(base)
        page.wait_for_selector("#skip-psychometrics")
        assert page.locator("#skip-psychometrics").inner_text() == "SKIP PSYCHOMETRICS"
        assert page.locator("#quiz input:checked").count() == 0
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        output = Path("artifacts/ui-review"); output.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(output / f"admin-skip-psychometrics-{phase}.png"))
        page.locator("#skip-psychometrics").click()
        page.wait_for_selector(f'[data-view="{destination}"]')
        assert service.load_session(state.session_id).answers[f"admin_skipped_psychometrics_{phase}"] is True
        page.reload(); page.wait_for_selector(f'[data-view="{destination}"]')
        context.close(); browser.close()


def test_admin_can_repeat_simulator_from_completed_screen():
    principal = ParticipantPrincipal("r" * 64, email="admin@example.com", display_name="Admin", is_admin=True)
    repository = InMemoryExperimentRepository()
    service = ExperimentService(repository)
    first = service.bootstrap_session(principal, expected_version=0, language="en", request_id="first").state
    completed = first.copy()
    completed.page = "done"
    completed.submission_finalized = True
    completed.saved = True
    completed.final_score = 82.0
    repository.replace_state_and_ledger(completed)
    repository._accounts[principal.account_key] = first.session_id
    repository._completed_accounts.add(principal.account_key)
    bound = ParticipantPrincipal(**{**principal.__dict__, "bound_session_id": first.session_id})

    with live_app(repository=repository) as (base, manager, _service, _repo), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = _context(browser, base, manager, bound)
        page = context.new_page()
        page.goto(base)
        page.wait_for_selector('[data-view="completion"]')
        assert page.locator("#admin-repeat").is_visible()
        page.locator("#admin-repeat").click()
        page.wait_for_selector('[data-view="home"]')
        assert len(repository._sessions) == 2
        assert repository._accounts[principal.account_key] != first.session_id
        page.reload()
        page.wait_for_selector('[data-view="home"]')
        context.close(); browser.close()


def test_browser_language_consent_decline_and_reconsider_are_authoritative():
    principal = ParticipantPrincipal("e" * 64, display_name="Participant")
    with live_app() as (base, manager, _service, repository), sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True); context=_context(browser,base,manager,principal); page=context.new_page(); page.goto(base)
        old_version=page.locator("#app").get_attribute("data-version")
        page.locator("#language").select_option("ro")
        page.wait_for_function("v => document.querySelector('#app').dataset.version !== v",arg=old_version)
        assert next(iter(repository._sessions.values())).language == "ro"
        page.locator("#start").click(); page.wait_for_selector('[data-view="consent"]')
        page.locator("#decline").click(); page.wait_for_selector('[data-view="consent_declined"]')
        page.locator(".card button").click(); page.wait_for_selector('[data-view="consent"]')
        page.reload(); page.wait_for_selector('[data-view="consent"]')
        assert page.locator("#language").input_value() == "ro"
        context.close(); browser.close()


def test_browser_response_loss_retry_reuses_action_and_stale_tab_reloads_authority():
    principal = ParticipantPrincipal("f" * 64)
    with live_app() as (base, manager, _service, repository), sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True); context=_context(browser,base,manager,principal); first=context.new_page(); first.goto(base)
        second=context.new_page(); second.goto(base); second.wait_for_selector("#start")
        intercepted={"done":False}
        def lose_response(route):
            if not intercepted["done"]:
                intercepted["done"]=True; route.fetch(); route.abort()
            else: route.continue_()
        first.route("**/start",lose_response)
        first.locator("#start").click(); first.wait_for_selector("text=Retry saved action")
        assert next(iter(repository._sessions.values())).page == "consent"
        first.get_by_text("Retry saved action").click(); first.wait_for_selector('[data-view="consent"]')
        assert next(iter(repository._sessions.values())).state_version == 1
        second.locator("#start").click(); second.wait_for_selector('[data-view="consent"]')
        assert next(iter(repository._sessions.values())).state_version == 1
        context.close(); browser.close()


def test_browser_503_preserves_same_action_for_safe_retry():
    principal = ParticipantPrincipal("9" * 64)
    with live_app() as (base, manager, _service, repository), sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True); context=_context(browser,base,manager,principal); page=context.new_page(); page.goto(base)
        repository.fail_next("save_stage", phase="before")
        page.locator("#start").click(); page.wait_for_selector("text=Retry saved action")
        assert next(iter(repository._sessions.values())).page == "home"
        page.get_by_text("Retry saved action").click(); page.wait_for_selector('[data-view="consent"]')
        assert next(iter(repository._sessions.values())).state_version == 1
        context.close(); browser.close()


def test_browser_comprehension_correctness_stays_server_side():
    principal = ParticipantPrincipal(
        "7" * 64, identity_kind="prolific", prolific_pid="pid", prolific_study_id="study", prolific_session_id="attempt"
    )
    repository=InMemoryExperimentRepository(); service=ExperimentService(repository)
    state=ParticipantState.initial(SCENARIO_VERSION); state.session_id=str(uuid.uuid4()); state.page="comprehension"; state.prolific_mode=True
    service.create_session(state,account_key=principal.account_key,request_id="seed")
    principal=ParticipantPrincipal(**{**principal.__dict__,"bound_session_id":state.session_id})
    with live_app(repository=repository) as (base,manager,_service,_repo), sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True); context=_context(browser,base,manager,principal); page=context.new_page(); page.goto(base)
        page.wait_for_selector('[data-view="comprehension"]')
        assert "correct" not in page.content().lower()
        groups=page.locator('#comp input[type="radio"]').evaluate_all("els => [...new Set(els.map(e=>e.name))]")
        for name in groups: page.locator(f'#comp input[name="{name}"]').first.check()
        page.locator('#comp button[type="submit"]').click(); page.wait_for_selector('[data-view="profile"]')
        assert service.load_session(state.session_id).comprehension_passed
        context.close(); browser.close()


@pytest.mark.parametrize("motion", ["normal", "skip", "reduce", "reduce-midway"])
def test_next_month_narration_reveal_preserves_reading_and_decision_controls(motion):
    repository = InMemoryExperimentRepository()
    service = ExperimentService(repository)
    state = ParticipantState.initial(SCENARIO_VERSION)
    state.session_id = str(uuid.uuid4()); state.page = "simulation"
    for key, value in condition_config("C1").items(): setattr(state, key, value)
    state.treatment_bound = True
    service.create_session(state, account_key="m" * 64, request_id="motion-seed")
    principal = ParticipantPrincipal("m" * 64, bound_session_id=state.session_id)
    with live_app(repository=repository) as (base, manager, _service, _repo), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = _context(browser, base, manager, principal)
        page = context.new_page()
        page.emulate_media(reduced_motion="reduce" if motion == "reduce" else "no-preference")
        page.goto(base); page.wait_for_selector("#decision")
        assert page.locator(".narrative-word").count() == 0  # No reveal on initial load.
        page.locator("#decision input").fill("0")
        page.locator("#decision button").click(); page.wait_for_selector('[data-view="month_feedback"]')
        page.locator(".card .actions button").click(); page.wait_for_selector('[data-view="simulation"][data-month="2"]')
        passage = page.locator(".narrative-copy").text_content()
        assert passage and "The bills arrive again" in passage
        assert page.locator("#decision input").is_enabled()
        assert page.locator("#decision button").is_enabled()
        assert page.locator(".decision-workspace").evaluate("el => el.getAnimations({subtree:true}).length") == 0
        if motion == "reduce":
            assert page.locator(".narrative-word").count() == 0
        else:
            assert page.locator(".narrative-word").count() > 0
            assert page.locator(".narrative-copy").evaluate("el => Math.max(...el.getAnimations({subtree:true}).map(a => a.effect.getComputedTiming().endTime))") <= 1800
            if motion == "skip": page.locator(".narrative-copy").click()
            if motion == "reduce-midway": page.emulate_media(reduced_motion="reduce")
            page.wait_for_selector(".narrative-word", state="detached", timeout=2500)
            assert page.locator(".narrative-copy").text_content() == passage
        page.reload(); page.wait_for_selector("#decision")
        assert page.locator(".narrative-word").count() == 0  # No replay on recovery.
        context.close(); browser.close()
