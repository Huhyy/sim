"""Admin-only page navigation controls."""


def build_admin_page_flow(ctx):
    pre_count = len(getattr(ctx, "pre_sections_ro", None) or [])
    post_count = len(getattr(ctx, "post_sections_ro", None) or [])

    return (
        ["enter_session_code", "home", "consent", "demographics"]
        + [f"pre_question_{index}" for index in range(pre_count)]
        + ["instructions", "profile", "simulation"]
        + [f"post_question_{index}" for index in range(post_count)]
        + ["final_score", "done"]
    )


def page_display_name(page, ctx):
    if page.startswith("pre_question_"):
        count = len(getattr(ctx, "pre_sections_ro", None) or [])
        index = int(page.rsplit("_", 1)[1]) + 1
        return f"Pre questionnaire {index}/{count}"
    if page.startswith("post_question_"):
        count = len(getattr(ctx, "post_sections_ro", None) or [])
        index = int(page.rsplit("_", 1)[1]) + 1
        return f"Post questionnaire {index}/{count}"

    return {
        "enter_session_code": "Session code",
        "home": "Home",
        "consent": "Consent",
        "consent_declined": "Consent declined",
        "demographics": "Demographics",
        "instructions": "Instructions",
        "profile": "Profile",
        "simulation": "Simulation",
        "month_feedback": "Month feedback",
        "final_score": "Final score",
        "done": "Done",
        "admin": "Admin",
        "already_completed": "Already completed",
    }.get(page, page)


def adjacent_admin_pages(current_page, flow):
    if current_page not in flow:
        return None, None

    index = flow.index(current_page)
    previous_page = flow[index - 1] if index > 0 else None
    next_page = flow[index + 1] if index + 1 < len(flow) else None
    return previous_page, next_page


def render_admin_page_navigator(ctx):
    st = ctx.st
    t = ctx.t
    flow = build_admin_page_flow(ctx)
    current_page = st.session_state.get("page", "home")
    previous_page, next_page = adjacent_admin_pages(current_page, flow)

    st.markdown(f'<div class="account-language-label">{t("auth.admin_navigator")}</div>', unsafe_allow_html=True)
    st.caption(t("auth.admin_navigator_current", page=page_display_name(current_page, ctx)))

    cols = st.columns(2)
    if cols[0].button(
        t("auth.admin_previous"),
        icon=":material/arrow_back:",
        key="admin_page_previous",
        disabled=previous_page is None,
        use_container_width=True,
    ):
        ctx.goto(previous_page)

    if cols[1].button(
        t("auth.admin_next"),
        icon=":material/arrow_forward:",
        key="admin_page_next",
        disabled=next_page is None,
        use_container_width=True,
    ):
        ctx.goto(next_page)


__all__ = [
    "adjacent_admin_pages",
    "build_admin_page_flow",
    "page_display_name",
    "render_admin_page_navigator",
]
