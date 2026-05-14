import re
import random
import uuid
import streamlit as st
import pandas as pd

from loan import Loan
from overdraft import Overdraft
from narratives import get_narrative
from tables import get_month
from questions import PRE_SECTIONS, POST_SECTIONS
from db import save_participant

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


def goto(page):
    st.session_state.page = page
    st.session_state.scroll_to_top = True
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
  [0, 50, 150, 300, 600, 1000, 1500, 2500].forEach(function(t){{ setTimeout(tryScroll, t); }});
  try {{
    var obs = new MutationObserver(tryScroll);
    obs.observe(window.parent.document.body, {{childList: true, subtree: true}});
    setTimeout(function() {{ obs.disconnect(); }}, 2500);
  }} catch(e) {{}}
}})();
</script>
""", height=0)
        st.session_state.scroll_to_top = False


def randomize_sections(sections):
    for section in sections:
        for i in range(len(section["questions"])):
            key = f"{section['key_prefix']}_{i}"
            st.session_state.answers[key] = random.choice(section["scale"])

# -------------------------
# INIT STATE
# -------------------------
if "page" not in st.session_state:
    st.session_state.page = "home"
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.month = 1
    st.session_state.loan = Loan(balance=7000.0, annual_interest=0.0835, months=24)
    st.session_state.overdraft = Overdraft(limit=1000.0, annual_interest=0.24)
    st.session_state.savings = None
    st.session_state.total_score = 0
    st.session_state.monthly_points = 0.0
    st.session_state.accumulated_costs = 0.0
    st.session_state.monthly_results = []
    st.session_state.pending_month_result = None
    st.session_state.final_score = None
    st.session_state.framing_mode = random.choice(["gain", "loss"])
    st.session_state.answers = {}


if DEV:
    with st.sidebar:
        st.subheader("Admin panel")
        framing_index = 0 if st.session_state.framing_mode == "gain" else 1
        framing_choice = st.radio(
            "Framing monetar",
            ["A. Gain frame", "B. Loss frame"],
            index=framing_index,
            key="admin_framing_mode",
        )
        st.session_state.framing_mode = "gain" if framing_choice.startswith("A.") else "loss"


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


def money(value):
    return round(float(value), 2)


def month_sum(values):
    return money(sum(values.values()))


def compute_month_result(month, data, loan, overdraft, payment):
    income_total = month_sum(data["income"])
    expenses_total = month_sum(data["expenses"])
    obligations = data.get("obligations", {})
    loan_obligation = money(loan.get_required_payment())
    overdraft_interest = money(obligations.get("overdraft_interest", 0))
    penalties = money(obligations.get("penalties", 0))
    opening_balance = money(data["position"]["initial"])

    available_total = money(opening_balance + income_total)
    outflows_before_credit = money(expenses_total + overdraft_interest + penalties)
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
        "costs_this_month": money(overdraft_interest + penalties),
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


def framing_summary(final_score):
    if st.session_state.get("framing_mode", "gain") == "loss":
        return f"Ai păstrat {final_score:.2f} puncte din 24. Valoare rămasă: {final_score:.2f} euro din 24 euro."
    return f"Ai acumulat {final_score:.2f} puncte din 24. Valoare câștigată: {final_score:.2f} euro."


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
        goto("pre_questions")


# ==================== PRE-SIMULATION QUESTIONS ====================
elif st.session_state.page == "pre_questions":
    scroll_top_anchor()
    st.title("Chestionar – înainte de simulare")
    st.markdown("Te rugăm să citești cu atenție fiecare afirmație și să indici răspunsul potrivit.")

    for section in PRE_SECTIONS:
        render_question_section(section)

    if DEV:
        if st.button("⚡ DEV: Randomizează și continuă", type="secondary"):
            randomize_sections(PRE_SECTIONS)
            goto("instructions")

    if not all_answered(PRE_SECTIONS):
        st.warning("Te rugăm să răspunzi la toate întrebările înainte de a continua.")
    if st.button("Continuă →", type="primary"):
        if all_answered(PRE_SECTIONS):
            goto("instructions")
        else:
            st.error("Sunt întrebări fără răspuns.")


# ==================== INSTRUCTIONS ====================
elif st.session_state.page == "instructions":
    scroll_top_anchor()
    st.title("Instrucțiuni pentru participant")
    st.markdown(
        "În această simulare vei lua rolul lui Andrei, o persoană care are un credit de nevoi personale "
        "și trebuie să ia decizii lunare de rambursare."
    )

    st.markdown(
        """
### Cum funcționează simularea
- Simularea durează **24 de luni**.
- În fiecare lună vei vedea veniturile, cheltuielile, soldul disponibil înainte de plata creditului, soldul creditului, soldul overdraftului și dobânzile sau penalitățile, dacă există.
- După ce citești informațiile lunii, introduci **o singură sumă** pe care dorești să o rambursezi din credit.
- Tu decizi doar suma plătită la credit. Nu trebuie să rambursezi separat overdraftul.
- După confirmare, decizia nu mai poate fi modificată.
- După feedback-ul lunii curente, vei apăsa **Continuă către luna următoare**.
"""
    )

    st.warning(
        "Introduceți o sumă numerică validă, mai mare sau egală cu 0. "
        "După confirmare, decizia nu mai poate fi modificată."
    )

    st.markdown(
        """
### Overdraft
- Overdraftul este o linie de credit atașată contului curent.
- Limita maximă de overdraft este de **1.000 euro**.
- Dacă banii disponibili nu ajung pentru cheltuielile lunii și pentru plata introdusă de tine, platforma va folosi overdraftul, în limita disponibilă.
- Dacă limita este depășită, plata nu poate fi executată.
"""
    )

    st.markdown(
        """
