import os
import streamlit as st

from sim_app.session.streamlit_secrets import configure_from_streamlit

configure_from_streamlit(st.secrets)

from sim_app.auth import current_account_key, current_user_email, is_admin_user, is_logged_in
from sim_app.application.errors import ExperimentError
from sim_app.content.tables import get_month
from sim_app.content.questions import PRE_SECTIONS as PRE_SECTIONS_RO
from sim_app.content.questions import POST_SECTIONS as POST_SECTIONS_RO
from sim_app.content.translations import (
    ensure_language,
    get_category_label,
    get_display_post_sections,
    get_display_pre_sections,
    get_language,
    get_localized_narrative,
    set_language,
    t,
)
from sim_app.config import REPEAT_SCENARIO_DEV_MODE, SCENARIO_VERSION
from sim_app.config import PROLIFIC_MODE_ENABLED
from sim_app.domain.experimental_conditions import condition_options
from sim_app.prolific import has_any_prolific_param, load_prolific_params, prolific_params_complete
from sim_app.prolific.identity import prolific_study_allowed
from sim_app.persistence.study_sessions import (
    cancel_admin_study_session,
    create_admin_study_session,
    list_admin_study_sessions,
    list_participant_sessions_for_study_session,
    load_admin_study_session_by_code,
)
from sim_app.session.manager import bootstrap_authenticated_session, ensure_current_scenario_version, start_new_scenario
from sim_app.session.service_provider import get_experiment_service
from sim_app.session.streamlit_service import commit_command as commit_streamlit_command
from sim_app.session.streamlit_service import commit_quality_state as commit_streamlit_quality_state
from sim_app.session.streamlit_service import commit_state as commit_streamlit_state
from sim_app.session.streamlit_service import navigate_committed
from sim_app.ui.components.account import render_account_menu as render_account_menu_component
from sim_app.ui.components.language import render_language_selector as render_language_selector_component
from sim_app.ui.context import make_ui_context
from sim_app.ui.pages.login import render_login_page as render_login_page_component
from sim_app.ui.pages.router import render_current_page

DEV = os.getenv("SCENARIO_DEV", "").lower() == "true"
ENABLE_PARENT_DOM_HACKS = False
experiment_service = get_experiment_service()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Manrope:wght@400;500;600;700&family=Roboto:wght@500&display=swap');

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
[data-testid="stToolbar"] {display: none !important;}
[data-testid="stDecoration"] {display: none !important;}
[data-testid="stStatusWidget"] {display: none !important;}
[data-testid="stAppDeployButton"] {display: none !important;}

:root {
    --scenario-bg-ink: #101c21;
    --scenario-bg-green: #152b2d;
    --scenario-bg-deep: #0c181a;
    --scenario-card: #fbf8f0;
    --scenario-card-border: rgba(223, 211, 181, 0.62);
    --scenario-text: #172b29;
    --scenario-muted: #586564;
    --scenario-green: #174b47;
    --scenario-soft-green: #e8efea;
    --scenario-rule: #e5decc;
    --scenario-warm: #d59b3c;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 12% 18%, rgba(213, 155, 60, 0.20), transparent 31rem),
        radial-gradient(circle at 84% 72%, rgba(20, 104, 98, 0.24), transparent 30rem),
        linear-gradient(132deg, var(--scenario-bg-ink) 0%, var(--scenario-bg-green) 46%, var(--scenario-bg-deep) 100%);
}

[data-testid="stMain"] {
    min-height: 100vh;
}

[data-testid="stMainBlockContainer"] {
    width: min(calc(100vw - 2rem), 68rem);
    max-width: 68rem;
    margin: clamp(1rem, 4vh, 2.4rem) auto;
    padding: clamp(1.35rem, 4vw, 2.45rem);
    border: 1px solid var(--scenario-card-border);
    border-radius: 1.75rem;
    background: var(--scenario-card);
    color: var(--scenario-text);
    box-shadow:
        0 28px 72px rgba(0, 0, 0, 0.34),
        0 2px 0 rgba(255, 255, 255, 0.75) inset;
}

