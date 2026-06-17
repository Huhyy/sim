"""Admin launcher page."""


def render_admin_page(ctx):
    st = ctx.st
    t = ctx.t
    if not ctx.is_admin_user():
        ctx.goto("home")
    ctx.scroll_top_anchor()
    admin_return_page = st.session_state.get("admin_return_page", "home")
    if admin_return_page in ("admin", "admin_sessions"):
        admin_return_page = "home"
    st.title(t("admin.title"))
    if st.button(t("admin.start_session"), type="primary", key="admin_start_session_launcher"):
        ctx.goto("admin_sessions")
    if st.button(t("admin.back_home"), key="admin_back_home_launcher"):
        ctx.goto(admin_return_page)


__all__ = [
    "render_admin_page",
]

