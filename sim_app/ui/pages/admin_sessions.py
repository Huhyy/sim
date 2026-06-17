"""Admin study-session management page."""

from html import escape

from sim_app.ui.components.admin_participants import render_admin_participants


ADMIN_SESSIONS_CSS = """
<style>
.admin-session-summary {
    margin: 0.25rem 0 1rem;
    padding: 0.9rem 1rem;
    border: 1px solid #e1dac8;
    border-radius: 0.5rem;
    background: rgba(255, 250, 240, 0.72);
}
.admin-session-summary-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.8rem;
}
.admin-session-label {
    color: #6f7774;
    font: 700 0.72rem/1.2 'Manrope', sans-serif;
}
.admin-session-value {
    margin-top: 0.18rem;
    color: #172b29;
    font: 800 0.92rem/1.25 'Manrope', sans-serif;
    overflow-wrap: anywhere;
}
div[data-testid="stTabs"] button[role="tab"] {
    border: 1px solid #d8d0bf;
    border-bottom: 0;
    border-radius: 0.65rem 0.65rem 0 0;
    background: #eee6d6;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    background: #fffaf0;
}
@media (max-width: 760px) {
    .admin-session-summary-grid {
        grid-template-columns: 1fr;
    }
}
</style>
"""


def render_admin_sessions_page(ctx):
    st = ctx.st
    t = ctx.t
    if not ctx.is_admin_user():
        ctx.goto("home")
    ctx.scroll_top_anchor()
    st.markdown(ADMIN_SESSIONS_CSS, unsafe_allow_html=True)
    st.title(t("admin.sessions_title"))

    cols = st.columns([1, 1, 4])
    if cols[0].button(t("admin.create_session"), type="primary", key="admin_create_session"):
        _open_create_session_dialog(ctx)
    if cols[1].button(t("admin.back_admin"), key="admin_sessions_back_admin"):
        ctx.goto("admin")

    st.caption(t("admin.participants_refresh_note"))
    if hasattr(st, "fragment"):
        @st.fragment(run_every="10s")
        def render_auto_refreshed_sessions():
            render_session_tabs(ctx)

        render_auto_refreshed_sessions()
    else:
        render_session_tabs(ctx)


def _open_create_session_dialog(ctx):
    st = ctx.st
    if hasattr(st, "dialog"):
        _render_create_session_dialog(ctx)
        return

    st.session_state.admin_create_session_inline = True
    st.rerun()


def _render_create_session_dialog(ctx):
    st = ctx.st
    t = ctx.t

    @st.dialog(t("admin.create_session_title"))
    def create_session_dialog():
        _render_create_session_form(ctx, in_dialog=True)

    create_session_dialog()


def _render_create_session_form(ctx, in_dialog=False):
    st = ctx.st
    t = ctx.t
    condition_options = ctx.condition_options()
    selected_condition = st.selectbox(
        t("admin.condition_label"),
        options=condition_options,
        format_func=lambda value: t(f"admin.conditions.{value}"),
        key="admin_create_experimental_condition",
    )
    st.caption(t(f"admin.condition_descriptions.{selected_condition}"))
    form_cols = st.columns([1, 1, 2])
    if form_cols[0].button(t("admin.create_session"), type="primary", key=f"admin_create_session_confirm_{in_dialog}"):
        created = ctx.create_admin_study_session(ctx.current_user_email(), selected_condition)
        st.session_state.admin_last_created_session = created
        st.session_state.admin_create_session_inline = False
        st.success(t("admin.created_success"))
        st.rerun()
    if form_cols[1].button(t("admin.cancel_create"), key=f"admin_create_session_cancel_{in_dialog}"):
        st.session_state.admin_create_session_inline = False
        st.rerun()


def render_session_tabs(ctx):
    st = ctx.st
    t = ctx.t
    condition_options = ctx.condition_options()
    active_sessions = ctx.list_admin_study_sessions(ctx.current_user_email())
    _clear_missing_latest_session(st, active_sessions)

    if st.session_state.get("admin_create_session_inline"):
        with st.expander(t("admin.create_session_title"), expanded=True):
            _render_create_session_form(ctx)

    if not active_sessions:
        st.info(t("admin.no_sessions"))
        return

    labels = [_session_tab_label(row) for row in active_sessions]
    tabs = st.tabs(labels)
    for tab, row in zip(tabs, active_sessions):
        with tab:
            render_session_tab(ctx, row, condition_options)


def render_session_tab(ctx, row, condition_options):
    st = ctx.st
    t = ctx.t
    code = row.get("session_code")
    condition = row.get("experimental_condition", "C1")
    condition_label = t(f"admin.conditions.{condition}") if condition in condition_options else condition

    st.markdown(
        f"""
<div class="admin-session-summary">
  <div class="admin-session-summary-grid">
    <div>
      <div class="admin-session-label">{escape(t("admin.code_label"))}</div>
      <div class="admin-session-value">{escape(str(code or "-"))}</div>
    </div>
    <div>
      <div class="admin-session-label">{escape(t("admin.condition_label"))}</div>
      <div class="admin-session-value">{escape(str(condition_label))}</div>
    </div>
    <div>
      <div class="admin-session-label">{escape(t("admin.status"))}</div>
      <div class="admin-session-value">{escape(str(row.get("status") or "-"))}</div>
    </div>
    <div>
      <div class="admin-session-label">{escape(t("admin.created_at"))}</div>
      <div class="admin-session-value">{escape(str(row.get("created_at") or "-"))}</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    if st.button(" ", icon=":material/delete:", help=t("admin.cancel_session"), key=f"cancel_session_{row.get('id')}"):
        _cancel_session(ctx, row)
    participants = ctx.list_participant_sessions_for_study_session(row.get("id"), code)
    render_admin_participants(ctx, participants)


def _cancel_session(ctx, row):
    st = ctx.st
    t = ctx.t
    code = row.get("session_code")
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


def _clear_missing_latest_session(st, active_sessions):
    latest_created = st.session_state.get("admin_last_created_session")
    if not latest_created:
        return
    active_session_ids = {row.get("id") for row in active_sessions}
    if latest_created.get("id") not in active_session_ids:
        st.session_state.admin_last_created_session = None


def _session_tab_label(row):
    code = row.get("session_code") or "-"
    condition = row.get("experimental_condition") or "C1"
    return f"{code} - {condition}"


__all__ = [
    "render_admin_sessions_page",
    "render_session_tab",
    "render_session_tabs",
]
