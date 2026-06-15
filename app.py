import re
import random
import os
import streamlit as st
import pandas as pd

from auth_manager import current_user_email, is_admin_user, is_logged_in
from tables import get_month
from questions import PRE_SECTIONS as PRE_SECTIONS_RO
from questions import POST_SECTIONS as POST_SECTIONS_RO
from i18n import (
    ensure_language,
    get_category_label,
    get_display_post_sections,
    get_display_pre_sections,
    get_language,
    get_localized_narrative,
    set_language,
    t,
)
from state_manager import (
    REPEAT_SCENARIO_DEV_MODE,
    SCENARIO_VERSION,
    bootstrap_authenticated_session,
    cancel_admin_study_session,
    create_admin_study_session,
    ensure_current_scenario_version,
    finalize_participant,
    list_admin_study_sessions,
    load_admin_study_session_by_code,
    persist_checkpoint,
    persist_month_result_snapshot,
    start_new_scenario,
)

try:
    from state_manager import (
        persist_psychometric_answers_snapshot,
        persist_session_summary_snapshot,
    )
except ImportError:
    # Keep deploys resilient if app.py is loaded before the matching state_manager.py update.
    def persist_psychometric_answers_snapshot(*_args, **_kwargs):
        return True

    def persist_session_summary_snapshot(*_args, **_kwargs):
        return True

DEV = os.getenv("SCENARIO_DEV", "").lower() == "true"
RECOMMENDED_BUFFER = 5.0
SESSION_MONTHS = 24
EURO_PER_MONTHLY_POINT = 0.005
MAX_MONTHLY_SCORE = 100.0
DEFAULT_BONUS_MAX_SESSION = SESSION_MONTHS * MAX_MONTHLY_SCORE * EURO_PER_MONTHLY_POINT


def get_bonus_max_session():
    return money(DEFAULT_BONUS_MAX_SESSION)

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

