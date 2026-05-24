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


def compute_month_result(month, data, loan, overdraft, payment):
    income_total = month_sum(data["income"])
    expenses_total = month_sum(data["expenses"])
    obligations = data.get("obligations", {})
    loan_obligation = money(loan.get_required_payment())
    credit_interest = money(loan.apply_interest())
    overdraft_interest = money(obligations.get("overdraft_interest", 0))
    penalties = money(obligations.get("penalties", 0))
    opening_balance = money(data["position"]["initial"])

    available_total = money(opening_balance + income_total)
    outflows_before_credit = money(expenses_total + overdraft_interest + credit_interest + penalties)
    deficit_before_credit = money(max(0.0, outflows_before_credit - available_total))
    liquidity_after_charges = money(max(0.0, available_total - outflows_before_credit))
    overdraft_after_charges = money(overdraft.balance + deficit_before_credit)
    overdraft_remaining = money(max(0.0, overdraft.limit - min(overdraft_after_charges, overdraft.limit)))
    max_payment = money(liquidity_after_charges + overdraft_remaining)

    pre_credit_impossible = overdraft_after_charges > overdraft.limit
    payment_value = None if payment is None else money(payment)
    payment_valid = (
        not pre_credit_impossible
        and payment_value is not None
        and payment_value >= 0
        and payment_value <= max_payment
        and payment_value <= loan.balance
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
        monthly_score = 0
        invalid_reason = "pre_credit"
    elif payment_valid:
        accepted_payment = payment_value
        overdraft_from_payment = money(max(0.0, accepted_payment - liquidity_after_charges))
        overdraft_final = money(overdraft_after_charges + overdraft_from_payment)
        cash_final = money(max(0.0, liquidity_after_charges - accepted_payment))
        credit_final = money(max(0.0, loan.balance - accepted_payment))
        monthly_score = 1
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
        monthly_score = 0
        feedback_message = (
            "Suma introdusă depășește lichiditatea disponibilă și limita de overdraft rămasă. "
            "Plata nu a fost executată. Pentru această lună, scorul este 0."
        )
        invalid_reason = "payment"

    if overdraft_final > overdraft.limit:
        overdraft_final = money(overdraft.limit)
        cash_final = 0.0
        if monthly_score == 1:
            monthly_score = 0
            accepted_payment = 0.0
            credit_final = money(loan.balance)
            overdraft_from_payment = 0.0
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
        "monthly_score": monthly_score,
        "costs_this_month": money(credit_interest + overdraft_interest + penalties),
        "feedback_message": feedback_message,
        "invalid_reason": invalid_reason,
        "pre_credit_impossible": pre_credit_impossible,
        "payment_valid": payment_valid,
    }


def compute_final_score():
    monthly_points = money(st.session_state.get("monthly_points", 0.0))
    remaining_credit = money(st.session_state.loan.balance)
    remaining_overdraft = money(st.session_state.overdraft.balance)
    accumulated_costs = money(st.session_state.get("accumulated_costs", 0.0))

    raw = monthly_points - (remaining_credit / 1000.0) - (remaining_overdraft / 100.0) - (accumulated_costs / 50.0)
    return money(max(0.0, min(24.0, raw)))


def get_final_score_breakdown():
    monthly_points = money(st.session_state.get("monthly_points", 0.0))
    remaining_credit = money(st.session_state.loan.balance)
    remaining_overdraft = money(st.session_state.overdraft.balance)
    accumulated_costs = money(st.session_state.get("accumulated_costs", 0.0))
    raw_score = monthly_points - (remaining_credit / 1000.0) - (remaining_overdraft / 100.0) - (accumulated_costs / 50.0)
    final_score = money(max(0.0, min(24.0, raw_score)))
    return {
        "monthly_points": monthly_points,
        "remaining_credit": remaining_credit,
        "remaining_overdraft": remaining_overdraft,
        "accumulated_costs": accumulated_costs,
        "raw_score": money(raw_score),
        "final_score": final_score,
    }


# ==================== COMPLETED ACCOUNT ====================
if st.session_state.page == "already_completed":
    scroll_top_anchor()
    st.title("Participare deja finalizată")
    st.info("Acest cont a finalizat deja scenariul. Nu poate fi trimis un al doilea răspuns.")
    if REPEAT_SCENARIO_DEV_MODE and st.button("Începe un scenariu nou (test)", type="primary"):
        start_new_scenario()
        st.rerun()
    if st.button("Ieși din cont", key="completed_logout"):
        st.logout()


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
        goto("pre_question_0")


# ==================== PRE-SIMULATION QUESTIONS ====================
elif st.session_state.page == "pre_questions":
    goto("pre_question_0")

elif st.session_state.page.startswith("pre_question_"):
    scroll_top_anchor()
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
.participant-instructions { text-align: justify; }
</style>
""", unsafe_allow_html=True)

    st.title("Instrucțiuni pentru participant")

    st.markdown(
        '<div class="participant-instructions">',
        unsafe_allow_html=True,
    )
    st.info(
        """
