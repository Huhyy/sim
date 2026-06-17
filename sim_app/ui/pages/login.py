"""Login page."""

from sim_app.ui.styles import AUTH_CARD_CSS, apply_css


def render_login_page(ctx):
    st = ctx.st
    t = ctx.t
    apply_css(st, AUTH_CARD_CSS)

    with st.container(key="auth_card"):
        st.markdown(
            f"""
<div class="auth-brand">
  <span class="auth-brand-mark">E</span>
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


__all__ = [
    "render_login_page",
]