.st-key-lang_ro button,
.st-key-lang_en button {
    min-height: 2.4rem;
    border-radius: 999px !important;
    font: 700 0.78rem/1 'Manrope', sans-serif !important;
}

.st-key-account_lang_en button,
.st-key-account_lang_ro button {
    min-height: 2.2rem;
    border-radius: 999px !important;
    font: 700 0.76rem/1 'Manrope', sans-serif !important;
}

.language-bar {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    margin-bottom: 1rem;
}

body:has(.st-key-auth_card) [data-testid="stMain"] {
    display: flex;
    align-items: center;
}

body:has(.st-key-auth_card) [data-testid="stMainBlockContainer"] {
    width: min(calc(100vw - 1.8rem), 52rem);
    max-width: 52rem;
    max-height: calc(100vh - 2rem);
    overflow-y: auto;
}

[data-testid="stMainBlockContainer"],
[data-testid="stMainBlockContainer"] p,
[data-testid="stMainBlockContainer"] li,
[data-testid="stMainBlockContainer"] label,
[data-testid="stMainBlockContainer"] input,
[data-testid="stMainBlockContainer"] textarea {
    font-family: 'Manrope', sans-serif;
}

[data-testid="stMainBlockContainer"] h1,
[data-testid="stMainBlockContainer"] h2,
[data-testid="stMainBlockContainer"] h3 {
    color: var(--scenario-text);
    letter-spacing: -0.025em;
}

[data-testid="stMainBlockContainer"] h1 {
    font-family: 'Fraunces', serif;
    font-weight: 600;
}

[data-testid="stMainBlockContainer"] p,
[data-testid="stMainBlockContainer"] li,
[data-testid="stMainBlockContainer"] label,
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] {
    color: var(--scenario-text);
}

[data-testid="stCaptionContainer"],
[data-testid="stMainBlockContainer"] small {
    color: var(--scenario-muted) !important;
}

[data-testid="stMetric"] {
    padding: 0.75rem 0.9rem;
    border: 1px solid #e1dac8;
    border-radius: 1rem;
    background: #fffaf0;
}

[data-testid="stMetricLabel"] p,
[data-testid="stMetricValue"] {
    color: var(--scenario-text) !important;
}

[data-testid="stTable"] {
    border: 1px solid #e0d8c6;
    border-radius: 1rem;
    overflow: hidden;
}

div[data-testid="stExpander"] {
    border-color: #d9d1bf !important;
    border-radius: 1rem !important;
    background: rgba(255, 252, 244, 0.74);
}

div[data-testid="stExpander"] summary p {
    color: var(--scenario-text) !important;
    font-weight: 700;
}

div[data-testid="stExpander"] details[open] > summary {
    background: #171c27 !important;
}

div[data-testid="stExpander"] details[open] > summary p,
div[data-testid="stExpander"] details[open] > summary span {
    color: var(--scenario-card) !important;
}

div[data-testid="stExpander"] details[open] > summary svg {
    color: var(--scenario-card) !important;
    fill: var(--scenario-card) !important;
}

.decision-card {
    margin-top: 1.1rem;
    padding: clamp(1rem, 2.4vw, 1.25rem);
    border: 1px solid #d9d1bf;
    border-radius: 1rem;
    background:
        linear-gradient(135deg, rgba(255, 250, 240, 0.96), rgba(238, 241, 234, 0.92));
    color: var(--scenario-text);
    box-shadow: 0 12px 30px rgba(23, 43, 41, 0.08);
}

.decision-card-title {
    margin-bottom: 0.95rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #e4ddcb;
    color: var(--scenario-green);
    font-weight: 800;
}

.decision-row {
    margin-bottom: 0.45rem;
    line-height: 1.45;
    font-weight: 700;
}

.decision-row:last-child {
    margin-bottom: 0;
}

.decision-row.positive {
    color: #176b4d;
}

.decision-row.risk {
    color: #b54842;
}

.decision-row.primary {
    margin-top: 0.82rem;
    padding-top: 0.82rem;
    border-top: 1px solid #e4ddcb;
    color: var(--scenario-green);
    font-weight: 800;
}

