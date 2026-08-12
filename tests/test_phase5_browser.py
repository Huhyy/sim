from __future__ import annotations

import socket
import threading
import time
import uuid
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


def _answer_questionnaire(page):
    form = page.locator("#quiz")
    version = page.locator("#app").get_attribute("data-version")
    names = form.locator('input[type="radio"]').evaluate_all("els => [...new Set(els.map(e => e.name))]")
    for name in names:
        if name == "attention_response": form.locator(f'input[name="{name}"][value="3"]').check()
        else: form.locator(f'input[name="{name}"]').first.check()
    for area in form.locator("textarea").all(): area.fill("Browser parity feedback")
    form.locator('button[type="submit"]').click()
    page.wait_for_function("version => document.querySelector('#app')?.dataset.version !== version", arg=version)


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
        while page.locator("#quiz").count(): _answer_questionnaire(page)
        page.wait_for_selector('[data-view="instructions"]')
        page.locator(".card .actions button").click()  # instructions
        page.wait_for_selector('[data-view="profile"]')
        profile_text = page.locator(".card").inner_text()
        assert "|---|" not in profile_text and "**" not in profile_text
        assert page.locator(".rich-table").count() >= 1
        page.locator(".card .actions button").click()  # profile
        page.wait_for_selector('[data-view="simulation"]')
        for month in range(1, 25):
            decision = page.locator("#decision")
            if decision.locator("input[name=payment]").count():
                decision.locator("input[name=payment]").fill("999999" if month == 1 else "0")
            decision.locator('button[type="submit"]').click()
            page.wait_for_selector('[data-view="month_feedback"]')
            feedback_text = page.locator(".card").inner_text()
            assert "**" not in feedback_text and "###" not in feedback_text and "{value}" not in feedback_text
            page.locator(".card .actions button").last.click()
            page.wait_for_selector('[data-view="simulation"]' if month < 24 else '[data-view="questionnaire_section"]')
        while page.locator("#quiz").count(): _answer_questionnaire(page)
        page.wait_for_selector('[data-view="final_score"]')
        page.locator(".card .actions button").click()  # final score acknowledgement
        page.wait_for_selector('[data-view="completion"]')
        page.locator("#finalize").click()
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
