import re
import random
import importlib
import uuid
import base64
import json
import zlib
import streamlit as st
import pandas as pd

from loan import Loan
from overdraft import Overdraft
from narratives import get_narrative
from tables import get_month
from questions import PRE_SECTIONS, POST_SECTIONS
import db as db_module

db_module = importlib.reload(db_module)
load_session_checkpoint = getattr(db_module, "load_session_checkpoint", lambda *_args, **_kwargs: None)
save_participant = getattr(db_module, "save_participant")
save_session_checkpoint = getattr(db_module, "save_session_checkpoint", lambda *_args, **_kwargs: None)

DEV = True

st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
[data-testid="stToolbar"] {display: none !important;}
[data-testid="stDecoration"] {display: none !important;}
[data-testid="stStatusWidget"] {display: none !important;}
[data-testid="stAppDeployButton"] {display: none !important;}
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


def get_query_param(name):
    try:
        value = st.query_params.get(name)
        if isinstance(value, list):
            return value[0] if value else None
        return value
    except Exception:
        params = st.experimental_get_query_params()
        value = params.get(name)
        if isinstance(value, list):
            return value[0] if value else None
        return value


def set_query_param(name, value):
    try:
        st.query_params[name] = value
    except Exception:
        st.experimental_set_query_params(**{name: value})

    script = f"""
<script>
(function() {{
  try {{
    var url = new URL(window.parent.location.href);
    url.searchParams.set({json.dumps(str(name))}, {json.dumps(str(value))});
    window.parent.history.replaceState({{}}, "", url.toString());
  }} catch (e) {{}}
}})();
</script>
"""
    st.components.v1.html(script, height=0)