.decision-row.formula {
    margin-top: 0.72rem;
    color: #57615f;
    font-size: 0.88rem;
    font-weight: 600;
}

.auth-info {
    display: flex;
    gap: 0.72rem;
    align-items: flex-start;
    margin-top: 1.05rem;
    padding: 0.86rem 0.92rem;
    border: 1px solid #d5dad6;
    border-radius: 1rem;
    color: #57615f;
    background: #edf0ed;
    font: 500 0.76rem/1.55 'Manrope', sans-serif;
}

.auth-info-icon {
    display: grid;
    place-items: center;
    flex: 0 0 1.18rem;
    height: 1.18rem;
    margin-top: 0.08rem;
    border: 1.35px solid #53716d;
    border-radius: 50%;
    color: #466661;
    font: 700 0.76rem/1 'Manrope', sans-serif;
}

.payment-note {
    align-items: center;
    margin: 0.75rem 0 !important;
}

.payment-note span:last-child {
    font-size: 0.98rem;
    font-weight: 700;
    line-height: 1.2;
}

.payment-note .auth-info-icon {
    flex-basis: 1.35rem;
    height: 1.35rem;
    margin-top: 0;
    font-size: 0.88rem;
}

.payment-label {
    margin-top: 0.75rem;
    margin-bottom: 0.25rem;
    color: var(--scenario-text);
    font-size: 1.02rem;
    font-weight: 800;
}

.payment-button-gap {
    height: 0;
}

.payment-button-gap + div[data-testid="stButton"] {
    margin-top: 0 !important;
}

div[data-testid="stNumberInput"] input {
    background: #f6f0e5 !important;
    color: var(--scenario-text) !important;
    border-color: #d8cfbd !important;
}

div[data-testid="stNumberInput"] > div {
    background: #f6f0e5 !important;
    border-radius: 0.9rem !important;
}

.final-score-card {
    display: inline-flex;
    flex-direction: column;
    gap: 0.25rem;
    width: fit-content;
    min-width: 10.5rem;
    margin: 0.35rem 0 1.2rem;
    padding: 0.85rem 1rem;
    border: 1px solid rgba(207, 191, 153, 0.82);
    border-radius: 0.95rem;
    background: rgba(255, 250, 240, 0.72);
}

.final-score-label {
    color: #65716e;
    font: 700 0.78rem/1.2 'Manrope', sans-serif;
}

.final-score-value {
    color: var(--scenario-text);
    font: 600 1.7rem/1.1 'Manrope', sans-serif;
    letter-spacing: -0.02em;
}

.st-key-account_menu {
    position: fixed;
    left: 1rem;
    top: 1rem;
    z-index: 9999;
    width: fit-content;
    max-width: calc(100vw - 2rem);
}

.st-key-account_menu div[data-testid="stExpander"] {
    border: 1px solid rgba(223, 211, 181, 0.7) !important;
    border-radius: 1rem !important;
    background: #fbf8f0 !important;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.24) !important;
    overflow: hidden;
}

.st-key-account_menu details {
    display: flex;
    flex-direction: column;
}

.st-key-account_menu details > summary {
    min-height: 2.7rem;
    padding: 0.65rem 0.85rem !important;
    background: #fbf8f0 !important;
}

.st-key-account_menu details[open] > summary {
    background: #fbf8f0 !important;
    border-bottom: 1px solid #e5decc;
}

.st-key-account_menu details > summary p,
.st-key-account_menu details[open] > summary p,
.st-key-account_menu details > summary span,
.st-key-account_menu details[open] > summary span {
    color: #172b29 !important;
    font-weight: 500 !important;
}

.st-key-account_logout button {
    width: 100%;
    justify-content: center;
    border-color: rgba(181, 72, 66, 0.28) !important;
    background: #fff3ec !important;
    color: #b54842 !important;
    box-shadow: none !important;
}

.st-key-account_logout button * {
    color: #b54842 !important;
    font-weight: 800 !important;
}

.account-menu-copy {
    margin: 0 0 0.55rem;
    white-space: nowrap;
    color: #65716e;
    font-size: 0.78rem;
    font-weight: 700;
}

