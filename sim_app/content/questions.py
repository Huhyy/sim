SCALE_5_FREQ = ["1 - Niciodată", "2 - Rar", "3 - Uneori", "4 - Des", "5 - Întotdeauna"]
SCALE_4_BIS  = ["1 - Rar/niciodată", "2 - Ocazional", "3 - Deseori", "4 - Întotdeauna"]
SCALE_5_TRUE = ["1 - Deloc adevărat", "2 - Puțin adevărat", "3 - Moderat adevărat", "4 - Aproape complet adevărat", "5 - Complet adevărat"]
SCALE_5_FREQ2 = ["1 - Niciodată", "2 - Rareori", "3 - Uneori", "4 - Deseori", "5 - Aproape tot timpul"]
SCALE_5_AGREE = ["1 - Complet neadevărat", "2 - Mai degrabă neadevărat", "3 - Nici/nici", "4 - Mai degrabă adevărat", "5 - Complet adevărat"]
SCALE_5_POST  = ["1 - Complet în dezacord", "2 - În dezacord", "3 - Neutru", "4 - De acord", "5 - Complet de acord"]

# These response values are intentionally kept separate from their display
# labels.  The new post-task items use compact stored values ("1", "2", ...)
# and, for the bipolar score item, only the anchor positions are labelled.
STATE_STRESS_SCALE = ["1", "2", "3", "4", "5"]
SCORE_CHECK_SCALE = ["1", "2", "3", "4", "5", "6", "7"]
SCORE_PERCEIVED_SCALE = ["1", "2", "3"]
MCHECK_AVOID_SCALE = ["1", "2", "3", "4", "5"]


def question_key(section, index):
    keys = section.get("question_keys")
    if keys:
        return keys[index]
    return f"{section['key_prefix']}_{index}"


def question_scale(section, index):
    scales = section.get("question_scales")
    return list(scales[index] if scales else section["scale"])


def question_option_labels(section, index):
    labels = section.get("question_option_labels")
    if labels:
        return list(labels[index])
    return question_scale(section, index)

