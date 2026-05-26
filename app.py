import re
import random
import os
import streamlit as st
import pandas as pd

from auth_manager import is_logged_in
from narratives import get_narrative
from tables import get_month
from questions import PRE_SECTIONS, POST_SECTIONS
from state_manager import (
    REPEAT_SCENARIO_DEV_MODE,
    bootstrap_authenticated_session,
    finalize_participant,
    persist_checkpoint,
    start_new_scenario,
)

DEV = os.getenv("SCENARIO_DEV", "").lower() == "true"
RECOMMENDED_BUFFER = 150.0
SESSION_MONTHS = 24


def get_bonus_max_session():
    try:
        value = st.secrets.get("BONUS_MAXIM_SESIUNE", os.getenv("BONUS_MAXIM_SESIUNE", 24))
    except Exception:
        value = os.getenv("BONUS_MAXIM_SESIUNE", 24)

    try:
        return money(value)
    except (TypeError, ValueError):
        return 24.0

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

.st-key-account_menu {
    position: fixed;
    left: 1rem;
    bottom: 1rem;
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
    flex-direction: column-reverse;
}

.st-key-account_menu details > summary {
    min-height: 2.7rem;
    padding: 0.65rem 0.85rem !important;
    background: #fbf8f0 !important;
}

.st-key-account_menu details[open] > summary {
    background: #fbf8f0 !important;
    border-top: 1px solid #e5decc;
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


def auto_open_context_narrativ(month):
    st.components.v1.html(
        """
<script>
(function() {
  function openNarrative() {
    try {
      var doc = window.parent.document;
      var expander = Array.from(doc.querySelectorAll('details')).find(function(el) {
        return (el.textContent || '').includes('Context narativ');
      });
      if (!expander) return;
      if (expander.open) return;
      var summary = expander.querySelector('summary');
      if (summary) summary.click();
    } catch (e) {}
  }

  setTimeout(openNarrative, 80);
  setTimeout(openNarrative, 300);
})();
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
            """
<div class="auth-brand">
  <span class="auth-brand-mark">S</span>
  <span>ScenariuCredit</span>
</div>
<div class="auth-rule"></div>
<h1 class="auth-title">Decizii financiare sub presiune</h1>
<p class="auth-copy">Autentifică-te pentru a începe sau relua scenariul exact din punctul în care ai rămas.</p>
<div class="auth-signals">
  <span class="auth-chip">Progres salvat</span>
  <span class="auth-chip">Reluare după întrerupere</span>
  <span class="auth-chip">Răspunsuri separate</span>
</div>
""",
            unsafe_allow_html=True,
        )
        if st.button("Continuă cu Google", key="google_login", use_container_width=True):
            st.login()
        st.markdown(
            """
<p class="auth-privacy"><strong>Confidențialitate:</strong> Platforma folosește autentificarea Google pentru identificarea sesiunii, prevenirea participărilor multiple și reluarea progresului în caz de întrerupere. Aplicația poate accesa numele, fotografia de profil și adresa de e-mail asociate contului Google. Aceste date de identificare vor fi stocate separat de răspunsurile experimentale. Analiza statistică se va realiza pe date pseudonimizate, folosind un cod unic de participant, fără includerea adresei de e-mail, numelui sau fotografiei de profil în setul de date analizat.</p>
<div class="auth-info">
  <span class="auth-info-icon">i</span>
  <span>Răspunsurile tale vor fi analizate în mod anonim și vor ajuta la înțelegerea legăturii dintre trăsăturile individuale și modul în care oamenii iau decizii financiare în condiții incerte sau stresante.</span>
</div>
""",
            unsafe_allow_html=True,
        )
# AUTHENTICATION AND INIT STATE

# -------------------------
if not is_logged_in():
    render_login_page()
    st.stop()

if not st.session_state.get("_bootstrap_done"):
    bootstrap_authenticated_session()
    st.session_state._bootstrap_done = True


def render_account_menu():
    email = st.user.get("email") or st.user.get("name") or "Cont conectat"
    with st.container(key="account_menu"):
        with st.expander(email):
            if st.button("Log out", icon=":material/logout:", key="account_logout", use_container_width=True):
                st.logout()


render_account_menu()


def render_question_section(section, chapter_number, question_offset=0):
    st.markdown(f"### Capitolul {chapter_number}")
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


def render_quiz_chapter(
    section,
    chapter_index,
    total_chapters,
    next_page,
    dev_label,
    title,
    skip_page=None,
    question_offset=0,
):
    st.title(title)
    st.caption(f"Capitolul {chapter_index + 1} din {total_chapters}")
    st.markdown("Răspunde la capitolul curent, apoi apasă **Continuă** pentru a trece mai departe.")
    st.progress((chapter_index + 1) / total_chapters)
    render_question_section(section, chapter_index + 1, question_offset)

    if DEV:
        if st.button(dev_label, type="secondary", key=f"dev_{section['key_prefix']}_{chapter_index}"):
            randomize_section(section)
            st.session_state.scroll_to_top = True
            goto(next_page)

    if skip_page is not None:
        if st.button("Skip all chapters", type="secondary", key=f"skip_{section['key_prefix']}_{chapter_index}"):
            st.session_state.scroll_to_top = True
            goto(skip_page)

    if not all_answered([section]):
        st.warning("Te rugăm să răspunzi la toate întrebările din acest capitol înainte de a continua.")

    if st.button("Continuă →", type="primary", key=f"continue_{section['key_prefix']}_{chapter_index}"):
        if all_answered([section]):
            st.session_state.scroll_to_top = True
            goto(next_page)
        else:
            st.error("Sunt întrebări fără răspuns.")


def money(value):
    return round(float(value), 2)


def display_number(value):
    value = money(value)
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}"


def display_euro(value):
    return f"{display_number(value)} €"


def display_value_table(values):
    rows = [(category, display_number(amount)) for category, amount in values.items()]
    return pd.DataFrame(rows, columns=["Categoria", "Valoare (€)"])


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


def compute_monthly_score(accepted_payment, cash_final, overdraft_final, overdraft_limit, loan_obligation):
    if loan_obligation <= 0:
        repayment_score = 40.0
    else:
        repayment_score = min(accepted_payment / loan_obligation, 1.0) * 40.0

    liquidity_score = min(cash_final / RECOMMENDED_BUFFER, 1.0) * 30.0
    overdraft_score = 30.0 if overdraft_limit <= 0 else max(0.0, 30.0 * (1.0 - overdraft_final / overdraft_limit))
    monthly_score = min(100.0, max(0.0, repayment_score + liquidity_score + overdraft_score))

    return {
        "score_model": "behavioral_v1",
        "score_repayment": money(repayment_score),
        "score_liquidity": money(liquidity_score),
        "score_overdraft": money(overdraft_score),
        "monthly_score": money(monthly_score),
        "bonus_lunar": money(monthly_score / 100.0 * (get_bonus_max_session() / SESSION_MONTHS)),
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
        )
    )
    return result


def compute_month_result(month, data, loan, overdraft, payment):
    income_total = month_sum(data["income"])
    expenses_total = month_sum(data["expenses"])
    obligations = data.get("obligations", {})
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
    payment_value = None if payment is None else money(payment)
    capped_payment = None if payment_value is None else money(min(payment_value, loan.balance))
    payment_valid = (
        not pre_credit_impossible
        and payment_value is not None
        and payment_value >= 0
        and capped_payment <= max_payment
    )

    if pre_credit_impossible:
        feedback_message = (
            "Cheltuielile lunii depășesc lichiditatea disponibilă și limita de overdraft. "
            "Plata creditului nu poate fi executată. Pentru această lună, scorul este 0."
        )
        accepted_payment = 0.0
        overdraft_from_payment = 0.0
        overdraft_final = money(overdraft.limit)
        cash_final = 0.0
        credit_final = money(loan.balance)
        score_data = zero_score_data()
        invalid_reason = "pre_credit"
    elif payment_valid:
        accepted_payment = capped_payment
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
        )
        feedback_message = (
            "Decizia a fost acceptată. Plata a fost înregistrată, iar soldurile au fost actualizate."
        )
        invalid_reason = None
    else:
        accepted_payment = 0.0
        overdraft_from_payment = 0.0
        overdraft_final = money(overdraft_after_charges)
        cash_final = money(liquidity_after_charges)
        credit_final = money(loan.balance)
        score_data = zero_score_data()
        feedback_message = (
            "Suma introdusă depășește lichiditatea disponibilă și limita de overdraft rămasă. "
            "Plata nu a fost executată. Pentru această lună, scorul este 0."
        )
        invalid_reason = "payment"

    if overdraft_final > overdraft.limit:
        overdraft_final = money(overdraft.limit)
        cash_final = 0.0
        if score_data["monthly_score"] > 0:
            accepted_payment = 0.0
            credit_final = money(loan.balance)
            overdraft_from_payment = 0.0
            score_data = zero_score_data()
            feedback_message = (
                "Suma introdusă depășește lichiditatea disponibilă și limita de overdraft rămasă. "
                "Plata nu a fost executată. Pentru această lună, scorul este 0."
            )
            invalid_reason = "payment"

    return {
        "month": month,
        "opening_balance": opening_balance,
        "income_total": income_total,
        "expenses_total": expenses_total,
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
    final_score = money(min(100.0, max(0.0, monthly_score_sum / SESSION_MONTHS)))
    bonus_max_session = get_bonus_max_session()
    bonus_final = money(final_score / 100.0 * bonus_max_session)
    total_repaid = money(sum(float(result.get("accepted_payment", 0.0)) for result in monthly_results))
    credit_interest_total = money(sum(float(result.get("credit_interest", 0.0)) for result in monthly_results))
    overdraft_interest_total = money(sum(float(result.get("overdraft_interest", 0.0)) for result in monthly_results))
    return {
        "months_completed": len(monthly_results),
        "monthly_score_sum": monthly_score_sum,
        "final_score": final_score,
        "bonus_max_session": bonus_max_session,
        "bonus_final": bonus_final,
        "total_repaid": total_repaid,
        "remaining_credit": money(st.session_state.loan.balance),
        "remaining_overdraft": money(st.session_state.overdraft.balance),
        "credit_interest_total": credit_interest_total,
        "overdraft_interest_total": overdraft_interest_total,
        "interest_total": money(credit_interest_total + overdraft_interest_total),
    }


# ==================== COMPLETED ACCOUNT ====================
if st.session_state.page == "already_completed":
    scroll_top_anchor()
    st.title("Participare deja finalizată")
    st.info("Acest cont a finalizat deja scenariul. Nu poate fi trimis un al doilea răspuns.")
    if REPEAT_SCENARIO_DEV_MODE and st.button("Începe un scenariu nou (test)", type="primary"):
        start_new_scenario()
        st.rerun()


# ==================== HOME ====================
elif st.session_state.page == "home":
    scroll_top_anchor()
    st.markdown("""
<style>
.home-title { text-align: center; font-size: 2rem; font-weight: 700; margin-bottom: 1rem; }
.home-body { text-align: justify; }
</style>
<div class="home-title">Percepția riscului și decizia financiară în condiții de incertitudine</div>
""", unsafe_allow_html=True)
    st.markdown('<div class="home-body">', unsafe_allow_html=True)
    st.markdown("""
Acest studiu își propune să investigheze modul în care indivizii percep și evaluează riscul
atunci când iau decizii financiare în contexte incerte sau instabile. Vei fi invitat(ă) să
parcurgi o serie de scenarii realiste de creditare, în care va trebui să formulezi estimări
și să iei decizii care implică bani, timp și responsabilitate. În paralel, vom analiza
reacțiile tale subiective privind nivelul de stres, presiunea socială, încărcătura
emoțională și încrederea în propriile judecăți.

Scopul este de a înțelege cum interacționează stările afective și profilul psihologic cu
procesul decizional în situații economice riscante.
    """)
    st.info(
        "Chestionarele sunt validate științific și nu conțin răspunsuri «corecte» sau «greșite». "
        "Răspunde cât mai sincer, alegând opțiunea care reflectă cel mai bine cum ești tu în general."
    )
    st.markdown(
        "Răspunsurile tale vor fi analizate **în mod anonim** și vor ajuta la înțelegerea legăturii "
        "dintre trăsăturile individuale și modul în care oamenii iau decizii financiare în condiții "
        "incerte sau stresante."
    )
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Începe scenariul →", type="primary"):
        st.session_state.scroll_to_top = True
        goto("consent")


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
    st.markdown("""
## Acord de participare și consimțământ informat

### Titlul studiului

Percepția riscului și decizia financiară în condiții de incertitudine

### Invitație de participare

Ești invitat(ă) să participi la un studiu de cercetare despre modul în care persoanele iau decizii financiare în condiții de incertitudine. Studiul include un experiment financiar structurat, în care vei lua decizii lunare privind rambursarea unui credit, pe baza unor informații despre venituri, cheltuieli, sold disponibil și evoluția obligațiilor financiare.

Participarea este voluntară. Te rugăm să citești cu atenție informațiile de mai jos înainte de a decide dacă dorești să continui.

### Scopul studiului

Scopul studiului este de a analiza relația dintre profilul psihologic, percepția riscului, nivelul de stres și deciziile financiare luate într-un experiment de credit.

Studiul urmărește să înțeleagă cum variază deciziile de rambursare în funcție de factori precum impulsivitatea, reglarea emoțională, toleranța la incertitudine, încrederea în propriile judecăți și reacțiile afective produse de sarcina financiară.

### Ce presupune participarea

Dacă accepți să participi, vei parcurge următoarele etape:

- vei citi informațiile despre studiu și vei confirma consimțământul informat;
- vei completa un scurt profil demografic;
- vei răspunde la un chestionar psihologic inițial;
- vei parcurge un experiment financiar structurat pe mai multe luni, în care vei lua decizii privind rambursarea unui credit;
- vei completa un chestionar final despre starea ta psihologică după experiment și despre percepția asupra sarcinii.

În cadrul experimentului, vei primi informații financiare lunare și vei decide suma pe care dorești să o aloci rambursării creditului. Experimentul este construit pentru a reflecta situații financiare realiste, fără a implica acces la conturi bancare reale sau modificări asupra unor obligații financiare personale.

### Durata estimată

Participarea durează aproximativ 30–45 de minute, în funcție de ritmul de completare.

### Tipuri de date colectate

În cadrul studiului pot fi colectate următoarele categorii de date:

- răspunsuri la întrebări demografice generale;
- răspunsuri la chestionare psihometrice;
- deciziile introduse în cadrul experimentului financiar;
- indicatori calculați automat pe baza deciziilor luate în experiment, precum soldul creditului, utilizarea overdraftului, penalități, dobânzi și scoruri experimentale;
- răspunsuri la întrebări finale despre experiența în cadrul experimentului.

Nu ți se va cere să furnizezi date bancare reale, parole, coduri de acces, extrase de cont reale sau informații financiare identificabile.

Dacă studiul va include în viitor date suplimentare, precum date open banking, profil profesional sau date din alte surse, acestea vor fi prezentate separat și vor necesita consimțământ distinct. În această versiune a studiului, sarcina financiară se bazează exclusiv pe informațiile prezentate în platforma experimentală.

### Natura experimentului

Situațiile financiare, evenimentele lunare și informațiile prezentate în cadrul experimentului sunt construite pentru scopuri de cercetare. Acestea nu reprezintă o evaluare a situației tale financiare personale și nu produc efecte asupra vreunui credit real, cont bancar sau raport de credit.

Deciziile tale din cadrul experimentului sunt folosite exclusiv în scop de cercetare.

### Posibile riscuri sau disconfort

Studiul include situații legate de credit, datorii, presiune financiară, stres, obligații lunare și incertitudine. Unele persoane pot resimți ușor disconfort, tensiune sau oboseală în timpul parcurgerii experimentului.

Nu există răspunsuri corecte sau greșite. Nu evaluăm competența ta financiară și nu formulăm judecăți individuale despre deciziile tale.

Poți întrerupe participarea în orice moment, fără să oferi explicații.

### Beneficii

Nu există un beneficiu personal direct garantat. Participarea ta poate contribui la o mai bună înțelegere a modului în care oamenii iau decizii financiare în contexte incerte sau stresante.

Rezultatele pot fi folosite pentru cercetare academică, dezvoltarea unor modele de analiză comportamentală și proiectarea unor instrumente educaționale sau experimentale în domeniul finanțelor comportamentale.

### Confidențialitate și anonimitate

Datele vor fi analizate în formă anonimă sau pseudonimizată. Răspunsurile individuale nu vor fi publicate în mod identificabil.

Dacă platforma folosește un cod de participant, acesta va fi utilizat doar pentru a lega răspunsurile inițiale, deciziile din cadrul experimentului și răspunsurile finale. Codul nu va fi folosit pentru identificarea publică a participantului.

Rezultatele vor fi raportate agregat, de exemplu sub formă de medii, corelații, modele statistice sau grafice.

### Participare voluntară și retragere

Participarea este voluntară. Ai dreptul:

- să refuzi participarea;
- să întrerupi completarea în orice moment;
- să nu răspunzi la o întrebare, dacă aceasta permite opțiune de necompletare;
- să soliciți informații suplimentare despre studiu.

Retragerea din studiu nu va avea consecințe negative asupra ta.

### Compensație

Participarea la acest studiu poate include o compensație fixă pentru participare și/sau o recompensă experimentală calculată pe baza deciziilor luate în cadrul experimentului financiar.

Recompensa experimentală are rol exclusiv de stimulent în cadrul studiului și nu reprezintă o evaluare reală a situației financiare, a competenței financiare sau a bonității participantului.

### Utilizarea rezultatelor

Datele colectate pot fi utilizate pentru: analize statistice; lucrări științifice; prezentări academice; rapoarte de cercetare; dezvoltarea unor modele experimentale privind decizia financiară.

Nicio publicație sau prezentare nu va include informații care să permită identificarea directă a participanților.

### Contact

Pentru întrebări despre studiu sau despre utilizarea datelor, poți contacta echipa de cercetare la:

coita.iflorina@gmail.com

### Declarație de consimțământ

Te rugăm să confirmi următoarele afirmații înainte de a continua:
""")
    st.markdown('</div>', unsafe_allow_html=True)

    consent_items = [
        "Am citit și am înțeles informațiile despre studiu.",
        "Am înțeles că participarea este voluntară.",
        "Am înțeles că pot întrerupe participarea în orice moment.",
        "Am înțeles că voi parcurge un experiment financiar care poate include situații de presiune financiară, stres și incertitudine.",
        "Am înțeles că datele mele vor fi analizate anonim sau pseudonimizat.",
        "Am înțeles că nu mi se cer date bancare reale sau informații financiare identificabile.",
        "Am înțeles că deciziile luate în cadrul experimentului nu afectează un credit real, un cont bancar sau un raport de credit.",
        "Sunt de acord să particip la acest studiu.",
    ]
    with st.form("consent_form"):
        consent_values = [
            st.checkbox(item, key=f"consent_item_{index}")
            for index, item in enumerate(consent_items)
        ]
        consent_complete = all(consent_values)

        col_accept, col_decline = st.columns([2, 1])
        with col_accept:
            accept_clicked = st.form_submit_button(
                "Sunt de acord și doresc să continui",
                type="primary",
                use_container_width=True,
            )
        with col_decline:
            decline_clicked = st.form_submit_button(
                "Nu sunt de acord",
                type="secondary",
                use_container_width=True,
            )

        if accept_clicked:
            if not consent_complete:
                st.warning("Te rugăm să confirmi toate afirmațiile înainte de a continua.")
                st.stop()
            st.session_state.answers["consent_agreed"] = "1 - Da"
            st.session_state.scroll_to_top = True
            goto("pre_question_0")

        if decline_clicked:
            st.session_state.answers["consent_agreed"] = "0 - Nu"
            st.session_state.scroll_to_top = True
            goto("consent_declined")


# ==================== CONSENT DECLINED ====================
elif st.session_state.page == "consent_declined":
    scroll_top_anchor()
    st.title("Participare întreruptă")
    st.markdown(
        "Ai ales să nu îți dai consimțământul pentru participare. Participarea este voluntară, "
        "iar chestionarul nu va începe fără acordul tău."
    )
    if st.button("Înapoi la acordul de participare", type="primary"):
        st.session_state.scroll_to_top = True
        goto("consent")


# ==================== PRE-SIMULATION QUESTIONS ====================
elif st.session_state.page == "pre_questions":
    goto("consent" if st.session_state.answers.get("consent_agreed") != "1 - Da" else "pre_question_0")

elif st.session_state.page.startswith("pre_question_"):
    scroll_top_anchor()
    if st.session_state.answers.get("consent_agreed") != "1 - Da":
        goto("consent")

    try:
        pre_index = int(st.session_state.page.rsplit("_", 1)[1])
    except Exception:
        goto("pre_question_0")

    if pre_index >= len(PRE_SECTIONS):
        goto("instructions")

    next_page = "instructions" if pre_index + 1 >= len(PRE_SECTIONS) else f"pre_question_{pre_index + 1}"
    render_quiz_chapter(
        PRE_SECTIONS[pre_index],
        pre_index,
        len(PRE_SECTIONS),
        next_page,
        "⚡ DEV: Randomizează acest capitol și continuă",
        "Chestionar – înainte de scenariu",
        skip_page="instructions",
        question_offset=sum(len(section["questions"]) for section in PRE_SECTIONS[:pre_index]),
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
    st.markdown(
        """
## Instrucțiuni pentru participant

În acest experiment vei lua rolul lui Andrei, o persoană care are un credit de nevoi personale și trebuie să ia decizii lunare de rambursare.

Experimentul se desfasoara pe parcursul a 24 de luni.

În fiecare lună vei vedea informații despre situația financiară a lunii respective:

- veniturile lunii;
- cheltuielile lunii;
- dobânda creditului;
- dobânda overdraftului, dacă există;
- banii disponibili înainte de plata creditului;
- soldul creditului;
- overdraftul utilizat;
- rata lunară prevăzută în contract.

După ce citești informațiile lunii, trebuie să introduci suma pe care dorești să o rambursezi din credit în acea lună.

Tu decizi doar suma plătită pentru credit.

Nu trebuie să rambursezi separat overdraftul. Overdraftul se actualizează automat în platformă, în funcție de deficitul lunii și de suma introdusă pentru plata creditului.

### Ce este overdraftul

Overdraftul este o linie de credit atașată contului curent. În acest experiment, limita maximă de overdraft este de 3.000 euro.

Overdraftul funcționează ca o rezervă de bani împrumutați. Dacă banii disponibili nu sunt suficienți pentru cheltuielile lunii sau pentru plata introdusă de tine, platforma poate folosi overdraftul, dar numai în limita disponibilă.

Utilizarea overdraftului crește gradul de îndatorare și reduce scorul lunar.

### Cum se calculează suma disponibilă înainte de plata creditului

În fiecare lună, platforma calculează automat banii disponibili înainte de plata creditului.

Formula este:

Bani disponibili înainte de plata creditului =
sold inițial disponibil + venituri totale - cheltuieli curente - dobândă credit - dobândă overdraft

Această sumă arată cât este disponibil înainte ca tu să introduci plata pentru credit.

### Cum funcționează decizia lunară

În fiecare lună vei introduce o singură sumă:

suma pe care dorești să o plătești pentru credit în luna respectivă.

Apoi apeși:

Confirmă decizia

După confirmare, decizia nu mai poate fi modificată.

Platforma va calcula automat:

- dacă plata poate fi realizată;
- cât scade soldul creditului;
- dacă se folosește overdraftul;
- care este suma rămasă după plată;
- care este overdraftul final al lunii;
- ce scor primești pentru luna respectivă.

După confirmare, vei vedea un ecran de feedback pentru luna curentă. Acolo vei vedea rezultatul deciziei tale. Apoi vei apăsa:

Continuă către luna următoare

### Ce se întâmplă dacă introduci o sumă posibilă

Dacă suma introdusă poate fi acoperită din banii disponibili și din overdraftul rămas, plata este acceptată.

În acest caz:

- plata se înregistrează;
- soldul creditului scade;
- soldurile lunii se actualizează;
- scorul lunii se calculează automat.

### Ce se întâmplă dacă introduci o sumă invalida

Dacă introduci o sumă mai mare decât banii disponibili plus overdraftul rămas, plata nu poate fi realizată.

În acest caz:

- plata este respinsă;
- creditul nu scade prin acea plată;
- suma introdusă nu se transferă în overdraft;
- limita maximă de overdraft nu este depășită;
- scorul lunii este 0;
- experimentul continuă cu luna următoare.

După ce ai confirmat o sumă invalida, nu vei putea reveni pentru a o corecta. De aceea, este important să verifici atent informațiile înainte de confirmare.

### Ce poți corecta înainte de confirmare

Înainte să apeși „Confirmă decizia”, poți corecta suma introdusă.

Dacă introduci din greșeală litere, semne sau o valoare negativă, platforma îți va cere să introduci o valoare numerică validă.

### Cum se acordă scorul lunar

În fiecare lună, scorul poate varia între 0 și 100 de puncte.

Scorul lunar ține cont de trei aspecte:

1. suma rambursată din credit;
2. banii rămași disponibili după plată;
3. nivelul overdraftului utilizat.

O plată mai mare din credit poate crește scorul de rambursare, dar trebuie să fie susținută de situația financiară a lunii.

Păstrarea unei rezerve de bani după plată contribuie la scorul de lichiditate.

Utilizarea unui overdraft mai mare reduce scorul lunar.

Scorul lunar nu reprezintă o evaluare personală. El reflectă doar rezultatul financiar al deciziei introduse în condițiile lunii respective.

### Cum se calculează scorul final

La finalul celor 24 de luni, platforma calculează scorul comportamental final.

Scorul comportamental final este media scorurilor lunare obținute în cele 24 de luni.

Formula generală este:

Scor comportamental final =
media scorurilor lunare din cele 24 de luni

Bonusul final este calculat în funcție de scorul comportamental final.

### Ce se afișează la final

La finalul experimentului vei vedea:

- scorul comportamental final;
- bonusul final obținut;
- creditul rămas la final;
- overdraftul utilizat la final;
- dobânzile totale acumulate, dacă sunt afișate în versiunea finală a platformei.

### Regula generală a experimentului

Scopul nu este să plătești mereu aceeași sumă.

Scopul este să iei o decizie lunară care poate fi susținută de situația financiară a lunii respective.

În unele luni poate fi mai ușor să plătești rata lunară prevăzută în contract. În alte luni, din cauza veniturilor, cheltuielilor și dobânzilor, decizia poate fi mai dificilă.

Trebuie să alegi suma pe care o consideri potrivită, ținând cont de:

- venituri;
- cheltuieli;
- dobânda creditului;
- dobânda overdraftului;
- creditul rămas;
- overdraftul utilizat;
- banii disponibili înainte de plată;
- riscul de a introduce o plată imposibilă.

### Mesaj important înainte de începerea experimentului

Te rugăm să citești cu atenție informațiile fiecărei luni înainte de a introduce suma de rambursat.

După ce apeși „Confirmă decizia”, suma introdusă nu mai poate fi modificată.

Dacă suma introdusă depășește resursele disponibile și limita de overdraft, plata nu va fi executată, iar scorul lunii va fi 0.
""",
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Continuă către profil →", type="primary"):
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

    st.title("Profilul participantului")
    st.markdown("Înainte de a începe scenariul, citește cu atenție profilul personajului pe care îl vei reprezenta.")

    st.markdown('<div class="profile-text">', unsafe_allow_html=True)

    st.subheader("Profil general – Andrei")
    st.markdown("""
| | |
|---|---|
| **Nume** | Andrei |
| **Vârstă** | 34 de ani |
| **Oraș** | Locuiește într-un oraș mare |
| **Locuință** | Împreună cu soția, în chirie, apartament de 2 camere |
| **Chirie** | 330 euro / lună (nu include utilitățile) |
""")

    st.subheader("Situație profesională")
    st.markdown("""
Andrei lucrează de aproximativ 6 ani în aceeași companie, într-o firmă din zona de servicii / corporație
(de exemplu: suport tehnic, operațiuni, back-office, project coordinator junior).
Nu este la început de drum, dar nici într-o poziție foarte bine plătită.

| | |
|---|---|
| **Contract** | Perioadă nedeterminată |
| **Venit lunar net** | Aproximativ 1.150 euro |

Venitul este relativ stabil, dar:
- fără bonusuri garantate
- creșteri salariale mici și rare
- uneori apar întârzieri administrative

Andrei se percepe ca având un job „sigur".
""")

    st.subheader("Situație personală și emoțională")
    st.markdown("""
- **Status relațional:** căsătorit cu Maria. Maria are un venit net lunar în jur de 800 euro.
- Are un cerc restrâns de prieteni, mulți dintre ei deja căsătoriți, cu copii, cu rate la casă.

Andrei nu este impulsiv emoțional, dar:
- evită conflictele
- evită să spună „nu" în contexte sociale
- preferă soluții pe termen scurt care reduc stresul imediat
""")

    st.subheader("Stil de viață și hobby-uri")
    st.markdown("""
- Iese de 1–2 ori pe săptămână în oraș (mâncare, cafea).
- Merge ocazional la sală.
- Are mașină (nu foarte nouă), pe care o folosește zilnic.
- Îi place să plece din oraș de câteva ori pe an.
- Nu cheltuie extravagant, dar nici nu ține un buget strict.
- Cheltuielile „mici, dar dese" sunt o constantă.
""")

    st.subheader("Obiceiuri financiare")
    st.markdown("""
Andrei:
- nu ține un buget scris
- știe aproximativ cât câștigă, cât este chiria și cât este rata
- restul banilor sunt gestionați „din mers"

Are următoarele obiceiuri:
- plătește facturile la timp, de obicei
- evită restanțele, pentru că îl stresează
- când apare o problemă, taie mai întâi din economii
- abia la final reduce din cheltuieli
""")

    st.subheader("Economii")
    st.markdown("""
La începutul scenariului:
- are aproximativ **350 euro** economii
- ținute în cont curent, nu separat
- nu are un „fond de urgență" clar definit

Aceste economii:
- nu sunt rezultatul unei discipline
- sunt mai degrabă „ce a rămas" din ultimele luni mai bune
""")

    st.subheader("Creditul")
    st.markdown("""
| | |
|---|---|
| **Tip credit** | Credit de nevoi personale |
| **Valoare inițială** | Aproximativ 7.000 euro |
| **Durată** | 24 luni |
| **Rată lunară** | 317.71 euro |
| **Dobândă** | 8,35% |

De ce a luat creditul:
- mobilă și electrocasnice pentru apartament
- o parte din bani au mers pe mutare
- reparații minore
- câteva cheltuieli „de confort"

Creditul nu a fost luat într-o criză, ci:
- într-o perioadă relativ stabilă
- cu convingerea că „mă descurc fără probleme"
""")

    st.subheader("Cum se raportează Andrei la credit")
    st.markdown("""
Nu vede creditul ca pe un pericol. Îl vede ca pe „o obligație fixă". Nu se gândește la ce se întâmplă dacă:
- venitul întârzie
- apar 2–3 luni proaste la rând

Are mentalitatea: **„Dacă apare ceva, rezolv atunci."**

Creditul îl plătește Andrei, dar cheltuielile lunare sunt suportate împreună.
""")

    st.subheader("Overdraft")
    st.markdown("""
| | |
|---|---|
| **Tip instrument** | Linie de credit de tip overdraft atașată contului curent |
| **Limită maximă** | Aproximativ 3.000 euro |

**Rolul overdraftului:** funcționează ca o rezervă de lichiditate care poate fi utilizată atunci când cheltuielile
lunare depășesc suma disponibilă în cont.

**Mod de utilizare:** dacă totalul cheltuielilor lunare și al sumei introduse pentru plata creditului depășește
lichiditatea disponibilă, diferența este acoperită automat din overdraft, în limita disponibilă.
Participanții nu activează manual overdraftul, dar decizia lor de plată poate conduce la utilizarea lui.

**Dobândă overdraft:** sumele utilizate generează dobândă lunară, care se adaugă la datoria acumulată.

**Rambursarea overdraftului:** orice sumă rămasă în cont după efectuarea plăților lunare reduce automat
soldul overdraftului utilizat.
""")

    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Începe scenariul →", type="primary"):
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
        st.title(f"Luna {month}")
    with col_score:
        st.metric("Scor acumulat", display_number(st.session_state.total_score))

    with st.expander("Context narativ", expanded=True):
        narrative = re.sub(r'^(\S+)', r'<strong>\1</strong>', get_narrative(month))
        st.markdown(
            f'<div style="text-align: justify">{narrative}</div>',
            unsafe_allow_html=True,
        )
    auto_open_context_narrativ(month)

    with st.expander("Buget lunar"):
        st.markdown("**Venituri**")
        st.table(display_value_table(data["income"]))
        st.write(f"**Total venituri:** {display_number(income_total)}")

        st.markdown("**Cheltuieli curente**")
        st.table(display_value_table(data["expenses"]))
        st.write(f"**Total cheltuieli:** {display_number(expenses_total)}")

    opening_balance_html = (
        f'<div class="decision-row positive"><strong>Sold inițial disponibil:</strong> {display_euro(opening_balance)}</div>'
        if month == 1
        else ""
    )

    st.markdown(
        f"""
<div class="decision-card">
<div class="decision-card-title">Decizie privind plata creditului</div>
{opening_balance_html}
<div class="decision-row positive"><strong>Venituri totale:</strong> {display_euro(income_total)}</div>
<div class="decision-row risk"><strong>Cheltuieli curente:</strong> {display_euro(expenses_total)}</div>
<div class="decision-row risk"><strong>Dobândă overdraft:</strong> {display_euro(overdraft_interest)} | <strong>Dobândă credit:</strong> {display_euro(credit_interest)}</div>
<div class="decision-row risk"><strong>Sold credit rămas:</strong> {display_euro(loan.balance)} | <strong>Overdraft utilizat:</strong> {display_euro(overdraft.balance)}</div>
<div class="decision-row positive"><strong>Bani disponibili înainte de plata creditului:</strong> {display_euro(liquidity_after_charges)}</div>
<div class="decision-row formula"><strong>Bani disponibili înainte de plata creditului</strong> = sold inițial disponibil + venituri totale - cheltuieli curente - dobândă credit - dobândă overdraft</div>
<div class="decision-row primary"><strong>Rata lunară prevăzută în contract:</strong> {display_euro(loan_obligation)}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    if blocked:
        st.error(
            "Cheltuielile lunii depășesc lichiditatea disponibilă și limita de overdraft. "
            "Plata creditului nu poate fi executată. Pentru această lună, scorul este 0."
        )

    st.markdown('<div class="payment-label">Sumă de rambursat din credit (€)</div>', unsafe_allow_html=True)
    payment = st.number_input(
        "Sumă de rambursat din credit (€)",
        min_value=0.0,
        step=1.0,
        value=None,
        format="%g",
        placeholder="Introduceți o sumă numerică mai mare sau egală cu 0.",
        key=f"payment_{month}",
        label_visibility="collapsed",
    )
    attach_payment_keyboard_bridge()
    st.markdown(
        """
<div class="auth-info payment-note">
  <span class="auth-info-icon">i</span>
  <span>După confirmare, decizia nu mai poate fi modificată.</span>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="payment-button-gap"></div>', unsafe_allow_html=True)

    if st.button("Confirmă decizia", type="primary"):
        if payment is None:
            st.warning("Vă rugăm să introduceți o sumă numerică validă, mai mare sau egală cu 0.")
            st.stop()

        result = compute_month_result(month, data, loan, overdraft, payment)
        st.session_state.pending_month_result = result
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
    st.title(f"Luna {month} - feedback")

    st.markdown("### Rezultatul deciziei")
    st.write(f"**Suma introdusă:** {display_euro(result['payment_input'])}")
    st.write(f"**Plata acceptată la credit:** {display_euro(result['accepted_payment'])}")
    st.write(
        f"**Sold disponibil după plata ratei = Sold inițial + Venituri − Cheltuieli curente − Dobândă overdraft − Rata − Dobânda credit:** {display_euro(result['cash_final'])}"
    )
    st.write(f"**Sold credit rămas:** {display_euro(result['credit_final'])}")
    st.write(f"**Overdraft utilizat final:** {display_euro(result['overdraft_final'])}")
    st.write(f"**Dobândă credit luna aceasta:** {display_euro(result['credit_interest'])}")
    st.write(f"**Dobândă overdraft luna aceasta:** {display_euro(result['overdraft_interest'])}")
    if result["penalties"] > 0:
        st.write(f"**Penalități luna aceasta:** {display_euro(result['penalties'])}")
    st.markdown("### Scorul lunii")
    st.write(f"**Scor rambursare:** {display_number(result['score_repayment'])} / 40")
    st.write(f"**Scor lichiditate:** {display_number(result['score_liquidity'])} / 30")
    st.write(f"**Scor overdraft:** {display_number(result['score_overdraft'])} / 30")
    st.metric("Scor lunar", f"{display_number(result['monthly_score'])} / 100")
    st.metric("Scor acumulat", display_number(st.session_state.total_score + result["monthly_score"]))

    if result["pre_credit_impossible"]:
        st.error(result["feedback_message"])
    elif result["payment_valid"]:
        st.success(result["feedback_message"])
    else:
        st.warning(result["feedback_message"])

    if st.button("Continuă către luna următoare", type="primary"):
        st.session_state.loan.balance = result["credit_final"]
        st.session_state.overdraft.balance = result["overdraft_final"]
        st.session_state.total_score += result["monthly_score"]
        st.session_state.monthly_points += result["monthly_score"]
        st.session_state.accumulated_costs += result["costs_this_month"]
        st.session_state.monthly_results.append(result)
        st.session_state.pending_month_result = None
        st.session_state.month += 1
        goto("simulation")


# ==================== POST-SIMULATION QUESTIONS ====================
elif st.session_state.page.startswith("post_question_"):
    scroll_top_anchor()
    try:
        post_index = int(st.session_state.page.rsplit("_", 1)[1])
    except Exception:
        goto("post_question_0")

    if post_index >= len(POST_SECTIONS):
        goto("final_score")

    section = POST_SECTIONS[post_index]
    next_page = "final_score" if post_index + 1 >= len(POST_SECTIONS) else f"post_question_{post_index + 1}"
    question_offset = sum(len(post_section["questions"]) for post_section in POST_SECTIONS[:post_index])

    st.title("Chestionar post-experiment")
    st.caption(f"Capitolul {post_index + 1} din {len(POST_SECTIONS)}")
    st.progress((post_index + 1) / len(POST_SECTIONS))
    render_question_section(section, post_index + 1, question_offset)

    if not all_answered([section]):
        st.warning("Te rugăm să răspunzi la toate întrebările din acest capitol înainte de a continua.")

    if post_index + 1 >= len(POST_SECTIONS):
        st.markdown("### Feedback opțional")
        st.session_state.answers["feedback"] = st.text_area(
            "Ce parte a scenariului ți s-a părut cea mai provocatoare sau realistă?",
            value=st.session_state.answers.get("feedback", ""),
        )

    if st.button("Skip all chapters", type="secondary", key=f"skip_post_question_{post_index}"):
        st.session_state.scroll_to_top = True
        goto("final_score")

    if DEV:
        if st.button("⚡ DEV: Randomizează acest capitol și continuă", type="secondary", key=f"dev_post_question_{post_index}"):
            randomize_section(section)
            st.session_state.scroll_to_top = True
            goto(next_page)

    button_label = "Finalizează →" if post_index + 1 >= len(POST_SECTIONS) else "Continuă →"
    if st.button(button_label, type="primary", key=f"continue_post_question_{post_index}"):
        if all_answered([section]):
            st.session_state.scroll_to_top = True
            goto(next_page)
        else:
            st.error("Sunt întrebări fără răspuns.")


# ==================== FINAL SCORE ====================
elif st.session_state.page == "final_score":
    scroll_top_anchor()

    st.session_state.final_score = compute_final_score()

    breakdown = get_final_score_breakdown()

    st.title("Scor final")
    st.markdown("Ai finalizat cele 24 de luni ale scenariului.")
    st.markdown("### Scor comportamental final")
    st.markdown(
        f"""
**Scor comportamental final:** {display_number(breakdown["final_score"])} / 100

**Bonus final obținut:** {display_euro(breakdown["bonus_final"])} / {display_euro(breakdown["bonus_max_session"])}

### Rezumat financiar final

**Total rambursat din credit:** {display_euro(breakdown["total_repaid"])}

**Credit rămas la final:** {display_euro(breakdown["remaining_credit"])}

**Overdraft utilizat la final:** {display_euro(breakdown["remaining_overdraft"])}

**Dobânzi totale acumulate:** {display_euro(breakdown["interest_total"])}
"""
    )
    st.info(
        "Scorul comportamental final a fost calculat automat pe baza deciziilor lunare privind "
        "rambursarea creditului, lichiditatea rămasă după plată și utilizarea overdraftului."
    )
    st.caption("Datele generate în scenariu vor fi folosite doar în scopul cercetării, conform acordului de participare.")

    if st.button("Continuă →", type="primary"):
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
            )
            st.session_state.saved = True
        except Exception as e:
            st.error(f"Eroare la salvarea datelor: {e}")

    st.title("Mulțumim pentru participare!")
    st.metric("Scor comportamental final", f"{display_number(st.session_state.final_score)} / 100")
    st.markdown(f"**Bonus final obținut:** {display_euro(breakdown['bonus_final'])}")
    st.markdown(
        f"""
Credit rămas: **{display_euro(st.session_state.loan.balance)}**

Overdraft utilizat: **{display_euro(st.session_state.overdraft.balance)}**

Răspunsurile tale au fost înregistrate. Rezultatele studiului vor fi disponibile după finalizarea colectării datelor.

Contact: coita.iflorina@gmail.com
"""
    )

    if REPEAT_SCENARIO_DEV_MODE:
        st.caption("Mod de testare activ: poți parcurge din nou scenariul cu același cont.")
        if st.button("Începe un scenariu nou (test)", type="primary", key="new_test_scenario"):
            start_new_scenario()
            st.rerun()

persist_checkpoint()