st.components.v1.html("""
<script>
(function() {
  function hide() {
    try {
      var doc = window.parent.document;

      // hide by known test IDs
      ['stToolbar','stDecoration','stStatusWidget','stAppDeployButton'].forEach(function(id) {
        var el = doc.querySelector('[data-testid="' + id + '"]');
        if (el) el.style.setProperty('display', 'none', 'important');
      });

      // hide any fixed/absolute element sitting in the top-right corner
      doc.querySelectorAll('body > div, body > div > div').forEach(function(el) {
        var s = window.parent.getComputedStyle(el);
        var r = el.getBoundingClientRect();
        if ((s.position === 'fixed' || s.position === 'absolute') &&
            r.top < 80 && r.right > window.parent.innerWidth * 0.6) {
          el.style.setProperty('display', 'none', 'important');
        }
      });

      // hide links to github / streamlit and their parent containers
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
    st.session_state.page = page
    st.session_state.scroll_to_top = True
    persist_checkpoint()
    st.rerun()


def scroll_top_anchor():
    st.markdown('<div id="sim-top"></div>', unsafe_allow_html=True)
    if st.session_state.get("scroll_to_top"):
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


def randomize_sections(sections):
    for section in sections:
        randomize_section(section)


def randomize_section(section):
    for i in range(len(section["questions"])):
        key = f"{section['key_prefix']}_{i}"
        st.session_state.answers[key] = random.choice(section["scale"])


def render_language_buttons(prefix="lang"):
    ensure_language()
    current_language = get_language()
    with st.container():
        col_en, col_ro = st.columns(2)
        with col_en:
            if st.button(
                t("language.en"),
                type="primary" if current_language == "en" else "secondary",
                key=f"{prefix}_en",
                use_container_width=True,
            ):
                if current_language != "en":
                    set_language("en")
                    st.rerun()
        with col_ro:
            if st.button(
                t("language.ro"),
                type="primary" if current_language == "ro" else "secondary",
                key=f"{prefix}_ro",
                use_container_width=True,
            ):
                if current_language != "ro":
                    set_language("ro")
                    st.rerun()


def render_language_selector():
    render_language_buttons("lang")


def render_login_page():
    st.markdown(
        """
<style>
.st-key-auth_card {
    margin: 0;
}

.auth-brand {
    display: flex;
    align-items: center;
    gap: 0.72rem;
    color: #1d4a46;
    font: 700 0.82rem/1 'Manrope', sans-serif;
    letter-spacing: 0.13em;
    text-transform: uppercase;
}

.auth-brand-mark {
    display: grid;
    place-items: center;
    width: 2.05rem;
    height: 2.05rem;
    border-radius: 0.75rem;
    color: #fbf8f0;
    background: #174b47;
    letter-spacing: 0;
    font-size: 1rem;
}

.auth-rule {
    width: 100%;
    height: 1px;
    margin: 1.45rem 0 1.35rem;
    background: #e5decc;
}

.auth-title {
    margin: 0 0 0.75rem;
    color: #172b29 !important;
    font: 600 clamp(1.75rem, 4vw, 2.12rem)/1.13 'Fraunces', serif;
    letter-spacing: -0.03em;
}

.auth-copy {
    margin: 0 0 1.35rem;
    color: #586564;
    font: 500 0.95rem/1.6 'Manrope', sans-serif;
}

.auth-signals {
    display: flex;
    gap: 0.48rem;
    flex-wrap: wrap;
    margin: 0 0 1.55rem;
}

.auth-chip {
    padding: 0.42rem 0.65rem;
    border-radius: 999px;
    color: #2e5753;
    background: #e8efea;
    font: 600 0.73rem/1 'Manrope', sans-serif;
}

.st-key-google_login button {
    position: relative;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.68rem;
    width: 100%;
    min-height: 3.15rem;
    padding: 0.75rem 1rem;
    border: 1px solid #747775 !important;
    border-radius: 999px !important;
    color: #1f1f1f !important;
    background: #ffffff !important;
    box-shadow: none !important;
    transition: background 140ms ease, box-shadow 140ms ease, border-color 140ms ease;
}

.st-key-google_login button::before {
    content: "";
    width: 1.18rem;
    height: 1.18rem;
    flex: 0 0 1.18rem;
    background: url("https://developers.google.com/static/identity/images/g-logo.png") center / contain no-repeat;
}

.st-key-google_login button p {
    color: #1f1f1f !important;
    font: 500 0.9rem/1.25 'Roboto', sans-serif !important;
}

.st-key-google_login button:hover {
    background: #f8faff !important;
    border-color: #5f6368 !important;
    box-shadow: 0 1px 3px rgba(60, 64, 67, 0.18) !important;
}

.st-key-google_login button:focus-visible {
    outline: 2px solid #1a73e8 !important;
    outline-offset: 2px;
}

.auth-privacy {
    margin: 1.45rem 0 0;
    padding-top: 1.15rem;
    border-top: 1px solid #e5decc;
    color: #687472;
    font: 500 0.76rem/1.55 'Manrope', sans-serif;
}

.auth-privacy strong {
    color: #304c49;
}

@media (max-width: 520px) {
    .st-key-auth_card {
        margin: 0;
    }
}
</style>
""",
        unsafe_allow_html=True,
    )

    with st.container(key="auth_card"):
        st.markdown(
            f"""
<div class="auth-brand">
  <span class="auth-brand-mark">S</span>
  <span>{t("auth.brand")}</span>
</div>
<div class="auth-rule"></div>
<h1 class="auth-title">{t("auth.title")}</h1>
<p class="auth-copy">{t("auth.copy")}</p>
<div class="auth-signals">
  <span class="auth-chip">{t("auth.chips")[0]}</span>
  <span class="auth-chip">{t("auth.chips")[1]}</span>
  <span class="auth-chip">{t("auth.chips")[2]}</span>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button(t("auth.google_button"), key="google_login", use_container_width=True):
            st.login()
        st.markdown(
            f"""
<p class="auth-privacy">{t("auth.privacy_html")}</p>
<div class="auth-info">
  <span class="auth-info-icon">i</span>
  <span>{t("auth.privacy_note")}</span>
</div>
""",
            unsafe_allow_html=True,
        )
# AUTHENTICATION AND INIT STATE

# -------------------------
if not is_logged_in():
    render_language_selector()
    render_login_page()
    st.stop()

if not st.session_state.get("_bootstrap_done"):
    bootstrap_authenticated_session()
    st.session_state._bootstrap_done = True
else:
    ensure_current_scenario_version()


def render_account_menu():
    email = st.user.get("email") or st.user.get("name") or t("auth.account_fallback")
    with st.container(key="account_menu"):
        with st.expander(email):
            st.markdown(f'<div class="account-language-label">{t("auth.language_label")}</div>', unsafe_allow_html=True)
            render_language_buttons("account_lang")
            if is_admin_user():
                if st.button(t("auth.admin_page"), key="account_admin", use_container_width=True):
                    st.session_state.admin_return_page = st.session_state.get("page", "home")
                    goto("admin")
            if st.button(t("auth.logout"), icon=":material/logout:", key="account_logout", use_container_width=True):
                st.logout()


render_account_menu()


def normalize_study_session_code(value):
    return re.sub(r"\D", "", str(value or ""))[:6]


def has_study_session_assignment():
    return bool(st.session_state.get("study_session_id") and st.session_state.get("study_session_code"))


def render_question_section(section, chapter_number, question_offset=0):
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


def all_answered(sections):
    for section in sections:
        for i in range(len(section["questions"])):
            key = f"{section['key_prefix']}_{i}"
            if st.session_state.answers.get(key) is None:
                return False
    return True


DEMOGRAPHIC_KEYS = [
    "demo_age",
    "demo_gender",
    "demo_education",
    "demo_field",
    "demo_occupation",
    "demo_financial_decisions",
    "demo_credit_experience",
    "demo_financial_familiarity",
    "demo_living_situation",
    "demo_recurring_responsibilities",
    "demo_country",
]


def demographics_complete():
    return all(st.session_state.answers.get(key) not in (None, "") for key in DEMOGRAPHIC_KEYS)


def render_quiz_chapter(
    section,
    chapter_index,
    total_chapters,
    next_page,
    dev_label,
    title,
    question_offset=0,
    on_continue=None,
    save_error_message="Error while saving progress. Please reload the page and try again.",
):
    st.title(title)
    st.caption(t("quiz.chapter_label", current=chapter_index + 1, total=total_chapters))
    st.markdown(t("quiz.chapter_continue_help"))
    st.progress((chapter_index + 1) / total_chapters)
    render_question_section(section, chapter_index + 1, question_offset)

    if DEV:
        if st.button(dev_label, type="secondary", key=f"dev_{section['key_prefix']}_{chapter_index}"):
            randomize_section(section)
            st.session_state.scroll_to_top = True
            goto(next_page)

    if not all_answered([section]):
        st.warning(t("quiz.chapter_required_warning"))

    if st.button(t("quiz.continue_button"), type="primary", key=f"continue_{section['key_prefix']}_{chapter_index}"):
        if all_answered([section]):
            if on_continue is not None and not on_continue():
                st.error(save_error_message)
                st.stop()
            st.session_state.scroll_to_top = True
            goto(next_page)
        else:
            st.error(t("quiz.chapter_missing_error"))


def money(value):
    return round(float(value), 2)


def display_number(value):
    value = money(value)
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}"


def display_euro(value):
    return f"{display_number(value)} €"


def persist_pre_psychometrics():
    return persist_psychometric_answers_snapshot(
        st.session_state.answers,
        pre_sections=get_display_pre_sections(),
    )


def persist_post_psychometrics():
    return persist_psychometric_answers_snapshot(
        st.session_state.answers,
        post_sections=get_display_post_sections(),
    )


def display_value_table(values):
    rows = [(get_category_label(category), display_number(amount)) for category, amount in values.items()]
    return pd.DataFrame(rows, columns=[t("table.category"), t("table.value")])


def month_sum(values):
    return money(sum(values.values()))


