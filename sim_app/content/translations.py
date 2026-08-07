from copy import deepcopy

import streamlit as st

from sim_app.content.narratives import get_narrative as get_ro_narrative
from sim_app.content.i18n_narratives import NARRATIVES_EN
from sim_app.content.i18n_questionnaire import POST_SECTIONS_EN
from sim_app.content.i18n_questionnaire import PRE_SECTIONS_EN
from sim_app.content.questions import POST_SECTIONS as POST_SECTIONS_RO
from sim_app.content.questions import PRE_SECTIONS as PRE_SECTIONS_RO


SUPPORTED_LANGUAGES = ("ro", "en")


UI_TEXT = {
    "ro": {
        "language": {
            "ro": "RO",
            "en": "EN",
        },
        "auth": {
            "brand": "XperimentCredit",
            "title": "Decizii financiare sub presiune",
            "copy": "Autentifică-te pentru a începe sau relua experimentul exact din punctul în care ai rămas.",
            "chips": [
                "Progres salvat",
                "Reluare după întrerupere",
                "Răspunsuri separate",
            ],
            "google_button": "Continuă cu Google",
            "privacy_html": "<strong>Confidențialitate:</strong> Platforma folosește autentificarea Google pentru identificarea sesiunii, prevenirea participărilor multiple și reluarea progresului în caz de întrerupere. Aplicația poate accesa numele, fotografia de profil și adresa de e-mail asociate contului Google. Aceste date de identificare vor fi stocate separat de răspunsurile experimentale. Analiza statistică se va realiza pe date anonime, folosind un cod unic de participant, fără includerea adresei de e-mail, numelui sau fotografiei de profil în setul de date analizat.",
            "privacy_note": "Răspunsurile tale vor fi analizate în mod anonim și vor ajuta la înțelegerea legăturii dintre trăsăturile individuale și modul în care oamenii iau decizii financiare în condiții incerte sau stresante.",
            "language_label": "Limbă",
            "account_fallback": "Cont conectat",
        "admin_page": "Admin",
        "admin_debug": "Debug admin",
        "admin_email": "Email detectat",
        "admin_configured": "Admini configurați",
            "admin_status": "Este admin",
            "admin_yes": "Da",
            "admin_no": "Nu",
            "admin_navigator": "Navigator admin",
            "admin_navigator_current": "Pagina: {page}",
            "admin_previous": "Inapoi",
            "admin_next": "Inainte",
            "logout": "Log out",
        },
        "study_session": {
            "title": "Codul sesiunii",
            "body": "Introdu codul de 6 cifre primit de la administrator pentru a participa la sesiunea activă.",
            "input_label": "Cod de sesiune",
            "input_help": "Codul trebuie să conțină exact 6 cifre.",
            "participant_label": "Cod participant",
            "participant_help": "Introdu codul primit in laborator, de forma P001.",
            "button": "Continuă",
            "optional_button": "Alătură-te unei sesiuni cu cod",
            "skip_button": "Continuă fără cod",
            "invalid": "Codul introdus nu corespunde unei sesiuni active.",
            "missing": "Te rugăm să introduci un cod valid din 6 cifre.",
            "participant_missing": "Te rugam sa introduci un cod participant valid, de forma P001.",
        },
        "prolific": {
            "error_missing_params": "Access denied. Please open the study only through Prolific.",
            "error_invalid_study": "Access denied. This Prolific study is not configured for this platform.",
            "error_already_completed": "Our records show that this Prolific ID has already completed this study. Duplicate participation is not allowed.",
            "anti_ai_declaration": "I confirm that I will complete this study myself, without using automated tools, scripts, browser agents, or AI systems to generate answers.",
            "comprehension_title": "Comprehension check",
            "comprehension_intro": "Please answer these questions before continuing. If needed, go back and re-read the instructions.",
            "comprehension_q1": "Who should complete this study?",
            "comprehension_q1_options": [
                "A. The Prolific participant personally",
                "B. A friend of the participant",
                "C. An automated tool",
                "D. Any person using the same computer",
            ],
            "comprehension_q2": "What is your task in each monthly decision?",
            "comprehension_q2_options": [
                "A. Choose how much of the loan to repay based on the available information",
                "B. Guess the researcher’s preferred answer",
                "C. Always choose the same amount",
                "D. Skip difficult months",
            ],
            "comprehension_button": "Continue",
            "comprehension_missing": "Please answer both comprehension questions.",
            "comprehension_retry": "One or more answers were incorrect. Please re-read the instructions and try once more.",
            "return_message": "You did not pass the study comprehension check after two attempts. Please close this page and return the study on Prolific by selecting “Stop Without Completing”.",
            "attention_1": "To show that you are reading the questions, please select number 3 below.",
            "attention_2": "Attention check: please select number 3 on the scale below.",
            "attention_number_options": ["1", "2", "3", "4", "5"],
            "attention_missing": "Please answer the attention check before continuing.",
            "redirecting": "Răspunsurile tale au fost salvate. Apasă butonul de mai jos pentru a reveni la Prolific.",
            "redirect_link": "Return to Prolific",
            "completion_code_fallback": "Dacă linkul nu se deschide, introdu manual în Prolific codul de finalizare:",
            "completion_ready": "Răspunsurile tale au fost salvate. Copiază codul de finalizare sau deschide manual linkul Prolific de mai jos.",
            "completion_code_label": "Cod de finalizare Prolific",
            "completion_link_label": "Link de finalizare Prolific",
            "completion_not_configured": "Linkul de finalizare Prolific nu este configurat. Te rugăm să contactezi cercetătorul înainte de a închide această pagină.",
        },
        "admin": {
            "title": "Panou administrator",
            "body": "Această pagină este disponibilă doar conturilor de administrator configurate prin adresă de e-mail.",
            "start_session": "Start a session",
            "sessions_title": "Administrare sesiuni",
            "create_session": "Create new session",
            "create_session_title": "Create new session",
            "cancel_create": "Cancel",
            "back_admin": "Inapoi la admin",
            "no_sessions": "Nu exista sesiuni active inca.",
            "created_success": "Sesiunea a fost creată. Distribuie codul de mai jos participanților.",
            "active_sessions": "Lista sesiunilor",
            "sessions_note": "Anularea oprește sesiunea fără a șterge datele deja colectate.",
            "cancel_session": "Anulează sesiunea",
            "cancelled_success": "Sesiunea {code} a fost anulată.",
            "cancelled_error": "Sesiunea nu a putut fi anulată.",
            "code_label": "Cod",
            "condition_label": "Condiție",
            "conditions": {
                "C1": "C1 - Gain frame + scor lunar afișat",
                "C2": "C2 - Gain frame + scor lunar neafișat",
                "C3": "C3 - Loss frame + scor lunar afișat",
                "C4": "C4 - Loss frame + scor lunar neafișat",
            },
            "condition_descriptions": {
                "C1": "Participantul pornește de la 0 GBP și vede scorul lunar pe pagina de feedback.",
                "C2": "Participantul pornește de la 0 GBP și nu vede scorul lunar.",
                "C3": "Participantul pornește de la un bonus maxim provizoriu de 3 GBP și vede scorul lunar ca pierdere.",
                "C4": "Participantul pornește de la un bonus maxim provizoriu de 3 GBP și nu vede scorul lunar.",
            },
            "created_at": "Creată la",
            "status": "Status",
            "participants_title": "Participanți",
            "no_participants": "Nu există încă participanți cu cod P### în această sesiune.",
            "participants_refresh_note": "Lista sesiunilor și progresul participanților se actualizează automat la fiecare 10 secunde.",
            "final_score_label": "Scor final",
            "payout_label": "Plata",
            "payment_status_label": "Status plata",
            "total_payout_label": "Plata totala",
            "participant_stage_pre": "Pre-psihometric",
            "participant_stage_months": "Luni",
            "participant_stage_post": "Post-psihometric",
            "back_home": "Înapoi la experiment",
        },
        "quiz": {
            "chapter_label": "Secțiunea {current}",
            "chapter_heading": "Capitolul {number}",
            "chapter_continue_help": "Răspunde la capitolul curent, apoi apasă **Continuă** pentru a trece mai departe.",
            "chapter_required_warning": "Te rugăm să răspunzi la toate întrebările din acest capitol înainte de a continua.",
            "chapter_missing_error": "Sunt întrebări fără răspuns.",
            "continue_button": "Continuă →",
            "skip_all_button": "Skip all chapters",
            "pre_title": "Chestionar – înainte de experiment",
            "post_title": "Chestionar post-experiment",
            "post_optional_feedback_title": "### Feedback opțional",
            "post_optional_feedback_prompt": "Ce parte a experimentului ți s-a părut cea mai provocatoare sau realistă?",
            "post_strategy_prompt": "Ce strategie ați folosit în timpul experimentului?",
            "post_finish_button": "Finalizează →",
            "dev_randomize": "⚡ DEV: Randomizează acest capitol și continuă",
        },
        "already_completed": {
            "title": "Participare deja finalizată",
            "body": "Acest cont a finalizat deja experimentul. Nu poate fi trimis un al doilea răspuns.",
            "button": "Începe un experiment nou (test)",
        },
        "home": {
            "title": "Percepția riscului și decizia financiară în condiții de incertitudine",
            "body": """Acest studiu își propune să investigheze modul în care indivizii percep și evaluează riscul
atunci când iau decizii financiare în contexte incerte sau instabile. Vei fi invitat(ă) să
parcurgi o serie de experimente realiste de creditare, în care va trebui să formulezi estimări
și să iei decizii care implică bani, timp și responsabilitate.

Scopul este de a înțelege cum interacționează stările afective și profilul psihologic cu
procesul decizional în situații economice riscante.""",
            "info": "Chestionarele sunt validate științific și nu conțin răspunsuri «corecte» sau «greșite». Răspunde cât mai sincer, alegând opțiunea care reflectă cel mai bine cum ești tu în general.",
            "gain_frame_notice": "Începi experimentul cu un bonus de performanță de 0 GBP. În funcție de deciziile tale și de scorul comportamental final, poți câștiga până la 3 GBP, ajungând la un bonus final de performanță între 1 și 3 GBP.",
            "loss_frame_notice": "Începi experimentul cu un bonus maxim provizoriu de performanță de 3 GBP. În funcție de deciziile tale și de scorul comportamental final, poți pierde până la 2 GBP, ajungând la un bonus final de performanță între 1 și 3 GBP.",
            "note": "Răspunsurile tale vor fi analizate **în mod anonim** și vor ajuta la înțelegerea legăturii dintre trăsăturile individuale și modul în care oamenii iau decizii financiare în condiții incerte sau stresante.",
            "button": "Începe experimentul →",
        },
        "consent": {
            "markdown": """## Acord de participare ?i consim??m?nt informat

Percep?ia riscului ?i decizia financiar? ?n condi?ii de incertitudine

E?ti invitat(?) s? participi la un studiu de cercetare despre modul ?n care persoanele iau decizii financiare ?n condi?ii de incertitudine. Studiul include un experiment financiar structurat, ?n care vei lua decizii lunare privind rambursarea unui credit, pe baza unor informa?ii despre venituri, cheltuieli, sold disponibil ?i evolu?ia obliga?iilor financiare.

Participarea este voluntar?. Te rug?m s? cite?ti cu aten?ie informa?iile de mai jos ?nainte de a decide dac? dore?ti s? continui.

Scopul studiului este de a analiza rela?ia dintre profilul psihologic, percep?ia riscului, nivelul de stres ?i deciziile financiare luate ?ntr-un experiment de credit.

Dac? accep?i s? participi, vei parcurge urm?toarele etape:

- vei citi informa?iile despre studiu ?i vei confirma consim??m?ntul informat;
- vei completa un scurt profil demografic;
- vei r?spunde la un chestionar psihologic ini?ial;
- vei parcurge un experiment financiar structurat pe mai multe luni, ?n care vei lua decizii privind rambursarea unui credit;
- vei completa un chestionar final despre starea ta psihologic? dup? experiment ?i despre percep?ia asupra sarcinii.

?n cadrul experimentului, vei primi informa?ii financiare lunare ?i vei decide suma pe care dore?ti s? o aloci ramburs?rii creditului. Experimentul este construit pentru a reflecta situa?ii financiare realiste, f?r? a implica acces la conturi bancare reale sau modific?ri asupra unor obliga?ii financiare personale.

Participarea dureaz? aproximativ 30-45 de minute, ?n func?ie de ritmul de completare.

?n cadrul studiului pot fi colectate urm?toarele categorii de date:

- r?spunsuri la ?ntreb?ri demografice generale;
- r?spunsuri la chestionare psihometrice;
- deciziile introduse ?n cadrul experimentului financiar;
- indicatori calcula?i automat pe baza deciziilor luate ?n experiment, precum soldul creditului, utilizarea overdraftului, penalit??i, dob?nzi ?i scoruri experimentale;
- r?spunsuri la ?ntreb?ri finale despre experien?a ?n cadrul experimentului.

Nu ?i se va cere s? furnizezi date bancare reale, parole, coduri de acces, extrase de cont reale sau informa?ii financiare identificabile.

Situa?iile financiare, evenimentele lunare ?i informa?iile prezentate ?n cadrul experimentului sunt construite pentru scopuri de cercetare. Acestea nu reprezint? o evaluare a situa?iei tale financiare personale ?i nu produc efecte asupra vreunui credit real, cont bancar sau raport de credit.

Deciziile tale din cadrul experimentului sunt folosite exclusiv ?n scop de cercetare.

Studiul include situa?ii legate de credit, datorii, presiune financiar?, stres, obliga?ii lunare ?i incertitudine.

Nu exist? r?spunsuri corecte sau gre?ite. Nu evalu?m competen?a ta financiar? ?i nu formul?m judec??i individuale despre deciziile tale.

Po?i ?ntrerupe participarea ?n orice moment, f?r? s? oferi explica?ii.

Datele vor fi analizate anonim. R?spunsurile individuale nu vor fi publicate ?n mod identificabil.

Dac? platforma folose?te un cod de participant, acesta va fi utilizat doar pentru a lega r?spunsurile ini?iale, deciziile din cadrul experimentului ?i r?spunsurile finale. Codul nu va fi folosit pentru identificarea public? a participantului.

Rezultatele vor fi raportate agregat, de exemplu sub form? de medii, corela?ii, modele statistice sau grafice.

Participarea este voluntar?. Ai dreptul:

- s? refuzi participarea;
- s? ?ntrerupi completarea ?n orice moment;
- s? nu r?spunzi la o ?ntrebare, dac? aceasta permite op?iune de necompletare;
- s? solici?i informa?ii suplimentare despre studiu.

Retragerea din studiu nu va avea consecin?e negative asupra ta.

Participarea la acest studiu poate include o compensa?ie fix? pentru participare ?i/sau o recompens? experimental? calculat? pe baza deciziilor luate ?n cadrul experimentului financiar.

Recompensa experimental? are rol exclusiv de stimulent ?n cadrul studiului ?i nu reprezint? o evaluare real? a situa?iei financiare, a competen?ei financiare sau a bonit??ii participantului.

Datele colectate pot fi utilizate pentru: analize statistice; lucr?ri ?tiin?ifice; prezent?ri academice; rapoarte de cercetare; dezvoltarea unor modele experimentale privind decizia financiar?.

Nicio publica?ie sau prezentare nu va include informa?ii care s? permit? identificarea direct? a participan?ilor.

Te rug?m s? confirmi urm?toarele afirma?ii ?nainte de a continua:""",
            "items": [
                "Am citit și am înțeles informațiile despre studiu.",
                "Am înțeles că participarea este voluntară.",
                "Am înțeles că pot întrerupe participarea în orice moment.",
                "Am înțeles că voi parcurge un experiment financiar care poate include situații de presiune financiară, stres și incertitudine.",
                "Am înțeles că datele mele vor fi analizate anonim.",
                "Am înțeles că nu mi se cer date bancare reale sau informații financiare identificabile.",
                "Am înțeles că deciziile luate în cadrul experimentului nu afectează un credit real, un cont bancar sau un raport de credit.",
                "Sunt de acord să particip la acest studiu.",
            ],
            "accept_button": "Sunt de acord și doresc să continui",
            "decline_button": "Nu sunt de acord",
            "warning": "Te rugăm să confirmi toate afirmațiile înainte de a continua.",
        },
        "consent_declined": {
            "title": "Participare întreruptă",
            "body": "Ai ales să nu îți dai consimțământul pentru participare. Participarea este voluntară, iar chestionarul nu va începe fără acordul tău.",
            "button": "Înapoi la acordul de participare",
        },
        "demographics": {
            "title": "Profil demografic",
            "intro": "Următoarele întrebări ne ajută să descriem eșantionul de participanți la nivel general. Răspunsurile vor fi analizate agregat și nu vor fi folosite pentru identificarea ta.",
            "age_title": "1. Vârsta",
            "age_caption": "Răspuns numeric",
            "age_prompt": "Te rugăm să introduci vârsta ta în ani împliniți:",
            "age_note": "Recomandare tehnică: acceptă doar valori între 18 și 75",
            "gender_title": "2. Genul",
            "gender_prompt": "Cum te identifici?",
            "education_title": "3. Nivelul de educație",
            "education_prompt": "Care este cel mai înalt nivel de educație finalizat?",
            "field_title": "4. Domeniul principal de studiu sau activitate",
            "field_prompt": "Care este domeniul tău principal de studiu sau activitate profesională?",
            "occupation_title": "5. Statut ocupațional",
            "occupation_prompt": "Care este statutul tău principal în prezent?",
            "income_title": "6. Venitul lunar personal",
            "income_prompt": "Care este intervalul aproximativ al venitului tău lunar net?",
            "financial_decisions_title": "7. Experiență cu decizii financiare personale",
            "financial_decisions_prompt": "Cât de des iei decizii legate de buget personal, plăți, economisire sau datorii?",
            "credit_experience_title": "8. Experiență anterioară cu produse de creditare",
            "credit_experience_prompt": "Ai utilizat vreodată un produs de creditare, cum ar fi credit de nevoi personale, card de credit, overdraft, credit ipotecar sau cumpărături în rate?",
            "financial_familiarity_title": "9. Familiaritate cu conceptele financiare",
            "financial_familiarity_prompt": "Cât de familiar(ă) ești cu termeni precum dobândă, rată lunară, sold restant, penalitate sau overdraft?",
            "living_title": "10. Situație de trai",
            "living_prompt": "Care variantă descrie cel mai bine situația ta actuală de trai?",
            "responsibilities_title": "11. Responsabilități financiare recurente",
            "responsibilities_prompt": "Ai responsabilități financiare recurente, cum ar fi chirie, rate, întreținere, sprijin pentru familie sau alte obligații lunare?",
            "country_title": "12. Țara de rezidență",
            "country_caption": "Răspuns liber",
            "country_prompt": "În ce țară locuiești în prezent?",
            "continue_button": "Continuă către chestionar →",
            "warning": "Te rugăm să răspunzi la toate întrebările înainte de a continua.",
            "options": {
                "gender": ["Femeie", "Bărbat", "Non-binar / altă identitate de gen", "Prefer să nu răspund"],
                "education": [
                    "Studii liceale",
                    "Studii postliceale",
                    "Studii universitare de licență",
                    "Studii universitare de master",
                    "Studii doctorale",
                    "Alt nivel de educație",
                    "Prefer să nu răspund",
                ],
                "field": [
                    "Economie / Finanțe / Contabilitate / Business",
                    "Informatică / Tehnologie / Inginerie",
                    "Științe sociale / Psihologie / Educație",
                    "Medicină / Științe ale vieții",
                    "Drept / Administrație publică",
                    "Arte / Științe umaniste",
                    "Alt domeniu",
                    "Prefer să nu răspund",
                ],
                "occupation": [
                    "Student(ă)",
                    "Angajat(ă) cu normă întreagă",
                    "Angajat(ă) cu normă parțială",
                    "Lucrător independent / freelancer / antreprenor",
                    "Șomer(ă) / în căutarea unui loc de muncă",
                    "Inactiv profesional / altă situație",
                    "Prefer să nu răspund",
                ],
                "income": [
                    "Nu am venit personal",
                    "Sub 500 EUR pe lună",
                    "500–999 EUR pe lună",
                    "1.000–1.499 EUR pe lună",
                    "1.500–2.499 EUR pe lună",
                    "2.500–3.999 EUR pe lună",
                    "4.000 EUR sau mai mult pe lună",
                    "Prefer să nu răspund",
                ],
                "frequency": ["Niciodată sau aproape niciodată", "Rar", "Uneori", "Des", "Foarte des", "Prefer să nu răspund"],
                "credit": ["Da", "Nu", "Nu sunt sigur(ă)", "Prefer să nu răspund"],
                "familiarity": ["Deloc familiar(ă)", "Puțin familiar(ă)", "Moderat familiar(ă)", "Familiar(ă)", "Foarte familiar(ă)", "Prefer să nu răspund"],
                "living": ["Locuiesc singur(ă)", "Locuiesc cu partenerul/partenera", "Locuiesc cu familia", "Locuiesc cu colegi/prieteni", "Altă situație", "Prefer să nu răspund"],
                "yes_no": ["Da", "Nu", "Prefer să nu răspund"],
            },
        },
        "instructions": {
            "body": """## Instrucțiuni pentru participant

În acest experiment vei lua rolul lui Andrei, o persoană care are un credit de nevoi personale și trebuie să ia decizii lunare de rambursare.

Experimentul se desfasoara pe parcursul a 24 de luni.

În fiecare lună vei vedea informațiile financiare ale lunii:

- venituri;
- cheltuieli;
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

<div style="border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 12px; padding: 0.9rem 1rem; margin: 1rem 0; background: rgba(255, 255, 255, 0.03);">
<strong>Pașii deciziei lunare</strong>
<ul>
<li>Introdu suma pe care vrei să o plătești din credit pentru luna respectivă.</li>
<li>Apoi apeși <strong>Confirmă decizia</strong>.</li>
<li>După confirmare, decizia nu mai poate fi modificată.</li>
<li>Vei vedea ecranul de feedback pentru luna curentă.</li>
<li>Apoi apeși <strong>Continuă către luna următoare</strong>.</li>
</ul>
</div>

Platforma va calcula automat:

- dacă plata poate fi realizată;
- cât scade soldul creditului;
- dacă se folosește overdraftul;
- care este suma rămasă după plată;
- care este overdraftul final al lunii;
- ce scor primești pentru luna respectivă.

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
- dobânzile totale acumulate.

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

Dacă suma introdusă depășește resursele disponibile și limita de overdraft, plata nu va fi executată, iar scorul lunii va fi 0.""",
            "button": "Continuă către profil →",
        },
        "profile": {
            "title": "Profilul participantului",
            "intro": "Înainte de a începe experimentul, citește cu atenție profilul personajului pe care îl vei reprezenta.",
            "sections": [
                {
                    "title": "Profil general – Andrei",
                    "body": """| | |
|---|---|
| **Nume** | Andrei |
| **Vârstă** | 34 de ani |
| **Oraș** | Locuiește într-un oraș mare |
| **Locuință** | Împreună cu soția, în chirie, apartament de 2 camere |
| **Chirie** | 330 euro / lună (nu include utilitățile) |""",
                },
                {
                    "title": "Situație profesională",
                    "body": """Andrei lucrează de aproximativ 6 ani în aceeași companie, într-o firmă din zona de servicii / corporație
(de exemplu: suport tehnic, operațiuni, back-office, project coordinator junior).
Nu este la început de drum, dar nici într-o poziție foarte bine plătită.

| | |
|---|---|
| **Contract** | Perioadă nedeterminată |
| **Venit lunar net** | Aproximativ 1.000 euro |

Venitul este relativ stabil, dar:
- fără bonusuri garantate
- creșteri salariale mici și rare
- uneori apar întârzieri administrative

Andrei se percepe ca având un job „sigur".""",
                },
                {
                    "title": "Situație personală și emoțională",
                    "body": """- Maria are un venit net lunar în jur de 720 euro.
- Are un cerc restrâns de prieteni, mulți dintre ei deja căsătoriți, cu copii, cu rate la casă.

Andrei nu este impulsiv emoțional, dar:
- evită conflictele
- evită să spună „nu" în contexte sociale
- preferă soluții pe termen scurt care reduc stresul imediat""",
                },
                {
                    "title": "Stil de viață și hobby-uri",
                    "body": """- Iese de 1–2 ori pe săptămână în oraș (mâncare, cafea).
- Merge ocazional la sală.
- Are mașină (nu foarte nouă), pe care o folosește zilnic.
- Îi place să plece din oraș de câteva ori pe an.
- Nu cheltuie extravagant, dar nici nu ține un buget strict.
- Cheltuielile „mici, dar dese" sunt o constantă.""",
                },
                {
                    "title": "Obiceiuri financiare",
                    "body": """Andrei:
- nu ține un buget scris
- știe aproximativ cât câștigă, cât este chiria și cât este rata
- restul banilor sunt gestionați „din mers"

Are următoarele obiceiuri:
- plătește facturile la timp, de obicei
- evită restanțele, pentru că îl stresează
- când apare o problemă, taie mai întâi din economii
- abia la final reduce din cheltuieli""",
                },
                {
                    "title": "Economii",
                    "body": """La începutul experimentului:
- are aproximativ **150 euro** economii
- ținute în cont curent, nu separat
- nu are un „fond de urgență" clar definit

Aceste economii:
- nu sunt rezultatul unei discipline
- sunt mai degrabă „ce a rămas" din ultimele luni mai bune""",
                },
                {
                    "title": "Creditul",
                    "body": """| | |
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
- cu convingerea că „mă descurc fără probleme".""",
                },
                {
                    "title": "Cum se raportează Andrei la credit",
                    "body": """Nu vede creditul ca pe un pericol. Îl vede ca pe „o obligație fixă". Nu se gândește la ce se întâmplă dacă:
- venitul întârzie
- apar 2–3 luni proaste la rând

Are mentalitatea: **„Dacă apare ceva, rezolv atunci."**

Creditul îl plătește Andrei, dar cheltuielile lunare sunt suportate împreună.""",
                },
                {
                    "title": "Overdraft",
                    "body": """| | |
|---|---|
| **Tip instrument** | Linie de credit de tip overdraft atașată contului curent |
| **Limită maximă** | Aproximativ 3.000 euro |
| **Dobândă** | 18% pe an (1,5% pe lună) |

**Rolul overdraftului:** funcționează ca o rezervă de lichiditate care poate fi utilizată atunci când cheltuielile
lunare depășesc suma disponibilă în cont.

**Mod de utilizare:** dacă totalul cheltuielilor lunare și al sumei introduse pentru plata creditului depășește
lichiditatea disponibilă, diferența este acoperită automat din overdraft, în limita disponibilă.
Participanții nu activează manual overdraftul, dar decizia lor de plată poate conduce la utilizarea lui.

""",
                },
            ],
            "button": "Începe experimentul →",
        },
        "simulation": {
            "month_title": "Luna {month}",
            "score_accumulated": "Scor acumulat",
            "narrative_expander": "Context narativ",
            "budget_expander": "Buget lunar",
            "income_header": "**Venituri**",
            "income_total": "**Total venituri:** {value}",
            "expenses_header": "**Cheltuieli curente**",
            "expenses_total": "**Total cheltuieli:** {value}",
            "decision_title": "Decizie privind plata creditului",
            "opening_balance": "Sold inițial disponibil",
            "income_total_label": "Venituri totale",
            "expenses_total_label": "Cheltuieli curente",
            "overdraft_interest_label": "Dobândă overdraft",
            "credit_interest_label": "Dobândă credit",
            "remaining_credit_label": "Sold credit rămas",
            "used_overdraft_label": "Overdraft utilizat",
            "available_before_payment_label": "Bani disponibili înainte de plata creditului",
            "available_before_payment_formula": "<strong>Bani disponibili înainte de plata creditului</strong> = sold inițial disponibil + venituri totale - cheltuieli curente - dobândă credit - dobândă overdraft",
            "contract_rate_label": "Rată contractuală de referință",
            "blocked_error": "Cheltuielile lunii depășesc lichiditatea disponibilă și limita de overdraft. Plata creditului nu poate fi executată.",
            "payment_label": "Sumă de rambursat din credit (€)",
            "payment_placeholder": "Introduceți o sumă numerică mai mare sau egală cu 0.",
            "payment_note": "După confirmare, decizia nu mai poate fi modificată.",
            "confirm_button": "Confirmă decizia",
            "no_payment_due_notice": "Creditul a fost deja rambursat integral. În această lună nu mai există o plată de credit scadentă.",
            "payment_validation_warning": "Vă rugăm să introduceți o sumă numerică validă, mai mare sau egală cu 0.",
            "save_error": "Eroare la salvarea lunii curente. Te rugăm să reîncarci pagina și să încerci din nou.",
            "feedback_title": "Luna {month} - feedback",
            "decision_result_heading": "### Rezultatul deciziei",
            "payment_entered": "**Suma introdusă:** {value}",
            "payment_accepted": "**Plata acceptată la credit:** {value}",
            "cash_after_payment": "**Sold disponibil după plata ratei = Sold inițial + Venituri − Cheltuieli curente − Dobândă overdraft − Rata − Dobânda credit:** {value}",
            "credit_remaining": "**Sold credit rămas:** {value}",
            "overdraft_final": "**Overdraft utilizat final:** {value}",
            "credit_interest_month": "**Dobândă credit luna aceasta:** {value}",
            "overdraft_interest_month": "**Dobândă overdraft luna aceasta:** {value}",
            "penalties_month": "**Penalități luna aceasta:** {value}",
            "monthly_score_heading": "### Scorul lunii",
            "score_repayment": "**Scor rambursare:** {value} / 40",
            "score_liquidity": "**Scor lichiditate:** {value} / 30",
            "score_overdraft": "**Scor overdraft:** {value} / 30",
            "score_credit_metric": "Scor credit",
            "score_liquidity_metric": "Scor lichiditate",
            "score_overdraft_metric": "Scor overdraft",
            "monthly_score_metric": "Scor lunar",
            "monthly_score_lost_metric": "Puncte pierdute luna aceasta",
            "continue_month_button": "Continuă către luna următoare",
            "continue_next_page_button": "Continuă către pagina următoare",
            "feedback_success": "Decizia a fost acceptată. Plata a fost înregistrată, iar soldurile au fost actualizate.",
            "feedback_no_payment_due": "Creditul a fost deja rambursat integral. În această lună nu a fost necesară nicio plată la credit.",
            "feedback_invalid": "Suma introdusă depășește lichiditatea disponibilă și limita de overdraft rămasă. Plata nu a fost executată.",
            "feedback_pre_credit": "Cheltuielile lunii depășesc lichiditatea disponibilă și limita de overdraft. Plata creditului nu poate fi executată.",
        },
        "final_score": {
            "title": "Scor final",
            "intro": "Ai finalizat cele 24 de luni ale experimentului.",
            "heading": "### Scor comportamental final",
            "card_label": "Scor comportamental final",
            "bonus_label": "Bonus final obținut",
            "performance_bonus_label": "Bonus de performanță obținut",
            "initial_bonus_label": "Bonus de performanță inițial",
            "bonus_lost_label": "Bonus de performanță pierdut",
            "final_bonus_label": "Bonus de performanță final",
            "summary_heading": "### Rezumat financiar final",
            "total_repaid": "Total rambursat din credit",
            "remaining_credit": "Credit rămas la final",
            "remaining_overdraft": "Overdraft utilizat la final",
            "interest_total": "Dobânzi totale acumulate",
            "info": "Scorul comportamental final a fost calculat automat pe baza deciziilor lunare privind rambursarea creditului, lichiditatea rămasă după plată și utilizarea overdraftului.",
            "caption": "Datele generate în experiment vor fi folosite doar în scopul cercetării, conform acordului de participare.",
            "button": "Continuă →",
        },
        "done": {
            "save_error": "Eroare la salvarea datelor: {error}",
            "title": "Mulțumim pentru participare!",
            "score_metric": "Scor comportamental final",
            "participant_code_label": "Cod participant",
            "bonus_label": "Bonus final obținut",
            "remaining_credit": "Credit rămas",
            "remaining_overdraft": "Overdraft utilizat",
            "registered_text": "Răspunsurile tale au fost înregistrate. Rezultatele studiului vor fi disponibile după finalizarea colectării datelor.",
            "save_pending": "Răspunsurile nu au fost încă salvate. Te rugăm să reîncarci pagina pentru a încerca din nou.",
            "contact": "Contact",
            "dev_caption": "Mod de testare activ: poți parcurge din nou experimentul cu același cont.",
            "dev_button": "Începe un experiment nou (test)",
        },
        "table": {
            "category": "Categoria",
            "value": "Valoare (€)",
        },
    },
    "en": {
        "language": {
            "ro": "RO",
            "en": "EN",
        },
        "auth": {
            "brand": "XperimentCredit",
            "title": "Financial decisions under pressure",
            "copy": "Sign in to start or resume the experiment exactly where you left off.",
            "chips": [
                "Saved progress",
                "Resume after interruption",
                "Separate responses",
            ],
            "google_button": "Continue with Google",
            "privacy_html": "<strong>Privacy:</strong> The platform uses Google authentication for session identification, duplicate-participation prevention, and progress recovery after interruption. The app may access the name, profile photo, and email address associated with the Google account. This identifying data will be stored separately from the experimental responses. Statistical analysis will be conducted on anonymous data, using a unique participant code, without including the email address, name, or profile photo in the analyzed dataset.",
            "privacy_note": "Your responses will be analyzed anonymously and will help us understand the link between individual traits and how people make financial decisions under uncertain or stressful conditions.",
            "language_label": "Language",
        "account_fallback": "Connected account",
        "admin_page": "Admin",
        "admin_debug": "Admin debug",
        "admin_email": "Detected email",
        "admin_configured": "Configured admins",
            "admin_status": "Is admin",
            "admin_yes": "Yes",
            "admin_no": "No",
            "admin_navigator": "Admin navigator",
            "admin_navigator_current": "Page: {page}",
            "admin_previous": "Previous",
            "admin_next": "Next",
            "logout": "Log out",
        },
        "study_session": {
            "title": "Session code",
            "body": "Enter the 6-digit code received from the administrator to join the active session.",
            "input_label": "Session code",
            "input_help": "The code must contain exactly 6 digits.",
            "participant_label": "Participant ID",
            "participant_help": "Enter the lab code you received, for example P001.",
            "button": "Continue",
            "optional_button": "Join a session with code",
            "skip_button": "Continue without a code",
            "invalid": "The code you entered does not match an active session.",
            "missing": "Please enter a valid 6-digit code.",
            "participant_missing": "Please enter a valid participant ID, for example P001.",
        },
        "prolific": {
            "error_missing_params": "Access denied. Please open the study only through Prolific.",
            "error_invalid_study": "Access denied. This Prolific study is not configured for this platform.",
            "error_already_completed": "Our records show that this Prolific ID has already completed this study. Duplicate participation is not allowed.",
            "anti_ai_declaration": "I confirm that I will complete this study myself, without using automated tools, scripts, browser agents, or AI systems to generate answers.",
            "comprehension_title": "Comprehension check",
            "comprehension_intro": "Please answer these questions before continuing. If needed, go back and re-read the instructions.",
            "comprehension_q1": "Who should complete this study?",
            "comprehension_q1_options": [
                "A. The Prolific participant personally",
                "B. A friend of the participant",
                "C. An automated tool",
                "D. Any person using the same computer",
            ],
            "comprehension_q2": "What is your task in each monthly decision?",
            "comprehension_q2_options": [
                "A. Choose how much of the loan to repay based on the available information",
                "B. Guess the researcher’s preferred answer",
                "C. Always choose the same amount",
                "D. Skip difficult months",
            ],
            "comprehension_button": "Continue",
            "comprehension_missing": "Please answer both comprehension questions.",
            "comprehension_retry": "One or more answers were incorrect. Please re-read the instructions and try once more.",
            "return_message": "You did not pass the study comprehension check after two attempts. Please close this page and return the study on Prolific by selecting “Stop Without Completing”.",
            "attention_1": "To show that you are reading the questions, please select number 3 below.",
            "attention_2": "Attention check: please select number 3 on the scale below.",
            "attention_number_options": ["1", "2", "3", "4", "5"],
            "attention_missing": "Please answer the attention check before continuing.",
            "redirecting": "Your responses have been saved. Use the button below to return to Prolific.",
            "redirect_link": "Return to Prolific",
            "completion_code_fallback": "If the link does not open, enter this completion code manually in Prolific:",
            "completion_ready": "Your responses have been saved. Copy the completion code or manually open the Prolific link below.",
            "completion_code_label": "Prolific completion code",
            "completion_link_label": "Prolific completion link",
            "completion_not_configured": "The Prolific completion link is not configured. Please contact the researcher before closing this page.",
        },
        "admin": {
            "title": "Admin panel",
            "body": "This page is available only to administrator accounts configured by email address.",
            "start_session": "Start a session",
            "sessions_title": "Session management",
            "create_session": "Create new session",
            "create_session_title": "Create new session",
            "cancel_create": "Cancel",
            "back_admin": "Back to admin",
            "no_sessions": "No active sessions yet.",
            "created_success": "The session has been created. Share the code below with participants.",
            "active_sessions": "Session list",
            "sessions_note": "Cancelling stops the session without deleting any data already collected.",
            "cancel_session": "Cancel session",
            "cancelled_success": "Session {code} has been cancelled.",
            "cancelled_error": "The session could not be cancelled.",
            "code_label": "Code",
            "condition_label": "Condition",
            "conditions": {
                "C1": "C1 - Gain frame + monthly score displayed",
                "C2": "C2 - Gain frame + monthly score hidden",
                "C3": "C3 - Loss frame + monthly score displayed",
                "C4": "C4 - Loss frame + monthly score hidden",
            },
            "condition_descriptions": {
                "C1": "The participant starts from 0 GBP and sees the monthly score on the feedback page.",
                "C2": "The participant starts from 0 GBP and does not see the monthly score.",
                "C3": "The participant starts from a provisional maximum bonus of 3 GBP and sees the monthly score as lost points.",
                "C4": "The participant starts from a provisional maximum bonus of 3 GBP and does not see the monthly score.",
            },
            "created_at": "Created at",
            "status": "Status",
            "participants_title": "Participants",
            "no_participants": "No P### participants have joined this session yet.",
            "participants_refresh_note": "The session list and participant progress refresh automatically every 10 seconds.",
            "final_score_label": "Final score",
            "payout_label": "Payout",
            "payment_status_label": "Payment status",
            "total_payout_label": "Total payout",
            "participant_stage_pre": "Pre-psychometric",
            "participant_stage_months": "Months",
            "participant_stage_post": "Post-psychometric",
            "back_home": "Back to experiment",
        },
        "quiz": {
            "chapter_label": "Section {current}",
            "chapter_heading": "Chapter {number}",
            "chapter_continue_help": "Answer the current chapter, then press **Continue** to move on.",
            "chapter_required_warning": "Please answer all questions in this chapter before continuing.",
            "chapter_missing_error": "Some questions are still unanswered.",
            "continue_button": "Continue →",
            "skip_all_button": "Skip all chapters",
            "pre_title": "Questionnaire - before the experiment",
            "post_title": "Post-experiment questionnaire",
            "post_optional_feedback_title": "### Optional feedback",
            "post_optional_feedback_prompt": "Which part of the experiment felt the most challenging or realistic to you?",
            "post_strategy_prompt": "What strategy did you use during the experiment?",
            "post_finish_button": "Finish →",
            "dev_randomize": "⚡ DEV: Randomize this chapter and continue",
        },
        "already_completed": {
            "title": "Participation already completed",
            "body": "This account has already completed the experiment. A second response cannot be submitted.",
            "button": "Start a new experiment (test)",
        },
        "home": {
            "title": "Risk perception and financial decision-making under uncertainty",
            "body": """This study aims to investigate how individuals perceive and evaluate risk
when making financial decisions in uncertain or unstable contexts. You will be invited to
go through a series of realistic credit experiments in which you will need to make estimates
and take decisions involving money, time, and responsibility.

The goal is to understand how affective states and psychological profile interact with
decision-making in risky economic situations.""",
            "info": "The questionnaires are scientifically validated and do not contain “correct” or “incorrect” answers. Answer as honestly as possible, choosing the option that best reflects how you are in general.",
            "gain_frame_notice": "You start the experiment with a performance bonus of 0 GBP. Depending on your decisions and final behavioral score, you can gain up to 3 GBP, resulting in a final performance bonus between 1 and 3 GBP.",
            "loss_frame_notice": "You start the experiment with a provisional maximum performance bonus of 3 GBP. Depending on your decisions and final behavioral score, you can lose up to 2 GBP, resulting in a final performance bonus between 1 and 3 GBP.",
            "note": "Your responses will be analyzed **anonymously** and will help us understand the link between individual traits and how people make financial decisions under uncertain or stressful conditions.",
            "button": "Start the experiment →",
        },
        "consent": {
            "markdown": """## Participation agreement and informed consent

Risk perception and financial decision-making under uncertainty

You are invited to take part in a research study on how people make financial decisions under conditions of uncertainty. The study includes a structured financial experiment in which you will make monthly decisions about repaying a loan based on information about income, expenses, available balance, and the evolution of financial obligations.

Participation is voluntary. Please read the information below carefully before deciding whether you wish to continue.

The purpose of the study is to analyze the relationship between psychological profile, risk perception, stress level, and financial decisions made in a credit-based experiment.

If you agree to participate, you will go through the following stages:

- you will read the study information and confirm your informed consent;
- you will complete a short demographic profile;
- you will answer an initial psychological questionnaire;
- you will go through a structured financial experiment spanning several months, in which you will make decisions about loan repayment;
- you will complete a final questionnaire about your psychological state after the experiment and your perception of the task.

During the experiment, you will receive monthly financial information and decide how much you want to allocate to loan repayment. The experiment is designed to reflect realistic financial situations, without involving access to real bank accounts or changes to any personal financial obligations.

Participation takes approximately 30-45 minutes, depending on your pace of completion.

The following categories of data may be collected in this study:

- answers to general demographic questions;
- answers to psychometric questionnaires;
- decisions entered during the financial experiment;
- indicators automatically calculated on the basis of decisions made in the experiment, such as loan balance, overdraft use, penalties, interest, and experimental scores;
- answers to final questions about your experience during the experiment.

You will not be asked to provide real banking data, passwords, access codes, real account statements, or identifiable financial information.

The financial situations, monthly events, and information presented during the experiment are constructed for research purposes. They do not represent an assessment of your personal financial situation and do not produce effects on any real loan, bank account, or credit report.

Your decisions in the experiment are used exclusively for research purposes.

The study includes situations related to credit, debt, financial pressure, stress, monthly obligations, and uncertainty.

There are no correct or incorrect answers. We are not evaluating your financial competence, and we do not make individual judgments about your decisions.

You may stop participating at any time without having to provide an explanation.

The data will be analyzed anonymously. Individual responses will not be published in an identifiable way.

If the platform uses a participant code, it will only be used to link the initial responses, the decisions made during the experiment, and the final responses. The code will not be used for public identification of the participant.

Results will be reported in aggregate form, for example as averages, correlations, statistical models, or graphs.

Participation is voluntary. You have the right:

- to refuse participation;
- to stop completing the study at any time;
- not to answer a question if it allows a non-response option;
- to request additional information about the study.

Withdrawing from the study will not have negative consequences for you.

Participation in this study may include a fixed compensation for participation and/or an experimental reward calculated on the basis of the decisions made during the financial experiment.

The experimental reward serves exclusively as an incentive within the study and does not represent a real evaluation of the participant?s financial situation, financial competence, or creditworthiness.

The collected data may be used for: statistical analyses; scientific papers; academic presentations; research reports; and the development of experimental models of financial decision-making.

No publication or presentation will include information that could directly identify participants.

Please confirm the following statements before continuing:""",
            "items": [
                "I have read and understood the information about the study.",
                "I understand that participation is voluntary.",
                "I understand that I may stop participating at any time.",
                "I understand that I will go through a financial experiment that may include situations of financial pressure, stress, and uncertainty.",
                "I understand that my data will be analyzed anonymously.",
                "I understand that I am not asked to provide real banking data or identifiable financial information.",
                "I understand that the decisions made during the experiment do not affect a real loan, bank account, or credit report.",
                "I agree to participate in this study.",
            ],
            "accept_button": "I agree and want to continue",
            "decline_button": "I do not agree",
            "warning": "Please confirm all statements before continuing.",
        },
        "consent_declined": {
            "title": "Participation interrupted",
            "body": "You chose not to give your consent for participation. Participation is voluntary, and the questionnaire will not begin without your agreement.",
            "button": "Back to the participation agreement",
        },
        "demographics": {
            "title": "Demographic profile",
            "intro": "The following questions help us describe the participant sample at a general level. Responses will be analyzed in aggregate and will not be used to identify you.",
            "age_title": "1. Age",
            "age_caption": "Numeric response",
            "age_prompt": "Please enter your age in completed years:",
            "age_note": "Technical recommendation: accept only values between 18 and 75",
            "gender_title": "2. Gender",
            "gender_prompt": "How do you identify?",
            "education_title": "3. Education level",
            "education_prompt": "What is the highest level of education you have completed?",
            "field_title": "4. Main field of study or activity",
            "field_prompt": "What is your main field of study or professional activity?",
            "occupation_title": "5. Occupational status",
            "occupation_prompt": "What is your main status at present?",
            "income_title": "6. Personal monthly income",
            "income_prompt": "What is the approximate range of your monthly net income?",
            "financial_decisions_title": "7. Experience with personal financial decisions",
            "financial_decisions_prompt": "How often do you make decisions related to personal budgeting, payments, saving, or debt?",
            "credit_experience_title": "8. Previous experience with credit products",
            "credit_experience_prompt": "Have you ever used a credit product such as a personal loan, credit card, overdraft, mortgage, or installment purchase?",
            "financial_familiarity_title": "9. Familiarity with financial concepts",
            "financial_familiarity_prompt": "How familiar are you with terms such as interest, monthly installment, outstanding balance, penalty, or overdraft?",
            "living_title": "10. Living situation",
            "living_prompt": "Which option best describes your current living situation?",
            "responsibilities_title": "11. Recurring financial responsibilities",
            "responsibilities_prompt": "Do you have recurring financial responsibilities such as rent, installments, utilities, family support, or other monthly obligations?",
            "country_title": "12. Country of residence",
            "country_caption": "Open response",
            "country_prompt": "In which country do you currently live?",
            "continue_button": "Continue to questionnaire →",
            "warning": "Please answer all questions before continuing.",
            "options": {
                "gender": ["Woman", "Man", "Non-binary / another gender identity", "Prefer not to answer"],
                "education": [
                    "High school education",
                    "Post-secondary education",
                    "Bachelor’s degree",
                    "Master’s degree",
                    "Doctoral studies",
                    "Another level of education",
                    "Prefer not to answer",
                ],
                "field": [
                    "Economics / Finance / Accounting / Business",
                    "Computer science / Technology / Engineering",
                    "Social sciences / Psychology / Education",
                    "Medicine / Life sciences",
                    "Law / Public administration",
                    "Arts / Humanities",
                    "Another field",
                    "Prefer not to answer",
                ],
                "occupation": [
                    "Student",
                    "Full-time employee",
                    "Part-time employee",
                    "Self-employed / freelancer / entrepreneur",
                    "Unemployed / looking for work",
                    "Professionally inactive / another situation",
                    "Prefer not to answer",
                ],
                "income": [
                    "I have no personal income",
                    "Under 500 EUR per month",
                    "500–999 EUR per month",
                    "1,000–1,499 EUR per month",
                    "1,500–2,499 EUR per month",
                    "2,500–3,999 EUR per month",
                    "4,000 EUR or more per month",
                    "Prefer not to answer",
                ],
                "frequency": ["Never or almost never", "Rarely", "Sometimes", "Often", "Very often", "Prefer not to answer"],
                "credit": ["Yes", "No", "I am not sure", "Prefer not to answer"],
                "familiarity": ["Not at all familiar", "Slightly familiar", "Moderately familiar", "Familiar", "Very familiar", "Prefer not to answer"],
                "living": ["I live alone", "I live with my partner", "I live with my family", "I live with roommates/friends", "Another situation", "Prefer not to answer"],
                "yes_no": ["Yes", "No", "Prefer not to answer"],
            },
        },
        "instructions": {
            "body": """## Instructions for the participant

In this experiment you will take on the role of Andrei, a person who has a personal loan and must make monthly repayment decisions.

The experiment takes place over 24 months.

Each month you will see monthly financial information:

- income;
- expenses;
- loan interest;
- overdraft interest, if any;
- money available before loan payment;
- loan balance;
- overdraft used;
- monthly installment specified in the contract.

After reading the month’s information, you must enter the amount you want to repay toward the loan for that month.

You decide only the amount paid toward the loan.

You do not need to repay the overdraft separately. The overdraft is updated automatically in the platform, depending on the month’s deficit and the amount you enter for loan payment.

### What the overdraft is

The overdraft is a credit line attached to the current account. In this experiment, the maximum overdraft limit is 3,000 euro.

The overdraft functions as a reserve of borrowed money. If the money available is not enough for the month’s expenses or for the payment you enter, the platform may use the overdraft, but only within the available limit.

Using the overdraft increases indebtedness and reduces the monthly score.

### How the amount available before loan payment is calculated

Each month, the platform automatically calculates the money available before loan payment.

The formula is:

Money available before loan payment =
initial available balance + total income - current expenses - loan interest - overdraft interest

This amount shows what is available before you enter the loan payment.

### How the monthly decision works

<div style="border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 12px; padding: 0.9rem 1rem; margin: 1rem 0; background: rgba(255, 255, 255, 0.03);">
<strong>Monthly decision steps</strong>
<ul>
<li>Enter the amount you want to pay toward the loan for that month.</li>
<li>Then press <strong>Confirm decision</strong>.</li>
<li>After confirmation, the decision can no longer be changed.</li>
<li>You will see the feedback screen for the current month.</li>
<li>Then press <strong>Continue to the next month</strong>.</li>
</ul>
</div>

The platform will automatically calculate:

- whether the payment can be made;
- how much the loan balance decreases;
- whether the overdraft is used;
- what amount remains after payment;
- what the final overdraft for the month is;
- what score you receive for that month.

### What happens if you enter a feasible amount

If the amount entered can be covered by the available money and the remaining overdraft, the payment is accepted.

In this case:

- the payment is recorded;
- the loan balance decreases;
- the month’s balances are updated;
- the month’s score is calculated automatically.

### What happens if you enter an invalid amount

If you enter an amount greater than the available money plus the remaining overdraft, the payment cannot be made.

In this case:

- the payment is rejected;
- the loan does not decrease through that payment;
- the entered amount is not transferred into overdraft;
- the maximum overdraft limit is not exceeded;
- the month’s score is 0;
- the experiment continues with the next month.

After you confirm an invalid amount, you will not be able to go back and correct it. That is why it is important to check the information carefully before confirming.

### What you can correct before confirmation

Before you press “Confirm decision,” you can correct the amount you entered.

If you accidentally enter letters, symbols, or a negative value, the platform will ask you to enter a valid numeric value.

### How the monthly score is awarded

Each month, the score can vary between 0 and 100 points.

The monthly score takes into account three aspects:

1. the amount repaid toward the loan;
2. the monthly liquidity balance;
3. the level of overdraft used.

A larger loan payment can increase the repayment score, but it must be supported by the month’s financial situation.

Keeping a reserve of money after payment contributes to the liquidity score.

Using a larger overdraft reduces the monthly score.

The monthly score does not represent a personal evaluation. It reflects only the financial result of the decision entered under that month’s conditions.

### How the final score is calculated

At the end of the 24 months, the platform calculates the final behavioral score.

The final behavioral score is the average of the monthly scores obtained across the 24 months.

The general formula is:

Final behavioral score =
average of the monthly scores across the 24 months

The final bonus is calculated based on the final behavioral score.

### What is displayed at the end

At the end of the experiment you will see:

- the final behavioral score;
- the final bonus obtained;
- the remaining loan balance at the end;
- the overdraft used at the end;
- the total accumulated interest.

### General rule of the experiment

The goal is not to pay the same amount every time.

The goal is to make a monthly decision that can be supported by that month’s financial situation.

In some months it may be easier to pay the monthly installment specified in the contract. In other months, because of income, expenses, and interest, the decision may be more difficult.

You must choose the amount you consider appropriate, taking into account:

- income;
- expenses;
- loan interest;
- overdraft interest;
- the remaining loan balance;
- the overdraft used;
- the money available before payment;
- the risk of entering an impossible payment.

### Important message before starting the experiment

Please read the information for each month carefully before entering the repayment amount.

After you press “Confirm decision,” the amount entered can no longer be changed.

If the amount entered exceeds the available resources and the overdraft limit, the payment will not be executed and the month’s score will be 0.""",
            "button": "Continue to profile →",
        },
        "profile": {
            "title": "Participant profile",
            "intro": "Before starting the experiment, read carefully the profile of the character you will represent.",
            "sections": [
                {
                    "title": "General profile - Andrei",
                    "body": """| | |
|---|---|
| **Name** | Andrei |
| **Age** | 34 years old |
| **City** | Lives in a large city |
| **Housing** | Together with his wife, renting a 2-room apartment |
| **Rent** | 330 euro / month (utilities not included) |""",
                },
                {
                    "title": "Professional situation",
                    "body": """Andrei has been working for about 6 years at the same company, in a services/corporate firm
(for example: technical support, operations, back office, junior project coordinator).
He is not at the beginning of his career, but neither is he in a very well-paid position.

| | |
|---|---|
| **Contract** | Permanent contract |
| **Monthly net income** | Approximately 1,000 euro |

His income is relatively stable, but:
- no guaranteed bonuses
- salary increases are small and rare
- administrative delays sometimes occur

Andrei sees his job as “secure.”""",
                },
                {
                    "title": "Personal and emotional situation",
                    "body": """- Maria has a monthly net income of around 720 euro.
- He has a small circle of friends, many of them already married, with children, and mortgage payments.

Andrei is not emotionally impulsive, but:
- he avoids conflicts
- he avoids saying “no” in social contexts
- he prefers short-term solutions that reduce immediate stress""",
                },
                {
                    "title": "Lifestyle and hobbies",
                    "body": """- He goes out 1–2 times a week (food, coffee).
- He goes to the gym occasionally.
- He has a car (not very new), which he uses daily.
- He likes to leave town a few times a year.
- He does not spend extravagantly, but he does not keep a strict budget either.
- “Small but frequent” expenses are a constant.""",
                },
                {
                    "title": "Financial habits",
                    "body": """Andrei:
- does not keep a written budget
- knows approximately how much he earns, how much the rent is, and how much the installment is
- the rest of the money is managed “on the go”

He has the following habits:
- he usually pays his bills on time
- he avoids arrears because they stress him
- when a problem appears, he first cuts from savings
- only at the end does he reduce spending""",
                },
                {
                    "title": "Savings",
                    "body": """At the start of the experiment:
- he has approximately **150 euro** in savings
- kept in the current account, not separately
- he does not have a clearly defined “emergency fund”

These savings:
- are not the result of discipline
- are rather “what was left” from the last better months""",
                },
                {
                    "title": "The loan",
                    "body": """| | |
|---|---|
| **Loan type** | Personal needs loan |
| **Initial value** | Approximately 7,000 euro |
| **Duration** | 24 months |
| **Monthly installment** | 317.71 euro |
| **Interest** | 8.35% |

Why he took the loan:
- furniture and appliances for the apartment
- part of the money went to moving
- minor repairs
- a few “comfort” expenses

The loan was not taken in a crisis, but:
- during a relatively stable period
- with the belief that “I can handle it without problems”.""",
                },
                {
                    "title": "How Andrei relates to the loan",
                    "body": """He does not see the loan as a danger. He sees it as “a fixed obligation.” He does not think about what happens if:
- the income is delayed
- 2–3 bad months appear in a row

His mentality is: **“If something comes up, I’ll deal with it then.”**

Andrei pays the loan, but monthly expenses are borne together.""",
                },
                {
                    "title": "Overdraft",
                    "body": """| | |
|---|---|
| **Instrument type** | Overdraft credit line attached to the current account |
| **Maximum limit** | Approximately 3,000 euro |
| **Interest** | 18% per year (1.5% per month) |

**Role of the overdraft:** it works as a liquidity reserve that can be used when monthly
expenses exceed the amount available in the account.

**How it is used:** if total monthly expenses and the amount entered for loan payment exceed
the available liquidity, the difference is covered automatically from the overdraft, within the available limit.
Participants do not activate the overdraft manually, but their payment decision can lead to its use.""",
                },
            ],
            "button": "Start the experiment →",
        },
        "simulation": {
            "month_title": "Month {month}",
            "score_accumulated": "Accumulated score",
            "narrative_expander": "Narrative context",
            "budget_expander": "Monthly budget",
            "income_header": "**Income**",
            "income_total": "**Total income:** {value}",
            "expenses_header": "**Current expenses**",
            "expenses_total": "**Total expenses:** {value}",
            "decision_title": "Loan payment decision",
            "opening_balance": "Initial available balance",
            "income_total_label": "Total income",
            "expenses_total_label": "Current expenses",
            "overdraft_interest_label": "Overdraft interest",
            "credit_interest_label": "Loan interest",
            "remaining_credit_label": "Remaining loan balance",
            "used_overdraft_label": "Overdraft used",
            "available_before_payment_label": "Money available before loan payment",
            "available_before_payment_formula": "<strong>Money available before loan payment</strong> = initial available balance + total income - current expenses - loan interest - overdraft interest",
            "contract_rate_label": "Reference contractual installment",
            "blocked_error": "This month’s expenses exceed the available liquidity and the overdraft limit. The loan payment cannot be executed.",
            "payment_label": "Loan repayment amount (€)",
            "payment_placeholder": "Enter a numeric amount greater than or equal to 0.",
            "payment_note": "After confirmation, the decision can no longer be changed.",
            "confirm_button": "Confirm decision",
            "no_payment_due_notice": "The loan has already been fully repaid. No loan payment is due this month.",
            "payment_validation_warning": "Please enter a valid numeric amount greater than or equal to 0.",
            "save_error": "Error while saving the current month. Please reload the page and try again.",
            "feedback_title": "Month {month} - feedback",
            "decision_result_heading": "### Decision result",
            "payment_entered": "**Entered amount:** {value}",
            "payment_accepted": "**Accepted loan payment:** {value}",
            "cash_after_payment": "**Available balance after installment payment = Initial balance + Income − Current expenses − Overdraft interest − Installment − Loan interest:** {value}",
            "credit_remaining": "**Remaining loan balance:** {value}",
            "overdraft_final": "**Final overdraft used:** {value}",
            "credit_interest_month": "**Loan interest this month:** {value}",
            "overdraft_interest_month": "**Overdraft interest this month:** {value}",
            "penalties_month": "**Penalties this month:** {value}",
            "monthly_score_heading": "### Monthly score",
            "score_repayment": "**Repayment score:** {value} / 40",
            "score_liquidity": "**Liquidity score:** {value} / 30",
            "score_overdraft": "**Overdraft score:** {value} / 30",
            "score_credit_metric": "Credit score",
            "score_liquidity_metric": "Liquidity score",
            "score_overdraft_metric": "Overdraft score",
            "monthly_score_metric": "Monthly score",
            "monthly_score_lost_metric": "Monthly points lost",
            "continue_month_button": "Continue to the next month",
            "continue_next_page_button": "Continue to the next page",
            "feedback_success": "The decision was accepted. The payment was recorded and the balances were updated.",
            "feedback_no_payment_due": "The loan has already been fully repaid. No loan payment was due this month.",
            "feedback_invalid": "The amount entered exceeds the available liquidity and the remaining overdraft limit. The payment was not executed.",
            "feedback_pre_credit": "This month’s expenses exceed the available liquidity and the overdraft limit. The loan payment cannot be executed.",
        },
        "final_score": {
            "title": "Final score",
            "intro": "You have completed all 24 months of the experiment.",
            "heading": "### Final behavioral score",
            "card_label": "Final behavioral score",
            "bonus_label": "Final bonus obtained",
            "performance_bonus_label": "Performance bonus obtained",
            "initial_bonus_label": "Initial performance bonus",
            "bonus_lost_label": "Performance bonus lost",
            "final_bonus_label": "Final performance bonus",
            "summary_heading": "### Final financial summary",
            "total_repaid": "Total amount repaid toward the loan",
            "remaining_credit": "Remaining loan balance at the end",
            "remaining_overdraft": "Overdraft used at the end",
            "interest_total": "Total accumulated interest",
            "info": "The final behavioral score was calculated automatically based on monthly decisions regarding loan repayment, the monthly liquidity balance, and overdraft use.",
            "caption": "The data generated in the experiment will be used only for research purposes, in accordance with the participation agreement.",
            "button": "Continue →",
        },
        "done": {
            "save_error": "Error while saving data: {error}",
            "title": "Thank you for participating!",
            "score_metric": "Final behavioral score",
            "participant_code_label": "Participant ID",
            "bonus_label": "Final bonus obtained",
            "remaining_credit": "Remaining loan balance",
            "remaining_overdraft": "Overdraft used",
            "registered_text": "Your responses have been recorded. The study results will be available after data collection is completed.",
            "save_pending": "Your responses have not been saved yet. Please reload this page to try again.",
            "contact": "Contact",
            "dev_caption": "Testing mode is active: you can go through the experiment again with the same account.",
            "dev_button": "Start a new experiment (test)",
        },
        "table": {
            "category": "Category",
            "value": "Value (€)",
        },
    },
}