PRE_SECTIONS = [
    {
        "title": "🧠 I. Funcționalitate dopaminergică",
        "instruction": "Indică cât de des se potrivește cu felul tău de a fi, în general.",
        "scale": SCALE_5_FREQ,
        "key_prefix": "dopa",
        "questions": [
            "Mă simt plin(ă) de energie când încep un proiect sau o provocare nouă.",
            "Caut varietate în viața mea de zi cu zi (locuri noi, experiențe, mâncare etc.).",
            "Îmi stabilesc des obiective personale și îmi place să lucrez pentru a le atinge.",
            "Mă plictisesc repede de sarcini repetitive.",
            "Simt o plăcere intensă când reușesc ceva important pentru mine.",
            "Sunt foarte motivat(ă) când există o posibilă recompensă.",
            "Acționez rapid atunci când observ o oportunitate.",
        ],
    },
    {
        "title": "🌤️ II. Funcționalitate serotoninergică",
        "instruction": "Indică cât de des se potrivește cu felul tău de a fi, în general.",
        "scale": SCALE_5_FREQ,
        "key_prefix": "sero",
        "questions": [
            "De obicei rămân calm(ă) chiar și în situații dificile.",
            "Am rareori schimbări bruște de dispoziție.",
            "Tind să mă îngrijorez excesiv.",
            "Îmi este ușor să amân gratificarea.",
            "Reflectez adesea înainte să reacționez emoțional.",
            "Mă simt stabil(ă) din punct de vedere emoțional în majoritatea zilelor.",
            "Rareori mă simt copleșit(ă) de stres.",
        ],
    },
    {
        "title": "💞 III. Funcționalitate oxitocinergică",
        "instruction": "Indică cât de des se potrivește cu felul tău de a fi, în general.",
        "scale": SCALE_5_FREQ,
        "key_prefix": "oxyt",
        "questions": [
            "Mă simt conectat(ă) emoțional cu persoanele apropiate.",
            "Îmi vine ușor să am încredere în alții, chiar și când îi întâlnesc prima dată.",
            "Îmi place apropierea fizică (îmbrățișări, atingere) cu cei dragi.",
            "Intuiesc adesea ce simt alții, fără să-mi spună.",
            "Simt o satisfacție puternică atunci când ajut pe cineva.",
            "Îmi place să formez relații profunde și de lungă durată.",
            "Mă emoționează interacțiunile sociale pozitive.",
        ],
    },
    {
        "title": "💪 IV. Funcționalitate endorfinergică",
        "instruction": "Indică cât de des se potrivește cu felul tău de a fi, în general.",
        "scale": SCALE_5_FREQ,
        "key_prefix": "endo",
        "questions": [
            "Mă simt mai bine după activitate fizică sau exercițiu.",
            "Tolerez mai ușor disconfortul fizic decât majoritatea oamenilor.",
            "Râd des cu prieteni sau familie.",
            "Simt un impuls puternic al dispoziției după ce ascult muzica preferată.",
            "Folosesc umorul pentru a gestiona situații dificile.",
            "Mă simt liniștit(ă) după ce petrec timp în natură.",
            "Rareori simt tensiune fizică în perioade stresante.",
        ],
    },
    {
        "title": "🧠 Scala BIS-11",
        "instruction": "Alege cât de mult se aplică în cazul tău, în general.",
        "scale": SCALE_4_BIS,
        "key_prefix": "bis",
        "questions": [
            "Îmi vine greu să mă concentrez pe o singură activitate.",
            "Trec repede de la un gând la altul fără legătură.",
            "Vorbesc fără să mă gândesc bine înainte.",
            "Îmi pierd rapid interesul pentru ce fac.",
            "Îmi este greu să finalizez lucruri începute.",
            "Acționez din instinct, fără să analizez situația.",
            "Îmi schimb planurile fără motiv clar.",
            "Mă întrerup ușor în timp ce lucrez sau studiez.",
            "Am tendința să întrerup oamenii în conversații.",
            "Acționez rapid, fără să stau pe gânduri.",
            "Am dificultăți în a rămâne calm(ă) când trebuie să aștept.",
            "Nu suport sarcinile care cer răbdare sau rutină.",
            "Mă implic în activități riscante fără a evalua toate datele.",
            "Am momente în care fac lucruri fără să-mi dau seama de ce.",
            "Fac uneori cumpărături scumpe sau impulsive fără plan.",
            "Mă enervez ușor și reacționez pe moment.",
            "Nu obișnuiesc să planific pe termen lung.",
            "Tind să trăiesc «clipa» fără să mă gândesc la viitor.",
            "Nu-mi organizez cheltuielile decât când e prea târziu.",
            "Gândesc adesea «las că văd eu ce fac când ajung acolo».",
            "Mă bazez mai mult pe impuls decât pe strategie.",
            "Mă trezesc că iau decizii importante fără analiză.",
            "Încep proiecte fără să estimez cât timp sau resurse necesită.",
            "Nu mă gândesc la consecințe decât după ce acționez.",
            "Mă simt obligat(ă) să acționez imediat când sunt furios/oasă.",
            "Când sunt stresat(ă), iau decizii rapide și regret apoi.",
            "Emoțiile intense mă fac să pierd controlul acțiunilor.",
            "Când sunt foarte entuziasmat(ă), nu mă mai gândesc la riscuri.",
            "Mă calmez greu după ce iau o decizie impulsivă greșită.",
            "Îmi pare rău adesea pentru lucruri făcute «la nervi» sau «la impuls».",
        ],
    },
    {
        "title": "🔹 Satisfacție generală cu viața",
        "instruction": "Răspunde sincer, în funcție de cum te simți în general.",
        "scale": SCALE_5_TRUE,
        "key_prefix": "swl",
        "questions": [
            "În general, sunt mulțumit(ă) de viața mea.",
            "Simt că am obținut ceea ce mi-am dorit în viață până acum.",
            "Viața mea se apropie, în mare parte, de idealul meu personal.",
            "Dacă ar trebui să trăiesc din nou, nu aș schimba aproape nimic.",
            "Am mai multe lucruri în viața mea de care pot fi recunoscător/oare.",
        ],
    },
    {
        "title": "🔹 Afect pozitiv și energie vitală",
        "instruction": "Răspunde sincer, în funcție de cum te simți în general.",
        "scale": SCALE_5_TRUE,
        "key_prefix": "who5",
        "questions": [
            "M-am simțit energic(ă) și plin(ă) de viață în ultimele zile.",
            "Am avut momente în care m-am bucurat sincer de lucruri simple.",
            "Am avut o dispoziție senină și echilibrată.",
            "M-am simțit motivat(ă) să încep sau să finalizez lucruri.",
            "Am simțit apropiere sau conexiune pozitivă cu alți oameni.",
            "Am râs sau am zâmbit sincer frecvent în ultimele zile.",
            "M-am simțit competent(ă) și capabil(ă) în ce am făcut.",
        ],
    },
    {
        "title": "🔹 Afect negativ și distres",
        "instruction": "Răspunde sincer, în funcție de cum te simți în general.",
        "scale": SCALE_5_TRUE,
        "key_prefix": "neg_aff",
        "questions": [
            "M-am simțit copleșit(ă) de grijile personale sau financiare.",
            "M-am simțit fără speranță sau lipsit(ă) de motivație.",
            "Am fost iritabil(ă) sau frustrat(ă) fără un motiv clar.",
            "M-am simțit singur(ă) sau deconectat(ă) de ceilalți.",
            "M-am simțit neîncrezător/neîncrezătoare în forțele proprii.",
            "Am avut dificultăți în a dormi sau a mă relaxa.",
            "Am simțit o stare de tensiune interioară constantă.",
        ],
    },
    {
        "title": "🔹 Eudaimonie și sens în viață",
        "instruction": "Răspunde sincer, în funcție de cum te simți în general.",
        "scale": SCALE_5_TRUE,
        "key_prefix": "euda",
        "questions": [
            "Simt că ceea ce fac are sens și valoare pentru mine.",
            "Trăiesc în acord cu valorile mele personale.",
            "Simt că viața mea are o direcție clară.",
            "Simt că evoluez ca persoană și învăț lucruri relevante.",
            "Mă simt implicat(ă) în activități care îmi dau un sentiment de împlinire.",
            "Simt că am un scop personal care mă ghidează.",
        ],
    },
    {
        "title": "🔹 Resurse psihologice și reziliență",
        "instruction": "Răspunde sincer, în funcție de cum te simți în general.",
        "scale": SCALE_5_TRUE,
        "key_prefix": "resil",
        "questions": [
            "Simt că pot face față eficient situațiilor dificile.",
            "Când trec prin momente grele, găsesc modalități de a merge mai departe.",
            "Sunt capabil(ă) să-mi reglez emoțiile când e nevoie.",
            "Mă adaptez relativ repede la schimbări neprevăzute.",
            "Am o imagine de sine sănătoasă, chiar și când lucrurile merg prost.",
        ],
    },
    {
        "title": "🔹 Reevaluare cognitivă",
        "instruction": "Cât de mult te regăsești în fiecare afirmație?",
        "scale": SCALE_5_AGREE,
        "key_prefix": "reapp",
        "questions": [
            "Încerc să privesc situațiile stresante dintr-o altă perspectivă.",
            "Mă concentrez pe aspectele pozitive ale unei situații dificile.",
            "Reinterpretez ceea ce simt pentru a-mi păstra calmul.",
            "Îmi spun că lucrurile ar putea fi mai rele și asta mă liniștește.",
            "Îmi ajustez gândurile pentru a reduce impactul emoțional.",
        ],
    },
    {
        "title": "🔹 Suprimarea expresiei emoționale",
        "instruction": "Cât de mult te regăsești în fiecare afirmație?",
        "scale": SCALE_5_AGREE,
        "key_prefix": "suppr",
        "questions": [
            "Evit să arăt când sunt trist(ă) sau afectat(ă).",
            "Îmi ascund emoțiile în fața celorlalți.",
            "Încerc să nu exprim ce simt, chiar dacă e intens.",
            "Mă abțin să arăt furia sau frustrarea în public.",
            "Nu las emoțiile să mi se citească pe față.",
        ],
    },
    {
        "title": "🔹 Impulsivitate emoțională",
        "instruction": "Cât de mult te regăsești în fiecare afirmație?",
        "scale": SCALE_5_AGREE,
        "key_prefix": "emo_imp",
        "questions": [
            "Când simt ceva puternic, acționez imediat.",
            "Reacționez fără să mă gândesc, atunci când sunt supărat(ă).",
            "Când sunt furios/oasă, îmi pierd controlul.",
            "Nu pot să-mi stăpânesc acțiunile când sunt copleșit(ă) emoțional.",
            "Spun sau fac lucruri regretabile când sunt tensionat(ă).",
        ],
    },
    {
        "title": "🔹 Conștientizarea și înțelegerea emoțiilor",
        "instruction": "Cât de mult te regăsești în fiecare afirmație?",
        "scale": SCALE_5_AGREE,
        "key_prefix": "emo_aware",
        "questions": [
            "Pot să-mi identific emoțiile ușor.",
            "Știu ce simt, chiar și când e complicat.",
            "Observ rapid când starea mea emoțională se schimbă.",
            "Îmi înțeleg reacțiile afective fără efort.",
            "Mă pot exprima clar despre ceea ce simt.",
        ],
    },
    {
        "title": "🔹 Acceptarea emoțiilor",
        "instruction": "Cât de mult te regăsești în fiecare afirmație?",
        "scale": SCALE_5_AGREE,
        "key_prefix": "emo_acc",
        "questions": [
            "Încerc să ignor emoțiile negative.",
            "Mă simt inconfortabil când sunt copleșit(ă) emoțional.",
            "Nu îmi permit să simt furie sau frică.",
            "Evit emoțiile dureroase cât de mult pot.",
            "Nu suport să simt vulnerabilitate.",
            "Emoțiile intense mă fac să mă retrag.",
        ],
    },
    {
        "title": "🔹 Claritate emoțională și reglaj adaptiv",
        "instruction": "Cât de mult te regăsești în fiecare afirmație?",
        "scale": SCALE_5_AGREE,
        "key_prefix": "emo_reg",
        "questions": [
            "Mă pot liniști singur(ă) în momente dificile.",
            "Am metode clare prin care îmi reglez emoțiile.",
            "Pot face față unui conflict fără să explodez.",
            "Îmi revin relativ repede după un moment de criză.",
            "Pot cere ajutor emoțional când am nevoie.",
            "Îmi folosesc rațiunea chiar și când emoțiile sunt intense.",
            "Simt că am control asupra reacțiilor mele afective.",
            "Pot comunica emoțiile într-un mod care nu rănește.",
            "Mă ajut de activități (sport, scris, meditație) ca să mă reglez.",
            "Când ceva mă copleșește, știu exact ce strategie emoțională să aplic.",
        ],
    },
    {
        "title": "🔹 Big Five – Deschidere către experiență",
        "instruction": "Cât de bine te descriu afirmațiile de mai jos?",
        "scale": SCALE_5_AGREE,
        "key_prefix": "open",
        "questions": [
            "Îmi place să explorez idei noi și concepte abstracte.",
            "Mă bucur de artă, muzică și forme creative de exprimare.",
            "Sunt curios/oasă intelectual și deschis(ă) la perspective alternative.",
            "Mă plictisesc repede în contexte monotone sau rigide.",
        ],
    },
    {
        "title": "🔹 Big Five – Conștiinciozitate",
        "instruction": "Cât de bine te descriu afirmațiile de mai jos?",
        "scale": SCALE_5_AGREE,
        "key_prefix": "cons",
        "questions": [
            "Îmi organizez timpul și sarcinile cu grijă.",
            "Mă țin de angajamente chiar și când devine dificil.",
            "Îmi place să finalizez ce încep.",
            "Sunt atent(ă) la detalii și evit greșelile prin planificare.",
        ],
    },
    {
        "title": "🔹 Big Five – Extraversiune",
        "instruction": "Cât de bine te descriu afirmațiile de mai jos?",
        "scale": SCALE_5_AGREE,
        "key_prefix": "extra",
        "questions": [
            "Mă simt energizat(ă) în prezența altor persoane.",
            "Îmi place să fiu în centrul atenției.",
            "Mă exprim ușor în grupuri și conversații sociale.",
            "Prefer activitățile dinamice, cu interacțiune.",
        ],
    },
    {
        "title": "🔹 Big Five – Agreabilitate",
        "instruction": "Cât de bine te descriu afirmațiile de mai jos?",
        "scale": SCALE_5_AGREE,
        "key_prefix": "agree",
        "questions": [
            "Încerc să evit conflictele și să mențin armonia.",
            "Mă consider empatic(ă) și atent(ă) la nevoile altora.",
            "Sunt dispus(ă) să ajut, chiar dacă nu mi se cere.",
            "Îmi pasă sincer de bunăstarea celor din jur.",
        ],
    },
    {
        "title": "🔹 Big Five – Nevrotism",
        "instruction": "Cât de bine te descriu afirmațiile de mai jos?",
        "scale": SCALE_5_AGREE,
        "key_prefix": "neuro",
        "questions": [
            "Mă simt frecvent neliniștit(ă) sau îngrijorat(ă).",
            "Reacționez puternic la stres.",
            "Am tendința de a analiza în exces greșelile mele.",
            "Mă simt ușor copleșit(ă) în fața incertitudinii.",
        ],
    },
    {
        "title": "🔹 Trăsături interpersonale",
        "instruction": "Cât de bine te descriu afirmațiile de mai jos?",
        "scale": SCALE_5_AGREE,
        "key_prefix": "dark",
        "question_keys": [f"dark_{index}" for index in range(12)] + [f"state_stress_pre_{index + 1}" for index in range(7)],
        "question_scales": [SCALE_5_AGREE] * 12 + [STATE_STRESS_SCALE] * 7,
        "question_option_labels": [SCALE_5_AGREE] * 12 + [["1 - Deloc", "2 - Puțin", "3 - Moderat", "4 - Destul de mult", "5 - Foarte mult"]] * 7,
        "question_instructions": {
            12: "Chiar acum, în acest moment, în ce măsură te simți în felul următor?\n\n1 = Deloc\n2 = Puțin\n3 = Moderat\n4 = Destul de mult\n5 = Foarte mult",
        },
        "questions": [
            "Cred că e mai important să fii eficient decât moral.",
            "Oamenii se lasă manipulați ușor dacă le cunoști slăbiciunile.",
            "Îmi place să influențez deciziile altora subtil, în favoarea mea.",
            "În relațiile sociale, controlez informațiile pe care le ofer.",
            "Merit să fiu admirat(ă) pentru cine sunt.",
            "Sunt o persoană specială, diferită de ceilalți.",
            "Îmi place să mi se recunoască valoarea, chiar dacă trebuie să insist.",
            "Cred că am calități care mă fac superior/oară majorității.",
            "Nu simt vină pentru lucruri făcute sub impuls.",
            "Îmi este greu să simt remușcări chiar dacă știu că am greșit.",
            "Trec rapid peste suferința altora – viața merge înainte.",
            "Îmi plac riscurile și trăirile intense, chiar dacă implică reguli încălcate.",
            "Copleșit(ă) de ceea ce am de gestionat",
            "Incapabil(ă) să controlez lucrurile care contează pentru mine",
            "Nervos/nervoasă sau încordat(ă)",
            "Că evenimentele și responsabilitățile mă depășesc",
            "Sub presiunea timpului",
            "Că se așteaptă prea mult de la mine",
            "Aproape de epuizare fizică sau psihică",
        ],
    },
]