.account-language-label {
    margin: 0 0 0.5rem;
    color: #65716e;
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.stButton > button {
    border-radius: 999px !important;
    font-family: 'Manrope', sans-serif !important;
    font-weight: 700 !important;
}

.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"] {
    border-color: #174b47 !important;
    background: #174b47 !important;
    color: #fbf8f0 !important;
}

.stButton > button[kind="primary"] *,
.stButton > button[data-testid="baseButton-primary"] * {
    color: #fbf8f0 !important;
}

.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="baseButton-primary"]:hover {
    border-color: #0f3a37 !important;
    background: #0f3a37 !important;
}

.stButton > button[kind="secondary"],
.stButton > button[data-testid="baseButton-secondary"] {
    border-color: #d8d1bf !important;
    background: #fffaf0 !important;
    color: #174b47 !important;
}

.st-key-account_logout button,
.st-key-account_logout button[data-testid="baseButton-secondary"] {
    border-color: rgba(181, 72, 66, 0.28) !important;
    background: #fff3ec !important;
    color: #b54842 !important;
    box-shadow: none !important;
}

.st-key-account_logout button *,
.st-key-account_logout button[data-testid="baseButton-secondary"] * {
    color: #b54842 !important;
    font-weight: 800 !important;
}

.st-key-account_menu div[data-testid="stExpander"] details > summary,
.st-key-account_menu div[data-testid="stExpander"] details[open] > summary,
.st-key-account_menu div[data-testid="stExpander"] details > summary:hover,
.st-key-account_menu div[data-testid="stExpander"] details > summary:focus,
.st-key-account_menu div[data-testid="stExpander"] details > summary:focus-visible {
    display: flex !important;
    align-items: center !important;
    background: #fbf8f0 !important;
    color: #172b29 !important;
    outline: none !important;
    box-shadow: none !important;
}

.st-key-account_menu div[data-testid="stExpander"] details > summary p,
.st-key-account_menu div[data-testid="stExpander"] details[open] > summary p,
.st-key-account_menu div[data-testid="stExpander"] details > summary span,
.st-key-account_menu div[data-testid="stExpander"] details[open] > summary span {
    color: #172b29 !important;
    -webkit-text-fill-color: #172b29 !important;
    background: transparent !important;
    font-weight: 500 !important;
    text-decoration: none !important;
}

@media (max-width: 720px) {
    [data-testid="stMainBlockContainer"] {
        width: min(calc(100vw - 1rem), 68rem);
        margin: 0.5rem auto;
        padding: 1.15rem;
        border-radius: 1.35rem;
    }

    body:has(.st-key-auth_card) [data-testid="stMainBlockContainer"] {
        width: min(calc(100vw - 1rem), 52rem);
    }
}
</style>
""", unsafe_allow_html=True)

if ENABLE_PARENT_DOM_HACKS:
    st.components.v1.html("""
<script>
(function() {
  function hide() {
    try {
      var doc = window.parent.document;

      ['stToolbar','stDecoration','stStatusWidget','stAppDeployButton'].forEach(function(id) {
        var el = doc.querySelector('[data-testid="' + id + '"]');
        if (el) el.style.setProperty('display', 'none', 'important');
      });

      doc.querySelectorAll('body > div, body > div > div').forEach(function(el) {
        var s = window.parent.getComputedStyle(el);
        var r = el.getBoundingClientRect();
        if ((s.position === 'fixed' || s.position === 'absolute') &&
            r.top < 80 && r.right > window.parent.innerWidth * 0.6) {
          el.style.setProperty('display', 'none', 'important');
        }
      });

      doc.querySelectorAll('a[href*="github.com"], a[href*="streamlit.io"]').forEach(function(a) {
        var el = a;
        for (var i = 0; i < 10; i++) {
          if (!el.parentElement || el.parentElement === doc.body) break;
          el = el.parentElement;
        }
        el.style.setProperty('display', 'none', 'important');
      });

    } catch(e) {}
  }

  hide();
  setTimeout(hide, 300);
  setTimeout(hide, 1000);
  setTimeout(hide, 3000);

  try {
    new MutationObserver(hide).observe(
      window.parent.document.body,
      {childList: true, subtree: true}
    );
  } catch(e) {}
})();
</script>
""", height=0)




def goto(page):
    if not st.session_state.get("session_id") or page in {"admin", "admin_sessions"}:
        st.session_state.page = page
        st.session_state.scroll_to_top = True
        st.rerun()
    navigate_committed(st, experiment_service, page)


def commit_command(command, *, operation="stage_transition", rerun=True):
    return commit_streamlit_command(
        st,
        experiment_service,
        command,
        operation=operation,
        rerun=rerun,
    )


def commit_state(state, *, operation, rerun=True):
    return commit_streamlit_state(
        st,
        experiment_service,
        state,
        operation=operation,
        rerun=rerun,
    )


def commit_quality_state(state, quality_events, *, operation, rerun=True):
    return commit_streamlit_quality_state(
        st,
        experiment_service,
        state,
        quality_events,
        operation=operation,
        rerun=rerun,
    )


def scroll_top_anchor():
    st.markdown('<div id="sim-top"></div>', unsafe_allow_html=True)
    if st.session_state.get("scroll_to_top"):
        if not ENABLE_PARENT_DOM_HACKS:
            st.session_state.scroll_to_top = False
            return
        import time as _t
        nonce = int(_t.time() * 1000)
        st.components.v1.html(f"""
