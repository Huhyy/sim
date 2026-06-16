"""Authenticated account menu component."""

from sim_app.ui.components.admin_navigation import render_admin_page_navigator
from sim_app.ui.components.language import render_language_buttons


def render_account_menu(ctx):
    st = ctx.st
    t = ctx.t
    email = st.user.get("email") or st.user.get("name") or t("auth.account_fallback")
    with st.container(key="account_menu"):
        with st.expander(email):
            st.markdown(f'<div class="account-language-label">{t("auth.language_label")}</div>', unsafe_allow_html=True)
            render_language_buttons(st, t, ctx.ensure_language, ctx.get_language, ctx.set_language, "account_lang")
            if ctx.is_admin_user():
                if st.button(t("auth.admin_page"), key="account_admin", use_container_width=True):
                    st.session_state.admin_return_page = st.session_state.get("page", "home")
                    ctx.goto("admin")
                render_admin_page_navigator(ctx)
            if st.button(t("auth.logout"), icon=":material/logout:", key="account_logout", use_container_width=True):
                st.logout()


__all__ = [
    "render_account_menu",
]

