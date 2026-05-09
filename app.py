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
    st.session_state.answers = {}


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
            goto("profile")

    if not all_answered(PRE_SECTIONS):
        st.warning("Te rugăm să răspunzi la toate întrebările înainte de a continua.")
    if st.button("Continuă →", type="primary"):
        if all_answered(PRE_SECTIONS):
            goto("profile")
        else:
            st.error("Sunt întrebări fără răspuns.")


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
| **Oraș** | Locuiește într-un oraș mare (ex. București / Cluj / Timișoara) |
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
| **Venit lunar net** | Aproximativ 880 euro |

Venitul este relativ stabil, dar:
- fără bonusuri garantate
- creșteri salariale mici și rare
- uneori apar întârzieri administrative

Andrei se percepe ca având un job „sigur".
""")

    st.subheader("Situație personală și emoțională")
    st.markdown("""
- **Status relațional:** căsătorit cu Maria. Maria are un venit net lunar în jur de 600 euro.
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
| **Rată lunară** | Aproximativ 330 euro |
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
| **Limită maximă** | Aproximativ 1.000 euro |

**Rolul overdraftului:** funcționează ca o rezervă de lichiditate care poate fi utilizată atunci când cheltuielile
lunare depășesc suma disponibilă în cont.

**Mod de utilizare:** dacă totalul cheltuielilor lunare și al sumei introduse pentru plata creditului depășește
lichiditatea disponibilă, diferența este acoperită automat din overdraft, în limita disponibilă.
Participanții nu activează manual overdraftul, dar decizia lor de plată poate conduce la utilizarea lui.

**Dobândă overdraft:** sumele utilizate generează dobândă lunară, care se adaugă la datoria acumulată.

**Rambursarea overdraftului:** orice sumă rămasă în cont după efectuarea plăților lunare reduce automat
soldul overdraftului utilizat.
""")

    st.info("""**Instrucțiuni pentru participant**

În fiecare lună vei vedea:
- veniturile disponibile
- cheltuielile lunare
- suma rămasă în cont
- soldul creditului și al overdraftului
- dobânzile sau penalitățile acumulate

**La fiecare lună vei decide ce sumă dorești să plătești din credit.**
Decizia ta poate influența evoluția soldului creditului, utilizarea overdraftului și rezultatul financiar final.
""")

    st.markdown('</div>', unsafe_allow_html=True)

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

    income = sum(data["income"].values())
    expenses = sum(data["expenses"].values())
    initial = data["position"]["initial"]

    if st.session_state.savings is None:
        cash = initial + income - expenses
    else:
        cash = st.session_state.savings + income - expenses

    liquidity_before_credit = cash
    required_payment = loan.get_required_payment()

    col_title, col_score = st.columns([5, 1])
    with col_title:
        st.title(f"Luna {month}")
    with col_score:
        st.metric("Scor total", st.session_state.total_score)

    with st.expander("Scenariu"):
        narrative = re.sub(r'^(\S+)', r'<strong>\1</strong>', get_narrative(month))
        st.markdown(
            f'<div style="text-align: justify">{narrative}</div>',
            unsafe_allow_html=True,
        )

    st.subheader("Buget lunar")

    st.markdown("**Venituri**")
    st.table(pd.DataFrame(list(data["income"].items()), columns=["Categoria", "Valoare (€)"]))
    st.write(f"**Total venituri:** {income:.2f}")

    st.markdown("**Cheltuieli curente**")
    st.table(pd.DataFrame(list(data["expenses"].items()), columns=["Categoria", "Valoare (€)"]))
    st.write(f"**Total cheltuieli:** {expenses:.2f}")

    st.markdown("**Obligații financiare**")
    st.table(pd.DataFrame(list(data["obligations"].items()), columns=["Categoria", "Valoare (€)"]))

    st.markdown("**Poziție lunară**")
    st.table(pd.DataFrame([
        ("Sold inițial disponibil", f"{initial:.2f}"),
        ("Total venituri", f"{income:.2f}"),
        ("Total cheltuieli", f"{expenses:.2f}"),
    ], columns=["Indicator", "Valoare (€)"]))

    blocked = liquidity_before_credit <= 0
    max_payment = max(0.0, liquidity_before_credit)

    st.info(f"""**Decizie privind rata**

Sumă disponibilă înainte de plata creditului: **{liquidity_before_credit:.2f} €**

Rata recomandată: **{required_payment:.2f} €**

Sold credit: **{loan.balance:.2f} €** | Sold overdraft: **{overdraft.balance:.2f} €**
""")

    if blocked:
        payment = st.number_input(
            "Sumă de rambursat din credit (€)",
            min_value=0.0, max_value=0.0, value=0.0, step=1.0, disabled=True,
            key=f"payment_{month}"
        )
    else:
        payment = st.number_input(
            "Sumă de rambursat din credit (€)",
            min_value=0.0, step=1.0, value=None, placeholder="Introduceți suma...",
            key=f"payment_{month}"
        )

    if st.button("Confirmă plata"):
        if not blocked and payment is None:
            st.warning("Introduceți o sumă.")
            st.stop()

        cash -= payment
        loan_result = loan.apply_payment(payment)

        cash = overdraft.cover_deficit(cash)
        if cash > 0:
            cash = overdraft.repay(cash)
        overdraft_interest = overdraft.apply_interest()

        st.session_state.savings = cash

        loan_state = loan.get_state()
        overdraft_state = overdraft.get_state()

        lower_bound = 0.9 * required_payment
        upper_bound = 1.1 * required_payment
        invalid = not (lower_bound <= payment <= upper_bound)

        result_flag = 0 if invalid else 1
        st.session_state.total_score += result_flag

        st.subheader("Rezultate end of month")
        st.write(f"Dobândă credit: {loan_result['interest']:.2f} €")
        st.write(f"Principal rambursat: {loan_result['principal']:.2f} €")
        st.write(f"Economii rămase: {cash:.2f} €")
        st.write(f"Sold credit: {loan_state['balance']:.2f} €")
        st.write(f"Restanțe credit: {loan_state['arrears']:.2f} €")
        st.write(f"Sold overdraft: {overdraft_state['balance']:.2f} €")
        st.write(f"Dobândă overdraft luna aceasta: {overdraft_interest:.2f} €")
        st.write(f"Scor luna aceasta: {result_flag} | Scor total: {st.session_state.total_score}")

        st.session_state.month += 1
        st.session_state.scroll_to_top = True
        st.rerun()  # stay on simulation; flag triggers scroll on next render


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
    if not st.session_state.get("saved"):
        try:
            save_participant(
                st.session_state.session_id,
                st.session_state.answers,
                st.session_state.total_score,
            )
            st.session_state.saved = True
        except Exception as e:
            st.error(f"Eroare la salvarea datelor: {e}")

    st.title("Mulțumim pentru participare!")
    st.metric("Scor final simulare", st.session_state.total_score)
    st.markdown(
        "Răspunsurile tale au fost înregistrate. Rezultatele studiului vor fi disponibile "
        "după finalizarea colectării datelor.\n\n"
        "Contact: coita.iflorina@gmail.com"
    )