def encode_checkpoint_to_query_param(checkpoint):
    try:
        payload = json.dumps(checkpoint, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        compressed = zlib.compress(payload, level=9)
        return base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
    except Exception:
        return None


def decode_checkpoint_from_query_param(token):
    if not token:
        return None

    try:
        padded = token + "=" * (-len(token) % 4)
        compressed = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = zlib.decompress(compressed)
        return json.loads(payload.decode("utf-8"))
    except Exception:
        return None


def runtime_defaults():
    return {
        "page": "home",
        "session_id": None,
        "month": 1,
        "loan": Loan(balance=7000.0, annual_interest=0.0835, months=24),
        "overdraft": Overdraft(limit=3000.0, annual_interest=0.24),
        "savings": None,
        "total_score": 0,
        "monthly_points": 0.0,
        "accumulated_costs": 0.0,
        "monthly_results": [],
        "pending_month_result": None,
        "final_score": None,
        "answers": {},
        "scroll_to_top": False,
    }


def collect_checkpoint():
    payment_values = {
        key: value
        for key, value in st.session_state.items()
        if key.startswith("payment_")
    }

    return {
        "page": st.session_state.get("page", "home"),
        "month": st.session_state.get("month", 1),
        "loan_balance": st.session_state.loan.balance,
        "overdraft_balance": st.session_state.overdraft.balance,
        "savings": st.session_state.get("savings"),
        "total_score": st.session_state.get("total_score", 0),
        "monthly_points": st.session_state.get("monthly_points", 0.0),
        "accumulated_costs": st.session_state.get("accumulated_costs", 0.0),
        "monthly_results": st.session_state.get("monthly_results", []),
        "pending_month_result": st.session_state.get("pending_month_result"),
        "final_score": st.session_state.get("final_score"),
        "answers": st.session_state.get("answers", {}),
        "payment_values": payment_values,
    }


def persist_checkpoint(status=None):
    session_id = st.session_state.get("session_id")
    if not session_id:
        return False

    checkpoint = collect_checkpoint()
    resolved_status = status or ("completed" if checkpoint.get("page") == "done" else "in_progress")
    token = encode_checkpoint_to_query_param(checkpoint)

    if token and get_query_param("cp") != token:
        set_query_param("cp", token)

    try:
        save_session_checkpoint(session_id, checkpoint, status=resolved_status)
        return True
    except Exception as e:
        st.session_state.checkpoint_save_error = str(e)
        return False


def hydrate_from_checkpoint(checkpoint):
    defaults = runtime_defaults()
    for key, value in defaults.items():
        if key not in ("loan", "overdraft"):
            st.session_state[key] = value

    page = checkpoint.get("page", "home")
    if page == "pre_questions":
        page = "pre_question_0"
    elif page == "post_questions":
        page = "post_question_0"
    elif page == "month_feedback" and not checkpoint.get("pending_month_result"):
        page = "simulation"

    st.session_state.page = page
    st.session_state.month = int(checkpoint.get("month", 1))
    st.session_state.session_id = st.session_state.get("session_id")
    st.session_state.loan = Loan(
        balance=float(checkpoint.get("loan_balance", 7000.0)),
        annual_interest=0.0835,
        months=24,
    )
    st.session_state.overdraft = Overdraft(
        limit=3000.0,
        annual_interest=0.24,
    )
    st.session_state.overdraft.balance = round(float(checkpoint.get("overdraft_balance", 0.0)), 2)
    st.session_state.savings = checkpoint.get("savings")
    st.session_state.total_score = checkpoint.get("total_score", 0)
    st.session_state.monthly_points = checkpoint.get("monthly_points", 0.0)
    st.session_state.accumulated_costs = checkpoint.get("accumulated_costs", 0.0)
    st.session_state.monthly_results = checkpoint.get("monthly_results", [])
    st.session_state.pending_month_result = checkpoint.get("pending_month_result")
    st.session_state.final_score = checkpoint.get("final_score")
    st.session_state.answers = checkpoint.get("answers", {})

    for key, value in (checkpoint.get("payment_values") or {}).items():
        st.session_state[key] = value


def bootstrap_anonymous_session():
    session_id = get_query_param("sid")
    if not session_id:
        session_id = str(uuid.uuid4())
        set_query_param("sid", session_id)

    st.session_state.session_id = session_id

    checkpoint = decode_checkpoint_from_query_param(get_query_param("cp"))
    if not checkpoint:
        checkpoint = load_session_checkpoint(session_id)
    if checkpoint:
        hydrate_from_checkpoint(checkpoint)
    else:
        defaults = runtime_defaults()
        for key, value in defaults.items():
            if key not in ("loan", "overdraft"):
                st.session_state[key] = value
        st.session_state.loan = defaults["loan"]
        st.session_state.overdraft = defaults["overdraft"]
        persist_checkpoint()


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
      'input[aria-label="Sumă de rambursat din credit (€)"]',
      'input[aria-label^="Sumă de rambursat din credit"]',
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

# -------------------------
# INIT STATE
# -------------------------
if not st.session_state.get("_bootstrap_done"):
    bootstrap_anonymous_session()
    st.session_state._bootstrap_done = True


def render_question_section(section):
    st.markdown(f"### {section['title']}")
    st.caption(section["instruction"])
    for i, q in enumerate(section["questions"]):
        key = f"{section['key_prefix']}_{i}"
        current = st.session_state.answers.get(key)
        idx = section["scale"].index(current) if current in section["scale"] else None
        st.session_state.answers[key] = st.radio(
            q,
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


def render_quiz_chapter(section, chapter_index, total_chapters, next_page, dev_label, title, skip_page=None):
    st.title(title)
    st.caption(f"Capitolul {chapter_index + 1} din {total_chapters}")
    st.markdown("Răspunde la capitolul curent, apoi apasă **Continuă** pentru a trece mai departe.")
    st.progress((chapter_index + 1) / total_chapters)
    render_question_section(section)

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


# ==================== HOME ====================
if st.session_state.page == "home":
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

    if st.button("Începe simularea →", type="primary"):
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
        "Chestionar – înainte de simulare",
        skip_page="instructions",
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

În această simulare vei lua rolul lui Andrei, o persoană care are un credit de nevoi personale și trebuie să ia decizii lunare de rambursare.

Simularea durează 24 de luni.

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

Creditul este obligația de bază a simulării. Overdraftul este o sursă suplimentară de finanțare care poate ajuta temporar, dar care indică fragilitate financiară. De aceea, participanții sunt penalizați mai puternic dacă acumulează overdraft sau dacă încheie simularea cu overdraft nerambursat.

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

În această simulare, limita maximă de overdraft este: **3.000 euro**

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
- simularea continuă cu luna următoare.

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

Apoi, scorul final este ajustat în funcție de situația financiară rămasă la finalul simulării.

Se ține cont de:

- creditul rămas;
- overdraftul rămas;
- dobânzile și penalitățile acumulate.

Cu cât rămân datorii mai mari la final, cu atât scorul final poate scădea.

Overdraftul rămas scade scorul mai mult, deoarece arată că s-au folosit bani împrumutați suplimentar.

Creditul ramas, dobânzile și penalitățile scad și ele scorul, deoarece sunt costuri acumulate pe parcursul jocului.

### 🖥️ Regula generală a simulării

Scopul nu este să plătești mereu aceeași sumă.

Scopul este să iei o decizie lunară care poate fi susținută de situația financiară a lunii respective.

În unele luni poate fi ușor să plătești rata recomandată. În alte luni, din cauza cheltuielilor și veniturilor, decizia poate fi mai dificilă.

Trebuie să alegi suma pe care o consideri potrivită, ținând cont de:

- venituri;
- cheltuieli;
- credit;
- overdraft;
- riscul de a introduce o plată imposibilă.

### Mesaj important înainte de începerea simulării

Te rugăm să citești cu atenție informațiile fiecărei luni înainte de a introduce suma de rambursat.

După ce apeși „Confirmă decizia”, suma introdusă nu mai poate fi modificată.

Dacă suma introdusă depășește resursele disponibile și limita de overdraft, plata nu va fi executată, iar scorul lunii va fi 0.

Simularea continuă până la finalul celor 24 de luni.
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
    st.markdown("Înainte de a începe simularea, citește cu atenție profilul personajului pe care îl vei reprezenta.")

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
La începutul simulării:
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

    if st.button("Începe simularea →", type="primary"):
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
        st.table(pd.DataFrame(list(data["income"].items()), columns=["Categoria", "Valoare (€)"]))
        st.write(f"**Total venituri:** {income_total:.2f}")

        st.markdown("**Cheltuieli curente**")
        st.table(pd.DataFrame(list(data["expenses"].items()), columns=["Categoria", "Valoare (€)"]))
        st.write(f"**Total cheltuieli:** {expenses_total:.2f}")

        st.markdown("**Obligații lunare**")
        st.table(
            pd.DataFrame(
                list(obligations.items()),
                columns=["Categoria", "Valoare (€)"],
            )
        )

    opening_balance_html = (
        f'<div style="margin-bottom: 0.9rem; color: #8fd18f;"><strong>Sold inițial disponibil:</strong> {opening_balance:.2f} €</div>'
        if month == 1
        else ""
    )

    st.markdown(
        f"""
<div style="background-color: #1f3b5b; padding: 1rem 1.2rem; border-radius: 0.5rem; color: #d8e9ff; line-height: 1.6;">
  <div style="font-weight: 700; margin-bottom: 0.85rem;">Decizie privind plata creditului</div>
  {opening_balance_html}
  <div style="margin-bottom: 0.45rem; color: #8fd18f;"><strong>Venituri totale:</strong> {income_total:.2f} €</div>
  <div style="margin-bottom: 0.45rem; color: #ff9a9a;"><strong>Cheltuieli curente:</strong> {expenses_total:.2f} €</div>
  <div style="margin-bottom: 0.45rem; color: #ff9a9a;"><strong>Dobândă overdraft:</strong> {overdraft_interest:.2f} € | <strong>Dobândă credit:</strong> {credit_interest:.2f} €</div>
  <div style="margin-bottom: 0.45rem; color: #8fd18f;"><strong>Sold final înainte de plata ratei creditului:</strong> {liquidity_after_charges:.2f} €</div>
  <div style="margin-bottom: 0.45rem; color: #ff9a9a;"><strong>Sold credit rămas:</strong> {loan.balance:.2f} € | <strong>Overdraft utilizat:</strong> {overdraft.balance:.2f} €</div>
  <div style="color: #d8e9ff;"><strong>Plata orientativă a creditului în această lună:</strong> {loan_obligation:.2f} €</div>
</div>
""",
        unsafe_allow_html=True,
    )

    if blocked:
        st.error(
            "Cheltuielile lunii depășesc lichiditatea disponibilă și limita de overdraft. "
            "Plata creditului nu poate fi executată. Pentru această lună, scorul este 0."
        )

    payment = st.number_input(
        "Sumă de rambursat din credit (€)",
        min_value=0.0,
        step=1.0,
        value=None,
        placeholder="Introduceți o sumă numerică...",
        key=f"payment_{month}",
    )
    attach_payment_keyboard_bridge()
    st.caption("Introduceți o sumă numerică mai mare sau egală cu 0.")
    st.caption("După confirmare, decizia nu mai poate fi modificată.")

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
    st.write(f"**Suma introdusă:** {result['payment_input']:.2f} €")
    st.write(f"**Plata acceptată la credit:** {result['accepted_payment']:.2f} €")
    st.write(
        f"**Sold disponibil după plata ratei = Sold inițial + Venituri − Cheltuieli curente − Dobândă overdraft − Rata − Dobânda credit:** {result['cash_final']:.2f} €"
    )
    st.write(f"**Sold credit rămas:** {result['credit_final']:.2f} €")
    st.write(f"**Overdraft utilizat final:** {result['overdraft_final']:.2f} €")
    st.write(f"**Dobândă credit luna aceasta:** {result['credit_interest']:.2f} €")
    st.write(f"**Dobândă overdraft luna aceasta:** {result['overdraft_interest']:.2f} €")
    if result["penalties"] > 0:
        st.write(f"**Penalități luna aceasta:** {result['penalties']:.2f} €")
    st.metric("Puncte acumulate", st.session_state.total_score + result["monthly_score"])

    if result["pre_credit_impossible"]:
        st.error(result["feedback_message"])
    elif result["payment_valid"]:
        st.success(result["feedback_message"])
    else:
        st.warning(result["feedback_message"])

    st.caption("După confirmare, decizia nu mai poate fi modificată.")

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
    st.title("Chestionar – după simulare")
    st.caption("Capitolul 1 din 1")
    st.markdown("Indicați cât de mult sunteți de acord cu fiecare afirmație, în funcție de cum vă simțiți **acum**.")
    st.progress(1.0)
    render_question_section(section)

    if not all_answered([section]):
        st.warning("Te rugăm să răspunzi la toate întrebările înainte de a finaliza.")

    st.markdown("### Feedback opțional")
    st.session_state.answers["feedback"] = st.text_area(
        "Ce parte a simulării ți s-a părut cea mai provocatoare sau realistă?",
        value=st.session_state.answers.get("feedback", ""),
    )

    if st.button("Skip all chapters", type="secondary", key="skip_post_question"):
        st.session_state.scroll_to_top = True
        goto("done")

    if DEV:
        if st.button("⚡ DEV: Randomizează acest capitol și finalizează", type="secondary"):
            randomize_section(section)
            st.session_state.scroll_to_top = True
            goto("done")

    if st.button("Finalizează →", type="primary"):
        if all_answered([section]):
            st.session_state.scroll_to_top = True
            goto("done")
        else:
            st.error("Sunt întrebări fără răspuns.")


# ==================== DONE ====================
elif st.session_state.page == "done":
    scroll_top_anchor()
    if st.session_state.final_score is None:
        st.session_state.final_score = compute_final_score()

    if not st.session_state.get("saved"):
        try:
            save_participant(
                st.session_state.session_id,
                st.session_state.answers,
                st.session_state.final_score,
            )
            st.session_state.saved = True
        except Exception as e:
            st.error(f"Eroare la salvarea datelor: {e}")

    st.title("Mulțumim pentru participare!")
    st.metric("Scor final simulare", f"{st.session_state.final_score:.2f}")
    st.markdown(
        f"Ai acumulat {st.session_state.final_score:.2f} puncte din 24. Valoare câștigată: {st.session_state.final_score:.2f} euro."
    )
    st.markdown(
        f"""
Puncte lunare brute: **{st.session_state.total_score:.2f}**

Credit rămas: **{st.session_state.loan.balance:.2f} €**

Overdraft utilizat: **{st.session_state.overdraft.balance:.2f} €**

Răspunsurile tale au fost înregistrate. Rezultatele studiului vor fi disponibile după finalizarea colectării datelor.

Contact: coita.iflorina@gmail.com
"""
    )

persist_checkpoint()