**Instrucțiuni pentru participant**

În acest scenariu vei lua rolul lui Andrei, o persoană care are un credit de nevoi personale și trebuie să ia decizii lunare de rambursare.

Scenariul durează 24 de luni.

În fiecare lună vei vedea:

- veniturile lunii;
- cheltuielile lunii;
- suma disponibilă înainte de plata creditului;
- soldul creditului;
- soldul overdraftului;
- dobânzile sau penalitățile, dacă există.

După ce citești informațiile lunii, trebuie să introduci suma pe care dorești să o rambursezi din credit în acea lună.

Tu decizi doar suma plătită la credit.

Nu trebuie să rambursezi separat overdraftul.

Creditul este obligația de bază a scenariului. Overdraftul este o sursă suplimentară de finanțare care poate ajuta temporar, dar care indică fragilitate financiară. De aceea, participanții sunt penalizați mai puternic dacă acumulează overdraft sau dacă încheie scenariul cu overdraft nerambursat.

### 📊 Cum funcționează decizia lunară

În fiecare lună, vei introduce o singură sumă:

- suma pe care vrei să o plătești din credit

Apoi apeși:

- **Confirmă decizia**

După confirmare, decizia nu mai poate fi modificată.

Platforma va calcula automat:

- dacă plata poate fi realizată;
- cât scade soldul creditului;
- dacă se folosește overdraftul;
- care este soldul final al lunii;
- ce scor primești pentru luna respectivă.

După confirmare, vei vedea un ecran de feedback pentru luna curentă. Acolo vei vedea rezultatul deciziei tale. Apoi vei apăsa:

- **Continuă către luna următoare**

Overdraftul este o linie de credit atașată contului curent.

În acest scenariu, limita maximă de overdraft este: **3.000 euro**

Overdraftul funcționează ca o rezervă de bani împrumutați.

Dacă banii disponibili nu ajung pentru cheltuielile lunii și pentru plata introdusă de tine, platforma va folosi overdraftul, în limita disponibilă.

### 😃 Ce se întâmplă dacă introduci o sumă posibilă

Dacă suma introdusă poate fi acoperită din banii disponibili și din overdraftul rămas, plata este acceptată.

În acest caz:

- plata se înregistrează;
- soldul creditului scade;
- soldurile lunii se actualizează;
- primești scorul lunii.

### 🤔 Ce se întâmplă dacă introduci o sumă imposibilă

Dacă introduci o sumă mai mare decât banii disponibili plus overdraftul rămas, plata nu poate fi realizată.

În acest caz:

- plata este respinsă;
- creditul nu scade;
- nu se depășește limita de overdraft;
- scorul lunii este 0;
- scenariul continuă cu luna următoare.

După ce ai confirmat o sumă imposibilă, nu vei putea reveni pentru a o corecta. De aceea, trebuie să verifici atent informațiile înainte de confirmare.

### 👍 Ce poți corecta înainte de confirmare

Înainte să apeși „Confirmă decizia”, poți corecta suma introdusă.

Dacă introduci din greșeală litere, semne sau o valoare negativă, platforma îți va cere să introduci o valoare numerică validă.

### 🏆 Cum se acordă scorul lunar

În fiecare lună poți primi:

- 1 punct sau 0 puncte

Primești 1 punct dacă suma introdusă este posibilă și plata poate fi executată.

Primești 0 puncte dacă suma introdusă este imposibilă.

Pe scurt:

- Plată posibilă = 1 punct
- Plată imposibilă = 0 puncte

Scorul lunar nu înseamnă că ai ales perfect. El arată doar dacă decizia ta a putut fi executată în condițiile financiare ale lunii respective.

### 🪙 Cum se calculează scorul final

La finalul celor 24 de luni, se adună punctele obținute în fiecare lună.

Scorul maxim lunar total este: **24 puncte**

Apoi, scorul final este ajustat în funcție de situația financiară rămasă la finalul scenariului.

Se ține cont de:

- creditul rămas;
- overdraftul rămas;
- dobânzile și penalitățile acumulate.

Cu cât rămân datorii mai mari la final, cu atât scorul final poate scădea.

Overdraftul rămas scade scorul mai mult, deoarece arată că s-au folosit bani împrumutați suplimentar.

Creditul ramas, dobânzile și penalitățile scad și ele scorul, deoarece sunt costuri acumulate pe parcursul jocului.

### 🖥️ Regula generală a scenariului

Scopul nu este să plătești mereu aceeași sumă.

Scopul este să iei o decizie lunară care poate fi susținută de situația financiară a lunii respective.

În unele luni poate fi ușor să plătești rata recomandată. În alte luni, din cauza cheltuielilor și veniturilor, decizia poate fi mai dificilă.

Trebuie să alegi suma pe care o consideri potrivită, ținând cont de:

