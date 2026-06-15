"""CSS snippets and style application helpers."""

AUTH_CARD_CSS = """
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
"""

HOME_CSS = """
<style>
.home-title { text-align: center; font-size: 2rem; font-weight: 700; margin-bottom: 1rem; }
.home-body { text-align: justify; }
</style>
"""

CONSENT_CSS = """
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
"""

DEMOGRAPHICS_CSS = """
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
"""

INSTRUCTIONS_CSS = """
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
"""

PROFILE_CSS = """
<style>
.profile-text { text-align: justify; }
div[data-testid="stAppViewBlockContainer"] > div:first-child { padding-top: 0.5rem; }
h1:first-of-type { margin-top: 0; }
h3 { margin-top: 0.5rem; }
</style>
"""


def apply_css(st, css):
    st.markdown(css, unsafe_allow_html=True)


__all__ = [
    "AUTH_CARD_CSS",
    "CONSENT_CSS",
    "DEMOGRAPHICS_CSS",
    "HOME_CSS",
    "INSTRUCTIONS_CSS",
    "PROFILE_CSS",
    "apply_css",
]