CATEGORY_LABELS = {
    "ro": {
        "andrei": "andrei",
        "maria": "maria",
        "bonus_andrei": "bonus andrei",
        "bonus_maria": "bonus maria",
        "other": "alte venituri",
        "rent": "chirie",
        "utilities": "utilități",
        "food": "mâncare",
        "transport": "transport",
        "car": "auto",
        "phone": "telefon / internet",
        "social": "social",
        "medical": "sănătate",
        "baby": "copil / familie",
        "home": "casă",
        "holiday": "vacanță",
        "vacation": "vacanță",
        "event": "eveniment",
        "repair": "reparații",
    },
    "en": {
        "andrei": "Andrei",
        "maria": "Maria",
        "bonus_andrei": "Andrei bonus",
        "bonus_maria": "Maria bonus",
        "other": "other income",
        "rent": "rent",
        "utilities": "utilities",
        "food": "food",
        "transport": "transport",
        "car": "car",
        "phone": "phone / internet",
        "social": "social",
        "medical": "medical",
        "baby": "child / family",
        "home": "home",
        "holiday": "holiday",
        "vacation": "vacation",
        "event": "event",
        "repair": "repairs",
    },
}


def ensure_language():
    language = st.session_state.get("language", "en")
    if language not in SUPPORTED_LANGUAGES:
        language = "en"
    st.session_state.language = language
    return language


def get_language():
    return ensure_language()


def set_language(language):
    st.session_state.language = language if language in SUPPORTED_LANGUAGES else "en"


def _lookup(mapping, key):
    value = mapping
    for part in key.split("."):
        value = value[part]
    return value


def t(key, language=None, **kwargs):
    selected_language = language or get_language()
    value = _lookup(UI_TEXT[selected_language], key)
    if isinstance(value, str) and kwargs:
        return value.format(**kwargs)
    return value


def get_category_label(category_key, language=None):
    selected_language = language or get_language()
    return CATEGORY_LABELS.get(selected_language, {}).get(category_key, category_key)


def get_display_pre_sections(language=None):
    selected_language = language or get_language()
    if selected_language == "en":
        return deepcopy(PRE_SECTIONS_EN)
    return deepcopy(PRE_SECTIONS_RO)


def get_display_post_sections(language=None):
    selected_language = language or get_language()
    if selected_language == "en":
        return deepcopy(POST_SECTIONS_EN)
    return deepcopy(POST_SECTIONS_RO)


def get_localized_narrative(month, language=None):
    selected_language = language or get_language()
    if selected_language == "en":
        return NARRATIVES_EN.get(month, "No narrative available.")
    return get_ro_narrative(month)