- venituri;
- cheltuieli;
- credit;
- overdraft;
- riscul de a introduce o plată imposibilă.

### Mesaj important înainte de începerea scenariului

Te rugăm să citești cu atenție informațiile fiecărei luni înainte de a introduce suma de rambursat.

După ce apeși „Confirmă decizia”, suma introdusă nu mai poate fi modificată.

Dacă suma introdusă depășește resursele disponibile și limita de overdraft, plata nu va fi executată, iar scorul lunii va fi 0.

Scenariul continuă până la finalul celor 24 de luni.
"""
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
    opening_balance = money(data["position"]["initial"])
    loan_obligation = money(loan.get_required_payment())
    credit_interest = money(loan.apply_interest())
    overdraft_interest = money(obligations.get("overdraft_interest", 0))
    penalties = money(obligations.get("penalties", 0))
    available_total = money(opening_balance + income_total)
    outflows_before_credit = money(expenses_total + overdraft_interest + penalties)
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
        st.metric("Puncte acumulate", st.session_state.total_score)

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

        st.markdown("**Obligații lunare**")
        st.table(display_value_table(obligations))

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
<div class="decision-row positive"><strong>Sold final înainte de plata ratei creditului:</strong> {display_euro(liquidity_after_charges)}</div>
<div class="decision-row risk"><strong>Sold credit rămas:</strong> {display_euro(loan.balance)} | <strong>Overdraft utilizat:</strong> {display_euro(overdraft.balance)}</div>
<div class="decision-row primary"><strong>Plata orientativă a creditului în această lună:</strong> {display_euro(loan_obligation)}</div>
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
    st.metric("Puncte acumulate", st.session_state.total_score + result["monthly_score"])

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
    post_index = 0
    section = POST_SECTIONS[post_index]
    st.title("Chestionar – după scenariu")
    st.caption("Capitolul 1 din 1")
    st.markdown("Indicați cât de mult sunteți de acord cu fiecare afirmație, în funcție de cum vă simțiți **acum**.")
    st.progress(1.0)
    render_question_section(section, post_index + 1)

    if not all_answered([section]):
        st.warning("Te rugăm să răspunzi la toate întrebările înainte de a finaliza.")

    st.markdown("### Feedback opțional")
    st.session_state.answers["feedback"] = st.text_area(
        "Ce parte a scenariului ți s-a părut cea mai provocatoare sau realistă?",
        value=st.session_state.answers.get("feedback", ""),
    )

    if st.button("Skip all chapters", type="secondary", key="skip_post_question"):
        st.session_state.scroll_to_top = True
        goto("final_score")

    if DEV:
        if st.button("⚡ DEV: Randomizează acest capitol și finalizează", type="secondary"):
            randomize_section(section)
            st.session_state.scroll_to_top = True
            goto("final_score")

    if st.button("Finalizează →", type="primary"):
        if all_answered([section]):
            st.session_state.scroll_to_top = True
            goto("final_score")
        else:
            st.error("Sunt întrebări fără răspuns.")


# ==================== FINAL SCORE ====================
elif st.session_state.page == "final_score":
    scroll_top_anchor()

    if st.session_state.final_score is None:
        st.session_state.final_score = compute_final_score()

    breakdown = get_final_score_breakdown()

    st.title("Scor final")
    st.markdown("### Formula de calcul")
    st.markdown(
        f"""
**Puncte lunare brute:** {display_number(breakdown["monthly_points"])}

**Credit rămas:** {display_euro(breakdown["remaining_credit"])}  → penalizare: -{display_number(breakdown["remaining_credit"] / 1000.0)}

**Overdraft utilizat:** {display_euro(breakdown["remaining_overdraft"])}  → penalizare: -{display_number(breakdown["remaining_overdraft"] / 100.0)}

**Costuri acumulate:** {display_euro(breakdown["accumulated_costs"])}  → penalizare: -{display_number(breakdown["accumulated_costs"] / 50.0)}

**Scor brut după formulă:** {display_number(breakdown["raw_score"])}

**Scor final ajustat:** **{display_number(breakdown["final_score"])} / 24**
"""
    )
    st.metric("Scor final", f"{display_number(breakdown['final_score'])} / 24")
    st.info("Acesta este scorul tău după aplicarea formulei finale de ajustare.")

    if st.button("Continuă →", type="primary"):
        st.session_state.scroll_to_top = True
        goto("done")


# ==================== DONE ====================
elif st.session_state.page == "done":
    scroll_top_anchor()
    if st.session_state.final_score is None:
        st.session_state.final_score = compute_final_score()

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
    st.metric("Scor final scenariu", display_number(st.session_state.final_score))
    st.markdown(
        f"Ai acumulat {display_number(st.session_state.final_score)} puncte din 24. Valoare câștigată: {display_number(st.session_state.final_score)} euro."
    )
    st.markdown(
        f"""
Puncte lunare brute: **{display_number(st.session_state.total_score)}**

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