def get_opening_balance(month, data):
    if month <= 1:
        return money(data["position"]["initial"])

    for result in reversed(st.session_state.get("monthly_results", [])):
        if int(result.get("month", 0)) == month - 1:
            return money(result.get("cash_final", 0.0))

    # Keep older/incomplete checkpoints usable if the previous result is absent.
    return money(data["position"].get("initial", 0.0))


def zero_score_data():
    return {
        "score_model": "behavioral_v1",
        "score_repayment": 0.0,
        "score_liquidity": 0.0,
        "score_overdraft": 0.0,
        "monthly_score": 0.0,
        "bonus_lunar": 0.0,
    }


def compute_monthly_score(
    accepted_payment,
    cash_final,
    overdraft_final,
    overdraft_limit,
    loan_obligation,
    loan_balance_before_payment=None,
    loan_closed_by_payment=False,
):
    reference_payment = money(loan_obligation)
    remaining_balance = reference_payment if loan_balance_before_payment is None else money(loan_balance_before_payment)
    expected_repayment = money(
        min(reference_payment, remaining_balance)
        if loan_closed_by_payment
        else reference_payment
    )

    if expected_repayment <= 0:
        repayment_score = 40.0
    else:
        repayment_score = min(accepted_payment / expected_repayment, 1.0) * 40.0

    liquidity_score = min(cash_final / RECOMMENDED_BUFFER, 1.0) * 30.0
    overdraft_score = 30.0 if overdraft_limit <= 0 else max(0.0, 30.0 * (1.0 - overdraft_final / overdraft_limit))
    monthly_score = min(100.0, max(0.0, repayment_score + liquidity_score + overdraft_score))

    return {
        "score_model": "behavioral_v1",
        "score_repayment": money(repayment_score),
        "score_liquidity": money(liquidity_score),
        "score_overdraft": money(overdraft_score),
        "monthly_score": money(monthly_score),
        "bonus_lunar": money(monthly_score * EURO_PER_MONTHLY_POINT),
    }


def normalize_month_result_score(result):
    if result.get("score_model") == "behavioral_v1":
        return result

    if not result.get("payment_valid") or result.get("pre_credit_impossible"):
        result.update(zero_score_data())
        return result

    result.update(
        compute_monthly_score(
            money(result.get("accepted_payment", 0.0)),
            money(result.get("cash_final", 0.0)),
            money(result.get("overdraft_final", 0.0)),
            3000.0,
            money(result.get("loan_obligation", 317.71)),
            money(result.get("loan_balance_before_payment", result.get("loan_obligation", 317.71))),
            money(result.get("credit_final", 0.0)) <= 0 and money(result.get("loan_balance_before_payment", 0.0)) > 0,
        )
    )
    return result


def compute_month_result(month, data, loan, overdraft, payment):
    income_total = month_sum(data["income"])
    expenses_total = month_sum(data["expenses"])
    obligations = data.get("obligations", {})
    loan_balance_before_payment = money(loan.balance)
    loan_obligation = money(loan.get_required_payment())
    credit_interest = money(loan.apply_interest())
    overdraft_interest = money(overdraft.apply_interest())
    penalties = money(obligations.get("penalties", 0))
    opening_balance = get_opening_balance(month, data)

    available_total = money(opening_balance + income_total)
    outflows_before_credit = money(expenses_total + overdraft_interest + credit_interest + penalties)
    deficit_before_credit = money(max(0.0, outflows_before_credit - available_total))
    liquidity_after_charges = money(max(0.0, available_total - outflows_before_credit))
    overdraft_after_charges = money(overdraft.balance + deficit_before_credit)
    overdraft_remaining = money(max(0.0, overdraft.limit - min(overdraft_after_charges, overdraft.limit)))
    max_payment = money(liquidity_after_charges + overdraft_remaining)

    pre_credit_impossible = overdraft_after_charges > overdraft.limit
    no_loan_due = loan_balance_before_payment <= 0 and loan_obligation <= 0
    payment_value = None if payment is None else money(payment)
    capped_payment = None if payment_value is None else money(min(payment_value, loan.balance))
    payment_valid = (
        not pre_credit_impossible
        and (
            no_loan_due
            or (
                payment_value is not None
                and payment_value >= 0
                and capped_payment <= max_payment
            )
        )
    )

    if pre_credit_impossible:
        feedback_message = t("simulation.feedback_pre_credit")
        accepted_payment = 0.0
        overdraft_from_payment = 0.0
        overdraft_final = money(overdraft.limit)
        cash_final = 0.0
        credit_final = money(loan.balance)
        score_data = zero_score_data()
        invalid_reason = "pre_credit"
    elif payment_valid:
        accepted_payment = 0.0 if no_loan_due else capped_payment
        overdraft_from_payment = money(max(0.0, accepted_payment - liquidity_after_charges))
        overdraft_final = money(overdraft_after_charges + overdraft_from_payment)
        cash_final = money(max(0.0, liquidity_after_charges - accepted_payment))
        credit_final = money(max(0.0, loan.balance - accepted_payment))
        score_data = compute_monthly_score(
            accepted_payment,
            cash_final,
            overdraft_final,
            overdraft.limit,
            loan_obligation,
            loan_balance_before_payment,
            credit_final <= 0 and loan_balance_before_payment > 0,
        )
        feedback_message = t("simulation.feedback_no_payment_due") if no_loan_due else t("simulation.feedback_success")
        invalid_reason = None
    else:
        accepted_payment = 0.0
        overdraft_from_payment = 0.0
        overdraft_final = money(overdraft_after_charges)
        cash_final = money(liquidity_after_charges)
        credit_final = money(loan.balance)
        score_data = zero_score_data()
        feedback_message = t("simulation.feedback_invalid")
        invalid_reason = "payment"

    if overdraft_final > overdraft.limit:
        overdraft_final = money(overdraft.limit)
        cash_final = 0.0
        if score_data["monthly_score"] > 0:
            accepted_payment = 0.0
            credit_final = money(loan.balance)
            overdraft_from_payment = 0.0
            score_data = zero_score_data()
            feedback_message = t("simulation.feedback_invalid")
            invalid_reason = "payment"

    return {
        "month": month,
        "opening_balance": opening_balance,
        "income_total": income_total,
        "expenses_total": expenses_total,
        "loan_balance_before_payment": loan_balance_before_payment,
        "loan_obligation": loan_obligation,
        "credit_interest": credit_interest,
        "overdraft_interest": overdraft_interest,
        "penalties": penalties,
        "available_total": available_total,
        "outflows_before_credit": outflows_before_credit,
        "deficit_before_credit": deficit_before_credit,
        "liquidity_after_charges": liquidity_after_charges,
        "overdraft_after_charges": overdraft_after_charges,
        "overdraft_remaining": overdraft_remaining,
        "max_payment": max_payment,
        "payment_input": 0.0 if payment_value is None else payment_value,
        "accepted_payment": accepted_payment,
        "overdraft_from_payment": overdraft_from_payment,
        "overdraft_final": overdraft_final,
        "cash_final": cash_final,
        "credit_final": credit_final,
        **score_data,
        "costs_this_month": money(credit_interest + overdraft_interest + penalties),
        "feedback_message": feedback_message,
        "invalid_reason": invalid_reason,
        "pre_credit_impossible": pre_credit_impossible,
        "payment_valid": payment_valid,
    }