<script>
(function() {{
  var nonce = {nonce};
  function tryScroll() {{
    try {{
      var win = window.parent;
      var doc = win.document;
      win.scrollTo(0, 0);
      doc.documentElement.scrollTop = 0;
      doc.body.scrollTop = 0;
      ['[data-testid="stAppViewContainer"]','[data-testid="stMain"]',
       '[data-testid="stAppViewBlockContainer"]','section.main','.main','.stApp']
        .forEach(function(sel){{
          var el = doc.querySelector(sel);
          if (el) {{ el.scrollTop = 0; if (el.scrollTo) el.scrollTo(0,0); }}
        }});
      var anchor = doc.getElementById('sim-top');
      if (anchor) anchor.scrollIntoView({{behavior:'instant', block:'start'}});
    }} catch(e) {{}}
  }}
  tryScroll();
  setTimeout(tryScroll, 120);
}})();
</script>
""", height=0)
        st.session_state.scroll_to_top = False


def auto_open_context_narrativ(expander_label):
    if not ENABLE_PARENT_DOM_HACKS:
        return
    st.components.v1.html(
        f"""
<script>
(function() {{
  function openNarrative() {{
    try {{
      var doc = window.parent.document;
      var expander = Array.from(doc.querySelectorAll('details')).find(function(el) {{
        return (el.textContent || '').includes({expander_label!r});
      }});
      if (!expander) return;
      if (expander.open) return;
      var summary = expander.querySelector('summary');
      if (summary) summary.click();
    }} catch (e) {{}}
  }}

  setTimeout(openNarrative, 80);
  setTimeout(openNarrative, 300);
}})();
</script>
""",
        height=0,
    )


def attach_payment_keyboard_bridge():
    if not ENABLE_PARENT_DOM_HACKS:
        return
    st.components.v1.html(
        """