POST_SECTIONS = [
    {
        "title": "Capitolul 1",
        "instruction": """Următoarele afirmații se referă la felul în care te-ai simțit în timpul simulării financiare și imediat după finalizarea acesteia. Te rugăm să răspunzi în funcție de experiența ta din această sarcină, nu în funcție de starea ta obișnuită.

Scală de răspuns
1 = Deloc
2 = Puțin
3 = Moderat
4 = Mult
5 = Foarte mult""",
        "scale": ["1 - Deloc", "2 - Puțin", "3 - Moderat", "4 - Mult", "5 - Foarte mult"],
        "key_prefix": "post_stress",
        "question_keys": [f"state_stress_post_{index + 1}" for index in range(7)] + [f"post_stress_{index}" for index in range(25)],
        # Persist the legacy post-question numbers for existing items.  The
        # newly inserted stress block is displayed first but stored after the
        # original 35 questions, avoiding conflicts with the legacy UNIQUE
        # (session_id, question_number) constraint.
        "persisted_question_numbers": list(range(36, 43)) + list(range(1, 26)),
        "question_scales": [STATE_STRESS_SCALE] * 7 + [["1 - Deloc", "2 - Puțin", "3 - Moderat", "4 - Mult", "5 - Foarte mult"]] * 25,
        "question_option_labels": [["1 - Deloc", "2 - Puțin", "3 - Moderat", "4 - Destul de mult", "5 - Foarte mult"]] * 7 + [["1 - Deloc", "2 - Puțin", "3 - Moderat", "4 - Mult", "5 - Foarte mult"]] * 25,
        "question_instructions": {
            0: "Chiar acum, în acest moment, în ce măsură te simți în felul următor?\n\n1 = Deloc\n2 = Puțin\n3 = Moderat\n4 = Destul de mult\n5 = Foarte mult",
        },
        "questions": [
            "Copleșit(ă) de ceea ce am de gestionat",
            "Incapabil(ă) să controlez lucrurile care contează pentru mine",
            "Nervos/nervoasă sau încordat(ă)",
            "Că evenimentele și responsabilitățile mă depășesc",
            "Sub presiunea timpului",
            "Că se așteaptă prea mult de la mine",
            "Aproape de epuizare fizică sau psihică",
            "În timpul experimentului, m-am simțit copleșit(ă) de informațiile și deciziile pe care trebuia să le gestionez.",
            "În timpul experimentului, am avut impresia că nu pot controla complet evoluția situației financiare prezentate.",
            "În timpul experimentului, m-am simțit nervos/oasă sau încordat(ă).",
            "În timpul experimentului, am simțit că evenimentele lunare și responsabilitățile financiare mă depășesc.",
            "În timpul experimentului, am simțit presiune din cauza timpului sau a numărului de decizii de luat.",
            "În timpul experimentului, am avut impresia că situația financiară prezentată cere mai mult decât puteam gestiona confortabil.",
            "La finalul experimentului, m-am simțit aproape de epuizare psihică sau mentală.",
            "După experiment, m-am simțit tensionat(ă) sau iritabil(ă).",
            "După experiment, m-am simțit anxios/anxioasă sau cu o stare de apăsare interioară.",
            "După experiment, am simțit o stare de descurajare.",
            "După experiment, m-am simțit vinovat(ă) sau auto-critic(ă) în legătură cu unele decizii luate.",
            "După experiment, m-am simțit neliniștit(ă), ca și cum îmi era greu să mă relaxez.",
            "După experiment, m-am simțit mai retras(ă) sau mai puțin disponibil(ă) pentru interacțiune decât de obicei.",
            "După experiment, m-am simțit energic(ă) și activ(ă).",
            "După experiment, m-am simțit calm(ă) și echilibrat(ă) emoțional.",
            "După experiment, m-am simțit mulțumit(ă) de felul în care am gestionat sarcina.",
            "În timpul experimentului, am simțit că am control asupra deciziilor mele.",
            "În timpul experimentului, m-am simțit motivat(ă) să continui și să finalizez sarcina.",
            "În timpul experimentului, au existat momente în care m-am simțit implicat(ă).",
            "În timpul sau imediat după experiment, mi-a fost greu să mă concentrez.",
            "În timpul experimentului, mi-a fost greu să finalizez unele decizii din cauza tensiunii sau oboselii.",
            "După experiment, am simțit oboseală mentală accentuată.",
            "După experiment, am resimțit tensiune musculară, durere de cap sau disconfort fizic ușor.",
            "După experiment, am simțit nevoia să iau o pauză înainte de a continua cu altă activitate.",
            "În timpul experimentului, am evitat să analizez în detaliu unele informații deoarece mi s-au părut prea solicitante.",
        ],
    },
    {
        "title": "Capitolul 2",
        "instruction": """Scală pentru percepția asupra experimentului:
1 = Complet în dezacord
2 = Mai degrabă în dezacord
3 = Nici de acord, nici în dezacord
4 = Mai degrabă de acord
5 = Complet de acord""",
        "scale": [
            "1 - Complet în dezacord",
            "2 - Mai degrabă în dezacord",
            "3 - Nici de acord, nici în dezacord",
            "4 - Mai degrabă de acord",
            "5 - Complet de acord",
        ],
        "key_prefix": "post_perception",
        "question_keys": [f"post_perception_{index}" for index in range(10)] + ["score_check", "score_perceived", "mcheck_avoid"],
        "persisted_question_numbers": list(range(26, 36)) + [43, 44, 45],
        "question_scales": [[
            "1 - Complet în dezacord",
            "2 - Mai degrabă în dezacord",
            "3 - Nici de acord, nici în dezacord",
            "4 - Mai degrabă de acord",
            "5 - Complet de acord",
        ]] * 10 + [SCORE_CHECK_SCALE, SCORE_PERCEIVED_SCALE, MCHECK_AVOID_SCALE],
        "question_option_labels": [[
            "1 - Complet în dezacord",
            "2 - Mai degrabă în dezacord",
            "3 - Nici de acord, nici în dezacord",
            "4 - Mai degrabă de acord",
            "5 - Complet de acord",
        ]] * 10 + [
            ["1 - la cât am câștigat", "", "", "4 - în egală măsură", "", "", "7 - la cât am pierdut"],
            ["1 - puncte câștigate", "2 - puncte pierdute", "3 - nu îmi amintesc"],
            ["1 - dezacord total", "2 - dezacord", "3 - nici acord, nici dezacord", "4 - acord", "5 - acord total"],
        ],
        "question_instructions": {
            10: "Răspunde la următoarele întrebări despre felul în care ți-a fost prezentat scorul lunar.",
        },
        "questions": [
            "Experimentul mi s-a părut realist.",
            "Deciziile lunare mi s-au părut credibile pentru o situație financiară reală.",
            "Informațiile afișate în fiecare lună au fost clare.",
            "Mi-a fost ușor să înțeleg efectul deciziilor mele asupra creditului.",
            "Mi-a fost ușor să înțeleg efectul deciziilor mele asupra overdraftului.",
            "Sarcina a fost dificilă din punct de vedere financiar.",
            "Sarcina a fost dificilă din punct de vedere emoțional.",
            "Am simțit presiune când trebuia să aleg suma de rambursare.",
            "Am avut impresia că deciziile mele aveau consecințe importante.",
            "Am tratat experimentul ca pe o situație serioasă.",
            "Când te uitai la scorul lunar, la ce te gândeai în principal?",
            "În fiecare lună, scorul tău ți-a fost prezentat ca:",
            "În timpul sarcinii m-am concentrat mai mult pe a evita pierderile decât pe a obține câștiguri.",
        ],
    },
]