def compute_final_score():
    monthly_results = [normalize_month_result_score(result) for result in st.session_state.get("monthly_results", [])]
    score_sum = sum(float(result.get("monthly_score", 0.0)) for result in monthly_results)
    return money(min(100.0, max(0.0, score_sum / SESSION_MONTHS)))


def get_final_score_breakdown():
    monthly_results = [normalize_month_result_score(result) for result in st.session_state.get("monthly_results", [])]
    monthly_score_sum = money(sum(float(result.get("monthly_score", 0.0)) for result in monthly_results))
    final_score = money(min(MAX_MONTHLY_SCORE, max(0.0, monthly_score_sum / SESSION_MONTHS)))
    bonus_max_session = get_bonus_max_session()
    bonus_final = money(monthly_score_sum * EURO_PER_MONTHLY_POINT)
    total_repaid = money(sum(float(result.get("accepted_payment", 0.0)) for result in monthly_results))
    credit_interest_total = money(sum(float(result.get("credit_interest", 0.0)) for result in monthly_results))
    overdraft_interest_total = money(sum(float(result.get("overdraft_interest", 0.0)) for result in monthly_results))
    return {
        "months_completed": len(monthly_results),
        "monthly_score_sum": monthly_score_sum,
        "final_score": final_score,
        "bonus_max_session": bonus_max_session,
        "bonus_final": bonus_final,
        "study_session_id": st.session_state.get("study_session_id"),
        "study_session_code": st.session_state.get("study_session_code"),
        "total_repaid": total_repaid,
        "remaining_credit": money(st.session_state.loan.balance),
        "remaining_overdraft": money(st.session_state.overdraft.balance),
        "credit_interest_total": credit_interest_total,
        "overdraft_interest_total": overdraft_interest_total,
        "interest_total": money(credit_interest_total + overdraft_interest_total),
    }


# ==================== STUDY SESSION CODE ====================
if st.session_state.page == "enter_session_code":
    scroll_top_anchor()
    st.title(t("study_session.title"))
    st.markdown(t("study_session.body"))
    code_value = st.text_input(
        t("study_session.input_label"),
        value=st.session_state.get("study_session_code", ""),
        max_chars=6,
        help=t("study_session.input_help"),
    )
    if st.button(t("study_session.button"), type="primary"):
        session_code = normalize_study_session_code(code_value)
        if len(session_code) != 6:
            st.warning(t("study_session.missing"))
            st.stop()
        record = load_admin_study_session_by_code(session_code)
        if not record:
            st.error(t("study_session.invalid"))
            st.stop()
        st.session_state.study_session_id = record["id"]
        st.session_state.study_session_code = record["session_code"]
        st.session_state.scroll_to_top = True
        goto("home")
    if st.button(t("study_session.skip_button"), type="secondary"):
        st.session_state.study_session_id = None
        st.session_state.study_session_code = None
        st.session_state.scroll_to_top = True
        goto("home")


# ==================== ADMIN PAGE ====================
elif st.session_state.page == "admin":
    if not is_admin_user():
        goto("home")
    scroll_top_anchor()
    admin_return_page = st.session_state.get("admin_return_page", "home")
    if admin_return_page == "admin":
        admin_return_page = "home"
    st.title(t("admin.title"))
    st.markdown(t("admin.body"))
    if st.button(t("admin.start_session"), type="primary"):
        created = create_admin_study_session(current_user_email())
        st.session_state.admin_last_created_session = created
        st.success(t("admin.created_success"))
    active_sessions = list_admin_study_sessions(current_user_email())
    latest_created = st.session_state.get("admin_last_created_session")
    active_session_ids = {row.get("id") for row in active_sessions}
    if latest_created and latest_created.get("id") in active_session_ids:
        st.metric(t("admin.code_label"), latest_created["session_code"])
    elif latest_created:
        st.session_state.admin_last_created_session = None
    if active_sessions:
        st.markdown(f"### {t('admin.active_sessions')}")
        st.caption(t("admin.sessions_note"))
        header_cols = st.columns([2, 2, 3, 1])
        header_cols[0].markdown(f"**{t('admin.code_label')}**")
        header_cols[1].markdown(f"**{t('admin.status')}**")
        header_cols[2].markdown(f"**{t('admin.created_at')}**")
        for row in active_sessions:
            code = row.get("session_code")
            status = row.get("status")
            created_at = row.get("created_at")
            cols = st.columns([2, 2, 3, 1])
            cols[0].markdown(f"**{code}**")
            cols[1].write(status)
            cols[2].write(created_at)
            if cols[3].button(" ", icon=":material/delete:", help=t("admin.cancel_session"), key=f"cancel_session_{row.get('id')}"):
                cancelled = cancel_admin_study_session(row.get("id"), current_user_email())
                if cancelled:
                    if (st.session_state.get("admin_last_created_session") or {}).get("id") == row.get("id"):
                        st.session_state.admin_last_created_session = None
                    if st.session_state.get("study_session_id") == row.get("id"):
                        st.session_state.study_session_id = None
                        st.session_state.study_session_code = None
                    st.success(t("admin.cancelled_success", code=code))
                    st.rerun()
                else:
                    st.error(t("admin.cancelled_error"))
    if st.button(t("admin.back_home")):
        goto(admin_return_page)