### Ce se întâmplă după confirmare
- Dacă plata este posibilă, aceasta se înregistrează.
- Soldul creditului scade.
- Soldul final al lunii este actualizat automat.
- Primești scorul lunii.
- Dacă plata este imposibilă, nu se execută și scorul lunii este **0**.
"""
    )

    st.markdown(
        """
### Scor și rezultat final
- Scorul lunar este binar: **1** pentru o decizie executabilă, **0** pentru o decizie imposibilă.
- La finalul celor 24 de luni se adună punctele lunare.
- Scorul final este apoi ajustat în funcție de creditul rămas, overdraftul rămas și dobânzile sau penalitățile acumulate.
"""
    )

    st.markdown(
        """
### Mesajele cheie ale simulării
- **Decizie validă:** Decizia a fost acceptată. Plata a fost înregistrată, iar soldurile au fost actualizate.
- **Decizie imposibilă:** Suma introdusă depășește lichiditatea disponibilă și limita de overdraft rămasă. Plata nu a fost executată. Pentru această lună, scorul este 0.
"""
    )

    st.markdown(
        """
### Fluxul fiecărei luni
1. Pagina lunii curente
2. Context narativ al lunii
3. Tabel bugetar lunar
4. Câmp pentru suma de rambursat din credit
5. Buton **Confirmă decizia**
6. Ecran de feedback lunar
7. Buton **Continuă către luna următoare**
"""
    )

    st.markdown(
        """
### Framing monetar
- În admin panel există opțiunea **A. Gain frame** sau **B. Loss frame**.
- Participantul nu poate schimba această opțiune.
- Formula matematică rămâne aceeași în ambele variante.
"""
    )

    if st.button("Începe simularea →", type="primary"):
        goto("simulation")


# ==================== SIMULATION ====================
elif st.session_state.page == "simulation":

    if st.session_state.month > 24:
        goto("post_questions")

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

    with st.expander("Context narativ"):
        narrative = re.sub(r'^(\S+)', r'<strong>\1</strong>', get_narrative(month))
        st.markdown(
            f'<div style="text-align: justify">{narrative}</div>',
            unsafe_allow_html=True,
        )

    st.subheader("Buget lunar")

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

    st.info(
        f"""**Decizie privind plata creditului**

Sold inițial disponibil: **{opening_balance:.2f} €**

Venituri totale: **{income_total:.2f} €**

Cheltuieli curente: **{expenses_total:.2f} €**

Dobândă overdraft: **{overdraft_interest:.2f} €** | Penalități: **{penalties:.2f} €**

Sold disponibil după cheltuieli și costuri: **{liquidity_after_charges:.2f} €**

Sold credit rămas: **{loan.balance:.2f} €** | Sold overdraft: **{overdraft.balance:.2f} €**

Plata orientativă a creditului în această lună: **{loan_obligation:.2f} €**
"""
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
    st.caption("Introduceți o sumă numerică mai mare sau egală cu 0.")
    st.caption("După confirmare, decizia nu mai poate fi modificată.")

    if st.button("Confirmă decizia", type="primary"):
        if payment is None:
            st.warning("Vă rugăm să introduceți o sumă numerică validă, mai mare sau egală cu 0.")
            st.stop()

        result = compute_month_result(month, data, loan, overdraft, payment)
        st.session_state.pending_month_result = result
        st.session_state.page = "month_feedback"
        st.session_state.scroll_to_top = True
        st.rerun()


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
    st.write(f"**Sold final disponibil:** {result['cash_final']:.2f} €")
    st.write(f"**Sold credit rămas:** {result['credit_final']:.2f} €")
    st.write(f"**Sold overdraft final:** {result['overdraft_final']:.2f} €")
    st.write(f"**Dobânzi și penalități luna aceasta:** {result['costs_this_month']:.2f} €")
    st.metric("Scorul lunii", result["monthly_score"])

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
        st.session_state.page = "simulation"
        st.session_state.scroll_to_top = True
        st.rerun()


# ==================== POST-SIMULATION QUESTIONS ====================
elif st.session_state.page == "post_questions":
    scroll_top_anchor()
    st.title("Chestionar – după simulare")
    st.markdown("Indicați cât de mult sunteți de acord cu fiecare afirmație, în funcție de cum vă simțiți **acum**.")

    for section in POST_SECTIONS:
        render_question_section(section)

    st.markdown("### Feedback opțional")
    st.session_state.answers["feedback"] = st.text_area(
        "Ce parte a simulării ți s-a părut cea mai provocatoare sau realistă?",
        value=st.session_state.answers.get("feedback", ""),
    )

    if DEV:
        if st.button("⚡ DEV: Randomizează și finalizează", type="secondary"):
            randomize_sections(POST_SECTIONS)
            goto("done")

    if not all_answered(POST_SECTIONS):
        st.warning("Te rugăm să răspunzi la toate întrebările înainte de a finaliza.")

    if st.button("Finalizează →", type="primary"):
        if all_answered(POST_SECTIONS):
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
    st.markdown(framing_summary(st.session_state.final_score))
    st.markdown(
        f"""
Puncte lunare brute: **{st.session_state.total_score:.2f}**

Credit rămas: **{st.session_state.loan.balance:.2f} €**

Overdraft rămas: **{st.session_state.overdraft.balance:.2f} €**

Răspunsurile tale au fost înregistrate. Rezultatele studiului vor fi disponibile după finalizarea colectării datelor.

Contact: coita.iflorina@gmail.com
"""
    )