<script>
(function() {
  var root = window.parent;

  function isEditableTarget(target) {
    if (!target) return false;
    var tag = (target.tagName || '').toLowerCase();
    return tag === 'input' || tag === 'textarea' || target.isContentEditable;
  }

  function findPaymentInput() {
    var selectors = [
      'input[aria-label*="rambursat"]',
      'input[type="number"]'
    ];

    for (var i = 0; i < selectors.length; i++) {
      var el = root.document.querySelector(selectors[i]);
      if (el && el.offsetParent !== null) return el;
    }
    return null;
  }

  function setNativeValue(input, value) {
    var setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(input), 'value').set;
    setter.call(input, value);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  if (root.__paymentKeyboardBridgeHandler) {
    root.removeEventListener('keydown', root.__paymentKeyboardBridgeHandler, true);
  }

  root.__paymentKeyboardBridgeHandler = function(event) {
    if (isEditableTarget(event.target)) return;

    var input = findPaymentInput();
    if (!input) return;

    var key = event.key;
    var current = input.value || '';

    if (/^[0-9]$/.test(key)) {
      event.preventDefault();
      setNativeValue(input, current + key);
      input.focus({ preventScroll: true });
      return;
    }

    if (key === ',' || key === '.') {
      event.preventDefault();
      if (current.indexOf('.') === -1) {
        setNativeValue(input, current ? current + '.' : '0.');
        input.focus({ preventScroll: true });
      }
      return;
    }

    if (key === 'Backspace') {
      event.preventDefault();
      setNativeValue(input, current.slice(0, -1));
      input.focus({ preventScroll: true });
      return;
    }

    if (key === 'Delete') {
      event.preventDefault();
      setNativeValue(input, '');
      input.focus({ preventScroll: true });
      return;
    }
  };

  root.addEventListener('keydown', root.__paymentKeyboardBridgeHandler, true);
})();
</script>
""",
        height=0,
    )


# AUTHENTICATION AND INIT STATE

# -------------------------
prolific_params_before_login = load_prolific_params()
if (
    PROLIFIC_MODE_ENABLED
    and has_any_prolific_param(prolific_params_before_login)
    and not prolific_params_complete(prolific_params_before_login)
):
    st.error(t("prolific.error_missing_params"))
    st.stop()
if (
    PROLIFIC_MODE_ENABLED
    and prolific_params_complete(prolific_params_before_login)
    and not prolific_study_allowed(prolific_params_before_login.get("STUDY_ID"))
):
    st.error(t("prolific.error_invalid_study"))
    st.stop()

prolific_launch = PROLIFIC_MODE_ENABLED and prolific_params_complete(prolific_params_before_login)

if not is_logged_in() and not prolific_launch:
    login_ctx = make_ui_context(st=st, t=t)
    render_language_selector_component(st, t, ensure_language, get_language, set_language)
    render_login_page_component(login_ctx)
    st.stop()

if not st.session_state.get("_bootstrap_done"):
    try:
        bootstrap_authenticated_session()
        st.session_state._bootstrap_done = True
    except ExperimentError as exc:
        st.error(f"The saved experiment session could not be loaded safely. Please retry. ({exc})")
        st.stop()
else:
    ensure_current_scenario_version()


if is_logged_in() and not prolific_launch:
    render_account_menu_component(
        make_ui_context(
            st=st,
            t=t,
            ensure_language=ensure_language,
            get_language=get_language,
            set_language=set_language,
            is_admin_user=is_admin_user,
            goto=goto,
            pre_sections_ro=PRE_SECTIONS_RO,
            post_sections_ro=POST_SECTIONS_RO,
        )
    )


# ==================== PAGE ROUTING ====================
ui_ctx = make_ui_context(
    st=st,
    t=t,
    dev=DEV,
    scenario_version=SCENARIO_VERSION,
    repeat_scenario_dev_mode=REPEAT_SCENARIO_DEV_MODE,
    pre_sections_ro=PRE_SECTIONS_RO,
    post_sections_ro=POST_SECTIONS_RO,
    goto=goto,
    commit_command=commit_command,
    commit_state=commit_state,
    commit_quality_state=commit_quality_state,
    experiment_service=experiment_service,
    scroll_top_anchor=scroll_top_anchor,
    auto_open_context_narrativ=auto_open_context_narrativ,
    attach_payment_keyboard_bridge=attach_payment_keyboard_bridge,
    get_month=get_month,
    get_category_label=get_category_label,
    get_display_pre_sections=get_display_pre_sections,
    get_display_post_sections=get_display_post_sections,
    get_localized_narrative=get_localized_narrative,
    load_admin_study_session_by_code=load_admin_study_session_by_code,
    create_admin_study_session=create_admin_study_session,
    list_admin_study_sessions=list_admin_study_sessions,
    list_participant_sessions_for_study_session=list_participant_sessions_for_study_session,
    cancel_admin_study_session=cancel_admin_study_session,
    condition_options=condition_options,
    current_user_email=current_user_email,
    current_account_key=current_account_key,
    is_admin_user=is_admin_user,
    start_new_scenario=start_new_scenario,
)

render_current_page(ui_ctx)