# ==================== COMPLETED ACCOUNT ====================
elif st.session_state.page == "already_completed":
    scroll_top_anchor()
    st.title(t("already_completed.title"))
    st.info(t("already_completed.body"))
    if REPEAT_SCENARIO_DEV_MODE and st.button(t("already_completed.button"), type="primary"):
        start_new_scenario()
        st.rerun()


# ==================== HOME ====================
elif st.session_state.page == "home":
    scroll_top_anchor()
    st.markdown(f"""
<style>
.home-title {{ text-align: center; font-size: 2rem; font-weight: 700; margin-bottom: 1rem; }}
.home-body {{ text-align: justify; }}
</style>
<div class="home-title">{t("home.title")}</div>
""", unsafe_allow_html=True)
    st.markdown('<div class="home-body">', unsafe_allow_html=True)
    st.markdown(t("home.body"))
    st.info(t("home.info"))
    st.markdown(t("home.note"))
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button(t("home.button"), type="primary"):
        st.session_state.scroll_to_top = True
        goto("consent")
    if st.button(t("study_session.optional_button"), type="secondary"):
        st.session_state.scroll_to_top = True
        goto("enter_session_code")


# ==================== INFORMED CONSENT ====================
elif st.session_state.page == "consent":
    scroll_top_anchor()
    st.markdown("""
<style>
.consent-page {
    text-align: justify;
    font-family: 'Manrope', sans-serif;
    color: var(--scenario-text);
}
.consent-page h2,
.consent-page h3 {
    font-family: 'Fraunces', serif;
    color: var(--scenario-text);
}
.consent-page h2 {
    margin-top: 0.4rem;
    font-size: 1.45rem;
}
.consent-page h3 {
    margin-top: 1.5rem;
    font-size: 1.08rem;
}
.consent-page p,
.consent-page li {
    font-size: 0.96rem;
    line-height: 1.7;
}
</style>
""", unsafe_allow_html=True)

    st.markdown('<div class="consent-page">', unsafe_allow_html=True)
    st.markdown(t("consent.markdown"))
    st.markdown('</div>', unsafe_allow_html=True)

    consent_items = t("consent.items")
    consent_values = [
        st.checkbox(item, key=f"consent_item_{index}")
        for index, item in enumerate(consent_items)
    ]
    consent_complete = all(consent_values)

    col_accept, col_decline = st.columns([2, 1])
    with col_accept:
        accept_clicked = st.button(
            t("consent.accept_button"),
            type="primary",
            use_container_width=True,
            key="consent_accept",
        )
    with col_decline:
        decline_clicked = st.button(
            t("consent.decline_button"),
            type="secondary",
            use_container_width=True,
            key="consent_decline",
        )

    if accept_clicked:
        if not consent_complete:
            st.warning(t("consent.warning"))
            st.stop()
        st.session_state.answers["consent_agreed"] = "1 - Da"
        st.session_state.scroll_to_top = True
        goto("demographics")

    if decline_clicked:
        st.session_state.answers["consent_agreed"] = "0 - Nu"
        st.session_state.scroll_to_top = True
        goto("consent_declined")


# ==================== CONSENT DECLINED ====================
elif st.session_state.page == "consent_declined":
    scroll_top_anchor()
    st.title(t("consent_declined.title"))
    st.markdown(t("consent_declined.body"))
    if st.button(t("consent_declined.button"), type="primary"):
        st.session_state.scroll_to_top = True
        goto("consent")


