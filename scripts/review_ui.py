"""Repeatable UI review using real routes and isolated in-memory research data.

Run: python scripts/review_ui.py before|after
Screenshots and a geometry/error manifest are saved under artifacts/ui-review.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import importlib.util
import json
from playwright.sync_api import sync_playwright
from sim_app.application.principal import ParticipantPrincipal

spec = importlib.util.spec_from_file_location('browser_tests', Path(__file__).resolve().parents[1] / 'tests/test_phase5_browser.py')
suite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(suite)
out = Path('artifacts/ui-review') / (sys.argv[1] if len(sys.argv) > 1 else 'after')
out.mkdir(parents=True, exist_ok=True)
manifest = []

admin_repo = suite.MemoryAdminRepository()
with suite.live_app(admin_repository=admin_repo) as (base, manager, service, repo), sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    principal = ParticipantPrincipal('a' * 64, email='review@example.test', display_name='Review participant', is_admin=True)
    context = suite._context(browser, base, manager, principal)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))

    def capture(name, mobile=True):
        # Static review captures the complete passage; motion gets a separate test.
        page.wait_for_selector('.narrative-word', state='detached', timeout=4000)
        for width, height, suffix in [(1440, 1000, 'desktop'), (390, 844, 'mobile')] if mobile else [(1440, 1000, 'desktop')]:
            page.set_viewport_size({'width': width, 'height': height})
            page.screenshot(path=str(out / f'{name}-{suffix}.png'), full_page=True)
            manifest.append({'page': name, 'viewport': width, 'overflow': page.evaluate('document.documentElement.scrollWidth > innerWidth'), 'height': page.evaluate('document.documentElement.scrollHeight')})
        page.set_viewport_size({'width': 1440, 'height': 1000})

    def submit(selector):
        version = page.locator('#app').get_attribute('data-version')
        page.locator(selector).click()
        page.wait_for_function('v => document.querySelector("#app").dataset.version !== v', arg=version)

    page.goto(base); page.wait_for_selector('#start'); capture('home')
    page.locator('details:not(.account-menu) summary').click(); capture('coded-session')
    submit('#start'); capture('consent')
    submit('#decline'); capture('consent-declined')
    submit('.card .actions button')
    for checkbox in page.locator('#consent input').all(): checkbox.check()
    submit('#consent button[type=submit]'); capture('demographics')
    page.locator('#demo input[type=number]').fill('30'); page.locator('#demo input[type=text]').fill('Romania')
    for select in page.locator('#demo select').all(): select.select_option(index=1)
    submit('#demo button')
    chapter = 0
    while page.locator('#quiz').count():
        chapter += 1; capture(f'pre-questionnaire-{chapter:02}')
        names = page.locator('#quiz input[type=radio]').evaluate_all('els => [...new Set(els.map(e => e.name))]')
        for name in names: page.locator(f'input[name="{name}"]').first.check()
        submit('#quiz button')
    capture('instructions'); submit('.card .actions button')
    capture('profile'); submit('.card .actions button')
    for month in range(1, 25):
        page.wait_for_selector('[data-view=simulation]'); capture(f'month-{month:02}')
        if month == 1:
            page.locator('details').filter(has=page.locator('.money-table')).locator('summary').click(); capture('budget-expanded')
        payment = page.locator('#decision input[name=payment]')
        if payment.count(): payment.fill('999999' if month == 1 else '0')
        submit('#decision button'); capture(f'feedback-{month:02}')
        submit('.card .actions button')
    chapter = 0
    while page.locator('#quiz').count():
        chapter += 1; capture(f'post-questionnaire-{chapter:02}')
        names = page.locator('#quiz input[type=radio]').evaluate_all('els => [...new Set(els.map(e => e.name))]')
        for name in names: page.locator(f'input[name="{name}"][value="3"]' if name == 'attention_response' else f'input[name="{name}"]').first.check()
        for area in page.locator('textarea').all(): area.fill('UI review')
        submit('#quiz button')
    capture('final-score'); submit('.card .actions button'); page.wait_for_selector('#finalize', state='detached'); capture('completion')
    page.goto(base + '/admin'); page.wait_for_selector('#create-admin'); capture('admin-empty')
    page.locator('#create-admin button').click(); page.wait_for_selector('.admin-session'); capture('admin-sessions')
    page.goto(base + '/admin/participants'); page.wait_for_selector('#participant-results .notice'); capture('admin-results-empty')
    admin_repo.participants[admin_repo.sessions[0]['id']] = [
        {'participant_code': 'P001', 'status': 'completed', 'summary': {'final_score': 82.5, 'performance_bonus_gbp': 2.48}},
        {'participant_code': 'P002', 'status': 'in_progress', 'checkpoint': {'page': 'simulation', 'month': 12}},
        {'prolific_pid': 'review-participant-0003', 'status': 'completed', 'summary': {'final_score': 67.8, 'performance_bonus_gbp': 2.03, 'total_payout_gbp': 6.03}},
    ]
    page.reload(); page.wait_for_selector('.admin-results'); capture('admin-results-populated')
    page.goto(base + '/admin'); page.wait_for_selector('.participant-row'); capture('admin-progress')
    context.close()
    page = browser.new_page(); page.goto(base); page.wait_for_selector('a[href="/auth/google/login"]'); capture('login')
    page.goto(base + '/?prolific_error=missing_params'); page.wait_for_selector('.notice.error'); capture('prolific-error')
    for index, (name, stage, options) in enumerate([
        ('study-session', 'enter_session_code', {}),
        ('comprehension', 'comprehension', {'prolific_mode': True}),
        ('comprehension-retry', 'comprehension', {'prolific_mode': True, 'comprehension_attempts': 1}),
        ('already-completed', 'already_completed', {}),
        ('simulation-ro', 'simulation', {'language': 'ro'}),
        ('simulation-repaid', 'simulation', {'loan_paid': True}),
        ('simulation-overdraft', 'simulation', {'overdraft_used': True}),
        ('simulation-blocked', 'simulation', {'overdraft_used': True, 'month': 17}),
        ('feedback-hidden', 'simulation', {'condition': 'C2'}),
    ]):
        import uuid
        st = suite.ParticipantState.initial(suite.SCENARIO_VERSION)
        st.session_id = str(uuid.uuid4()); st.page = stage
        for key, value in suite.condition_config(options.get('condition', 'C1')).items(): setattr(st, key, value)
        st.treatment_bound = True
        for key, value in options.items():
            if key not in {'loan_paid', 'overdraft_used', 'condition'}: setattr(st, key, value)
        if options.get('loan_paid'): st.loan.balance = 0
        if options.get('overdraft_used'): st.overdraft.balance = 3000; st.month = options.get('month', 10)
        account = str(index + 1) * 64
        service.create_session(st, account_key=account, request_id='review-seed')
        ctx = suite._context(browser, base, manager, ParticipantPrincipal(account, bound_session_id=st.session_id))
        page = ctx.new_page(); page.goto(base); page.wait_for_selector('[data-view]'); capture(name)
        if name == 'feedback-hidden':
            page.locator('#decision input').fill('0'); submit('#decision button'); capture(name + '-result')
        if name == 'simulation-ro':
            for width in [320, 768, 1024]:
                page.set_viewport_size({'width': width, 'height': 900})
                page.screenshot(path=str(out / f'{name}-{width}.png'), full_page=True)
                manifest.append({'page': name, 'viewport': width, 'overflow': page.evaluate('document.documentElement.scrollWidth > innerWidth')})
        ctx.close()
    browser.close()
    (out / 'manifest.json').write_text(json.dumps({'screens': manifest, 'browser_errors': errors}, indent=2))
    print(f'{len(manifest)} screenshots; {len(errors)} browser errors; {sum(x["overflow"] for x in manifest)} overflows. Saved to {out}')
