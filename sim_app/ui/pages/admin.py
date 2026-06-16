"""Admin page."""

from sim_app.ui.components.admin_participants import render_admin_participants


def render_admin_page(ctx):
    st = ctx.st
    t = ctx.t
    if not ctx.is_admin_user():
        ctx.goto("home")
    ctx.scroll_top_anchor()
    admin_return_page = st.session_state.get("admin_return_page", "home")
    if admin_return_page == "admin":
        admin_return_page = "home"
    st.title(t("admin.title"))
    st.markdown(t("admin.body"))
    condition_options = ctx.condition_options()
    selected_condition = st.selectbox(
        t("admin.condition_label"),
        options=condition_options,
        format_func=lambda value: t(f"admin.conditions.{value}"),
        key="admin_experimental_condition",
    )
    st.caption(t(f"admin.condition_descriptions.{selected_condition}"))
    if st.button(t("admin.start_session"), type="primary"):
        created = ctx.create_admin_study_session(ctx.current_user_email(), selected_condition)
        st.session_state.admin_last_created_session = created
        st.success(t("admin.created_success"))

    st.caption(t("admin.participants_refresh_note"))
    if hasattr(st, "fragment"):
        @st.fragment(run_every="10s")
        def render_auto_refreshed_sessions():
            render_session_list(ctx, condition_options, admin_return_page)

        render_auto_refreshed_sessions()
    else:
        render_session_list(ctx, condition_options, admin_return_page)

    if st.button(t("admin.back_home")):
        ctx.goto(admin_return_page)


def render_session_list(ctx, condition_options, admin_return_page):
    st = ctx.st
    t = ctx.t
    active_sessions = ctx.list_admin_study_sessions(ctx.current_user_email())
    latest_created = st.session_state.get("admin_last_created_session")
    active_session_ids = {row.get("id") for row in active_sessions}
    if latest_created and latest_created.get("id") in active_session_ids:
        st.metric(t("admin.code_label"), latest_created["session_code"])
    elif latest_created:
        st.session_state.admin_last_created_session = None
    if active_sessions:
        st.markdown(f"### {t('admin.active_sessions')}")
        st.caption(t("admin.sessions_note"))
        header_cols = st.columns([2, 2, 2, 3, 1])
        header_cols[0].markdown(f"**{t('admin.code_label')}**")
        header_cols[1].markdown(f"**{t('admin.condition_label')}**")
        header_cols[2].markdown(f"**{t('admin.status')}**")
        header_cols[3].markdown(f"**{t('admin.created_at')}**")
        for row in active_sessions:
            code = row.get("session_code")
            status = row.get("status")
            created_at = row.get("created_at")
            condition = row.get("experimental_condition", "C1")
            condition_label = t(f"admin.conditions.{condition}") if condition in condition_options else condition
            cols = st.columns([2, 2, 2, 3, 1])
            cols[0].markdown(f"**{code}**")
            cols[1].write(condition_label)
            cols[2].write(status)
            cols[3].write(created_at)
            if cols[4].button(" ", icon=":material/delete:", help=t("admin.cancel_session"), key=f"cancel_session_{row.get('id')}"):
                cancelled = ctx.cancel_admin_study_session(row.get("id"), ctx.current_user_email())
                if cancelled:
                    if (st.session_state.get("admin_last_created_session") or {}).get("id") == row.get("id"):
                        st.session_state.admin_last_created_session = None
                    if st.session_state.get("study_session_id") == row.get("id"):
                        st.session_state.study_session_id = None
                        st.session_state.study_session_code = None
                        st.session_state.experimental_condition = "C1"
                        st.session_state.score_frame = "gain_frame"
                        st.session_state.monthly_score_feedback = "displayed"
                    st.success(t("admin.cancelled_success", code=code))
                    st.rerun()
                else:
                    st.error(t("admin.cancelled_error"))
            participants = ctx.list_participant_sessions_for_study_session(row.get("id"), code)
            render_admin_participants(ctx, participants)


__all__ = [
    "render_admin_page",
    "render_session_list",
]