# ==================== DEMOGRAPHIC PROFILE ====================
elif st.session_state.page == "demographics":
    scroll_top_anchor()
    if st.session_state.answers.get("consent_agreed") != "1 - Da":
        goto("consent")

    st.markdown("""
<style>
.demographics-page {
    text-align: justify;
    font-family: 'Manrope', sans-serif;
    color: var(--scenario-text);
}
.demographics-page h2 {
    margin-top: 0.4rem;
    font-family: 'Fraunces', serif;
    font-size: 1.45rem;
    color: var(--scenario-text);
}
.demographics-page p {
    font-size: 0.98rem;
    line-height: 1.72;
}
</style>
""", unsafe_allow_html=True)

    st.markdown(
        f"""
<div class="demographics-page">
<h2>{t("demographics.title")}</h2>
<p>{t("demographics.intro")}</p>
</div>
""",
        unsafe_allow_html=True,
    )

    gender_options = t("demographics.options.gender")
    education_options = t("demographics.options.education")
    field_options = t("demographics.options.field")
    occupation_options = t("demographics.options.occupation")
    frequency_options = t("demographics.options.frequency")
    credit_options = t("demographics.options.credit")
    familiarity_options = t("demographics.options.familiarity")
    living_options = t("demographics.options.living")
    yes_no_options = t("demographics.options.yes_no")

    def radio_index(key, options):
        current = st.session_state.answers.get(key)
        return options.index(current) if current in options else None

    st.markdown(f"**{t('demographics.age_title')}**")
    st.caption(t("demographics.age_caption"))
    age = st.number_input(
        t("demographics.age_prompt"),
        min_value=18,
        max_value=75,
        step=1,
        value=st.session_state.answers.get("demo_age"),
        key="demo_age_input",
    )
    st.caption(t("demographics.age_note"))

    st.markdown(f"**{t('demographics.gender_title')}**")
    gender = st.radio(t("demographics.gender_prompt"), gender_options, index=radio_index("demo_gender", gender_options), key="demo_gender_input")

    st.markdown(f"**{t('demographics.education_title')}**")
    education = st.radio(t("demographics.education_prompt"), education_options, index=radio_index("demo_education", education_options), key="demo_education_input")

    st.markdown(f"**{t('demographics.field_title')}**")
    field = st.radio(t("demographics.field_prompt"), field_options, index=radio_index("demo_field", field_options), key="demo_field_input")

    st.markdown(f"**{t('demographics.occupation_title')}**")
    occupation = st.radio(t("demographics.occupation_prompt"), occupation_options, index=radio_index("demo_occupation", occupation_options), key="demo_occupation_input")

    st.markdown(f"**{t('demographics.financial_decisions_title')}**")
    financial_decisions = st.radio(t("demographics.financial_decisions_prompt"), frequency_options, index=radio_index("demo_financial_decisions", frequency_options), key="demo_financial_decisions_input")

    st.markdown(f"**{t('demographics.credit_experience_title')}**")
    credit_experience = st.radio(t("demographics.credit_experience_prompt"), credit_options, index=radio_index("demo_credit_experience", credit_options), key="demo_credit_experience_input")

    st.markdown(f"**{t('demographics.financial_familiarity_title')}**")
    financial_familiarity = st.radio(t("demographics.financial_familiarity_prompt"), familiarity_options, index=radio_index("demo_financial_familiarity", familiarity_options), key="demo_financial_familiarity_input")

    st.markdown(f"**{t('demographics.living_title')}**")
    living_situation = st.radio(t("demographics.living_prompt"), living_options, index=radio_index("demo_living_situation", living_options), key="demo_living_situation_input")

    st.markdown(f"**{t('demographics.responsibilities_title')}**")
    recurring_responsibilities = st.radio(t("demographics.responsibilities_prompt"), yes_no_options, index=radio_index("demo_recurring_responsibilities", yes_no_options), key="demo_recurring_responsibilities_input")

    st.markdown(f"**{t('demographics.country_title')}**")
    st.caption(t("demographics.country_caption"))
    country = st.text_input(t("demographics.country_prompt"), value=st.session_state.answers.get("demo_country", ""), key="demo_country_input")

    if st.button(t("demographics.continue_button"), type="primary", use_container_width=True, key="demographics_continue"):
        values = {
            "demo_age": int(age) if age is not None else None,
            "demo_gender": gender,
            "demo_education": education,
            "demo_field": field,
            "demo_occupation": occupation,
            "demo_financial_decisions": financial_decisions,
            "demo_credit_experience": credit_experience,
            "demo_financial_familiarity": financial_familiarity,
            "demo_living_situation": living_situation,
            "demo_recurring_responsibilities": recurring_responsibilities,
            "demo_country": country.strip(),
        }
        if any(value in (None, "") for value in values.values()):
            st.warning(t("demographics.warning"))
            st.stop()

        st.session_state.answers.update(values)
        st.session_state.scroll_to_top = True
        goto("pre_question_0")


# ==================== PRE-SIMULATION QUESTIONS ====================
elif st.session_state.page == "pre_questions":
    if st.session_state.answers.get("consent_agreed") != "1 - Da":
        goto("consent")
    elif not demographics_complete():
        goto("demographics")
    else:
        goto("pre_question_0")

elif st.session_state.page.startswith("pre_question_"):
    scroll_top_anchor()
    if st.session_state.answers.get("consent_agreed") != "1 - Da":
        goto("consent")
    if not demographics_complete():
        goto("demographics")

    pre_sections = get_display_pre_sections()

    try:
        pre_index = int(st.session_state.page.rsplit("_", 1)[1])
    except Exception:
        goto("pre_question_0")

    if pre_index >= len(pre_sections):
        goto("instructions")

    next_page = "instructions" if pre_index + 1 >= len(pre_sections) else f"pre_question_{pre_index + 1}"
    render_quiz_chapter(
        pre_sections[pre_index],
        pre_index,
        len(pre_sections),
        next_page,
        t("quiz.dev_randomize"),
        t("quiz.pre_title"),
        question_offset=sum(len(section["questions"]) for section in pre_sections[:pre_index]),
        on_continue=persist_pre_psychometrics,
        save_error_message="Error while saving questionnaire answers. Please reload the page and try again.",
    )


# ==================== PARTICIPANT INSTRUCTIONS ====================
elif st.session_state.page == "instructions":
    scroll_top_anchor()
    st.markdown("""
<style>
.participant-instructions {
    text-align: justify;
    font-family: 'Manrope', sans-serif;
    color: var(--scenario-text);
}
.participant-instructions h2,
.participant-instructions h3 {
    font-family: 'Fraunces', serif;
    color: var(--scenario-text);
}
.participant-instructions h2 {
    margin-top: 0.4rem;
    font-size: 1.45rem;
}
.participant-instructions h3 {
    margin-top: 1.55rem;
    font-size: 1.15rem;
}
.participant-instructions p,
.participant-instructions li {
    font-size: 0.98rem;
    line-height: 1.72;
}
.participant-instructions ul,
.participant-instructions ol {
    margin-bottom: 1.1rem;
}
</style>
""", unsafe_allow_html=True)

    st.markdown(
        '<div class="participant-instructions">',
        unsafe_allow_html=True,
    )
    st.markdown(t("instructions.body"), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button(t("instructions.button"), type="primary"):
        st.session_state.scroll_to_top = True
        goto("profile")


# ==================== PROFILE ====================
elif st.session_state.page == "profile":
    scroll_top_anchor()
    st.markdown("""
<style>
.profile-text { text-align: justify; }
div[data-testid="stAppViewBlockContainer"] > div:first-child { padding-top: 0.5rem; }
h1:first-of-type { margin-top: 0; }
h3 { margin-top: 0.5rem; }
</style>
""", unsafe_allow_html=True)

    st.title(t("profile.title"))
    st.markdown(t("profile.intro"))

    st.markdown('<div class="profile-text">', unsafe_allow_html=True)
    for section in t("profile.sections"):
        st.subheader(section["title"])
        st.markdown(section["body"])

    st.markdown('</div>', unsafe_allow_html=True)

    if st.button(t("profile.button"), type="primary"):
        st.session_state.scroll_to_top = True
        goto("simulation")


# ==================== SIMULATION ====================
elif st.session_state.page == "simulation":

    if st.session_state.month > 24:
        goto("post_question_0")

    scroll_top_anchor()

    month = st.session_state.month
    loan = st.session_state.loan
    overdraft = st.session_state.overdraft

    data = get_month(month)
    income_total = month_sum(data["income"])
    expenses_total = month_sum(data["expenses"])
    obligations = data.get("obligations", {})
    opening_balance = get_opening_balance(month, data)
    loan_obligation = money(loan.get_required_payment())
    no_loan_due = loan.balance <= 0 and loan_obligation <= 0
    credit_interest = money(loan.apply_interest())
    overdraft_interest = money(overdraft.apply_interest())
    penalties = money(obligations.get("penalties", 0))
    available_total = money(opening_balance + income_total)
    outflows_before_credit = money(expenses_total + overdraft_interest + credit_interest + penalties)
    liquidity_after_charges = money(max(0.0, available_total - outflows_before_credit))
    deficit_before_credit = money(max(0.0, outflows_before_credit - available_total))
    overdraft_after_charges = money(overdraft.balance + deficit_before_credit)
    overdraft_remaining = money(max(0.0, overdraft.limit - min(overdraft_after_charges, overdraft.limit)))
    max_payment = money(liquidity_after_charges + overdraft_remaining)
    blocked = overdraft_after_charges > overdraft.limit

    col_title, col_score = st.columns([5, 1])
    with col_title:
        st.title(t("simulation.month_title", month=month))
    with col_score:
        st.metric(t("simulation.score_accumulated"), display_number(st.session_state.total_score))

    with st.expander(t("simulation.narrative_expander"), expanded=True):
        narrative = re.sub(r'^(\S+)', r'<strong>\1</strong>', get_localized_narrative(month))
        st.markdown(
            f'<div style="text-align: justify">{narrative}</div>',
            unsafe_allow_html=True,
        )
    auto_open_context_narrativ(t("simulation.narrative_expander"))

    with st.expander(t("simulation.budget_expander")):
        st.markdown(t("simulation.income_header"))
        st.table(display_value_table(data["income"]))
        st.write(t("simulation.income_total", value=display_number(income_total)))

        st.markdown(t("simulation.expenses_header"))
        st.table(display_value_table(data["expenses"]))
        st.write(t("simulation.expenses_total", value=display_number(expenses_total)))

    opening_balance_html = (
        f'<div class="decision-row positive"><strong>{t("simulation.opening_balance")}:</strong> {display_euro(opening_balance)}</div>'
        if month == 1
        else ""
    )

    st.markdown(
        f"""
<div class="decision-card">
<div class="decision-card-title">{t("simulation.decision_title")}</div>
{opening_balance_html}
<div class="decision-row positive"><strong>{t("simulation.income_total_label")}:</strong> {display_euro(income_total)}</div>
<div class="decision-row risk"><strong>{t("simulation.expenses_total_label")}:</strong> {display_euro(expenses_total)}</div>
<div class="decision-row risk"><strong>{t("simulation.overdraft_interest_label")}:</strong> {display_euro(overdraft_interest)} | <strong>{t("simulation.credit_interest_label")}:</strong> {display_euro(credit_interest)}</div>
<div class="decision-row risk"><strong>{t("simulation.remaining_credit_label")}:</strong> {display_euro(loan.balance)} | <strong>{t("simulation.used_overdraft_label")}:</strong> {display_euro(overdraft.balance)}</div>
<div class="decision-row positive"><strong>{t("simulation.available_before_payment_label")}:</strong> {display_euro(liquidity_after_charges)}</div>
<div class="decision-row formula">{t("simulation.available_before_payment_formula")}</div>
<div class="decision-row primary"><strong>{t("simulation.contract_rate_label")}:</strong> {display_euro(loan_obligation)}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    if blocked:
        st.error(t("simulation.blocked_error"))

    payment = None
    if no_loan_due:
        st.info(t("simulation.no_payment_due_notice"))
    else:
        st.markdown(f'<div class="payment-label">{t("simulation.payment_label")}</div>', unsafe_allow_html=True)
        payment = st.number_input(
            t("simulation.payment_label"),
            min_value=0.0,
            step=1.0,
            value=None,
            format="%g",
            placeholder=t("simulation.payment_placeholder"),
            key=f"payment_{month}",
            label_visibility="collapsed",
        )
        attach_payment_keyboard_bridge()
        st.markdown(
            f"""
<div class="auth-info payment-note">
  <span class="auth-info-icon">i</span>
  <span>{t("simulation.payment_note")}</span>
</div>
""",
            unsafe_allow_html=True,
        )
    st.markdown('<div class="payment-button-gap"></div>', unsafe_allow_html=True)

    button_label = t("simulation.continue_month_button") if no_loan_due else t("simulation.confirm_button")
    if st.button(button_label, type="primary"):
        if not no_loan_due and payment is None:
            st.warning(t("simulation.payment_validation_warning"))
            st.stop()

        result = normalize_month_result_score(compute_month_result(month, data, loan, overdraft, payment))
        st.session_state.pending_month_result = result
        if not persist_month_result_snapshot(result, bonus_max_session=get_bonus_max_session()):
            st.error(t("simulation.save_error"))
            st.stop()
        goto("month_feedback")


# ==================== MONTH FEEDBACK ====================
elif st.session_state.page == "month_feedback":
    scroll_top_anchor()

    result = st.session_state.get("pending_month_result")
    if not result:
        goto("simulation")
    result = normalize_month_result_score(result)
    st.session_state.pending_month_result = result

    month = result["month"]
    st.title(t("simulation.feedback_title", month=month))

    st.markdown(t("simulation.decision_result_heading"))
    st.write(t("simulation.payment_entered", value=display_euro(result["payment_input"])))
    st.write(t("simulation.payment_accepted", value=display_euro(result["accepted_payment"])))
    st.write(t("simulation.cash_after_payment", value=display_euro(result["cash_final"])))
    st.write(t("simulation.credit_remaining", value=display_euro(result["credit_final"])))
    st.write(t("simulation.overdraft_final", value=display_euro(result["overdraft_final"])))
    st.write(t("simulation.credit_interest_month", value=display_euro(result["credit_interest"])))
    st.write(t("simulation.overdraft_interest_month", value=display_euro(result["overdraft_interest"])))
    if result["penalties"] > 0:
        st.write(t("simulation.penalties_month", value=display_euro(result["penalties"])))
    st.markdown(t("simulation.monthly_score_heading"))
    st.write(t("simulation.score_repayment", value=display_number(result["score_repayment"])))
    st.write(t("simulation.score_liquidity", value=display_number(result["score_liquidity"])))
    st.write(t("simulation.score_overdraft", value=display_number(result["score_overdraft"])))
    st.metric(t("simulation.monthly_score_metric"), f"{display_number(result['monthly_score'])} / 100")
    st.metric(t("simulation.score_accumulated"), display_number(st.session_state.total_score + result["monthly_score"]))

    if result["pre_credit_impossible"]:
        st.error(result["feedback_message"])
    elif result["payment_valid"]:
        st.success(result["feedback_message"])
    else:
        st.warning(result["feedback_message"])

    if st.button(t("simulation.continue_month_button"), type="primary"):
        st.session_state.loan.balance = result["credit_final"]
        st.session_state.overdraft.balance = result["overdraft_final"]
        st.session_state.total_score += result["monthly_score"]
        st.session_state.monthly_points += result["monthly_score"]
        st.session_state.accumulated_costs += result["costs_this_month"]
        st.session_state.monthly_results.append(result)
        if not persist_month_result_snapshot(result, bonus_max_session=get_bonus_max_session()):
            st.error(t("simulation.save_error"))
            st.stop()
        if not persist_session_summary_snapshot(get_final_score_breakdown(), feedback=st.session_state.answers.get("feedback")):
            st.error("Error while saving session summary. Please reload the page and try again.")
            st.stop()
        st.session_state.pending_month_result = None
        st.session_state.month += 1
        goto("simulation")


# ==================== POST-SIMULATION QUESTIONS ====================
elif st.session_state.page.startswith("post_question_"):
    scroll_top_anchor()
    post_sections = get_display_post_sections()
    try:
        post_index = int(st.session_state.page.rsplit("_", 1)[1])
    except Exception:
        goto("post_question_0")

    if post_index >= len(post_sections):
        goto("final_score")

    section = post_sections[post_index]
    next_page = "final_score" if post_index + 1 >= len(post_sections) else f"post_question_{post_index + 1}"
    question_offset = sum(len(post_section["questions"]) for post_section in post_sections[:post_index])

    st.title(t("quiz.post_title"))
    st.caption(t("quiz.chapter_label", current=post_index + 1, total=len(post_sections)))
    st.progress((post_index + 1) / len(post_sections))
    render_question_section(section, post_index + 1, question_offset)

    if not all_answered([section]):
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

    if DEV:
        if st.button(t("quiz.dev_randomize"), type="secondary", key=f"dev_post_question_{post_index}"):
            randomize_section(section)
            st.session_state.scroll_to_top = True
            goto(next_page)

    button_label = t("quiz.post_finish_button") if post_index + 1 >= len(post_sections) else t("quiz.continue_button")
    if st.button(button_label, type="primary", key=f"continue_post_question_{post_index}"):
        if all_answered([section]):
            if not persist_post_psychometrics():
                st.error("Error while saving questionnaire answers. Please reload the page and try again.")
                st.stop()
            st.session_state.scroll_to_top = True
            goto(next_page)
        else:
            st.error(t("quiz.chapter_missing_error"))


# ==================== FINAL SCORE ====================
elif st.session_state.page == "final_score":
    scroll_top_anchor()

    st.session_state.final_score = compute_final_score()

    breakdown = get_final_score_breakdown()

    st.title(t("final_score.title"))
    st.markdown(t("final_score.intro"))
    st.markdown(t("final_score.heading"))
    st.markdown(
        f"""
<div class="final-score-card">
  <span class="final-score-label">{t("final_score.card_label")}</span>
  <span class="final-score-value">{display_number(breakdown["final_score"])} / 100</span>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
**{t("final_score.bonus_label")}:** {display_euro(breakdown["bonus_final"])}

{t("final_score.summary_heading")}

**{t("final_score.total_repaid")}:** {display_euro(breakdown["total_repaid"])}

**{t("final_score.remaining_credit")}:** {display_euro(breakdown["remaining_credit"])}

**{t("final_score.remaining_overdraft")}:** {display_euro(breakdown["remaining_overdraft"])}

**{t("final_score.interest_total")}:** {display_euro(breakdown["interest_total"])}
"""
    )
    st.info(t("final_score.info"))
    st.caption(t("final_score.caption"))

    if st.button(t("final_score.button"), type="primary"):
        st.session_state.scroll_to_top = True
        goto("done")


# ==================== DONE ====================
elif st.session_state.page == "done":
    scroll_top_anchor()
    st.session_state.final_score = compute_final_score()
    breakdown = get_final_score_breakdown()
    st.session_state.answers["financial_summary"] = breakdown

    if not st.session_state.get("saved"):
        try:
            finalize_participant(
                st.session_state.session_id,
                st.session_state.answers,
                st.session_state.final_score,
                monthly_results=[
                    normalize_month_result_score(result)
                    for result in st.session_state.get("monthly_results", [])
                ],
                summary={
                    **breakdown,
                    "scenario_version": SCENARIO_VERSION,
                },
                pre_sections=PRE_SECTIONS_RO,
                post_sections=POST_SECTIONS_RO,
            )
            st.session_state.saved = True
        except Exception as e:
            st.error(t("done.save_error", error=e))

    st.title(t("done.title"))
    st.metric(t("done.score_metric"), f"{display_number(st.session_state.final_score)} / 100")
    st.markdown(f"**{t('done.bonus_label')}:** {display_euro(breakdown['bonus_final'])}")
    st.markdown(
        f"""
{t("done.remaining_credit")}: **{display_euro(st.session_state.loan.balance)}**

{t("done.remaining_overdraft")}: **{display_euro(st.session_state.overdraft.balance)}**

{t("done.registered_text")}

{t("done.contact")}: coita.iflorina@gmail.com
"""
    )

persist_checkpoint()

