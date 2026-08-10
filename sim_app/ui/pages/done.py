"""Completion page."""

from html import escape

from sim_app.prolific.identity import completion_redirect_url, configured_completion_code
from sim_app.session.query_params import get_query_param
from sim_app.session.streamlit_service import finalize_experiment
from sim_app.session.streamlit_state import apply_participant_state, read_participant_state
from sim_app.ui.formatting import display_euro, display_number
from sim_app.ui.pages.final_score import render_performance_bonus_summary


def render_done_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()
    participant_state = read_participant_state(st.session_state)
    if not participant_state.saved:
        participant_state = finalize_experiment(
            st,
            ctx.experiment_service,
            account_key=ctx.current_account_key(),
            pre_sections=ctx.pre_sections_ro,
            post_sections=ctx.post_sections_ro,
        )
        apply_participant_state(st.session_state, participant_state)
    breakdown = participant_state.final_score_breakdown

    st.title(t("done.title"))
    st.metric(t("done.score_metric"), f"{display_number(st.session_state.final_score)} / 100")
    participant_code = breakdown.get("participant_code") or st.session_state.get("participant_code")
    if participant_code:
        st.markdown(
            f"""
<div style="margin: 0.6rem 0 1rem; padding: 0.85rem 1rem; border: 1px solid #e1dac8; border-radius: 0.75rem; background: #fffaf0;">
  <div style="color: #586564; font-size: 0.78rem; font-weight: 700;">{t("done.participant_code_label")}</div>
  <div style="color: #172b29; font-size: 1.55rem; font-weight: 800; letter-spacing: 0.02em;">{participant_code}</div>
</div>
""",
            unsafe_allow_html=True,
        )
    render_performance_bonus_summary(st, t, breakdown)
    st.markdown(
        f"""
{t("done.remaining_credit")}: **{display_euro(st.session_state.loan.balance)}**

{t("done.remaining_overdraft")}: **{display_euro(st.session_state.overdraft.balance)}**

{t("done.registered_text") if st.session_state.get("saved") else t("done.save_pending")}

{t("done.contact")}: coita.iflorina@gmail.com
"""
    )

    completion_code = configured_completion_code() or st.session_state.get("prolific_completion_code")
    redirect_url = completion_redirect_url(completion_code) or st.session_state.get("prolific_completion_url")
    prolific_session = bool(
        st.session_state.get("prolific_mode")
        or st.session_state.get("prolific_pid")
        or breakdown.get("prolific_pid")
        or get_query_param("PROLIFIC_PID")
    )
    if prolific_session and st.session_state.get("saved") and redirect_url:
        st.session_state.prolific_completion_code = completion_code
        st.session_state.prolific_completion_url = redirect_url
        st.success(t("prolific.completion_ready"))
        st.markdown(f"**{t('prolific.completion_code_label')}**")
        st.code(str(completion_code or ""), language=None)
        st.markdown(f"**{t('prolific.completion_link_label')}**")
        st.markdown(
            f"""
<a href="{escape(redirect_url, quote=True)}" target="_blank" rel="noopener noreferrer">
  {escape(redirect_url)}
</a>
""",
            unsafe_allow_html=True,
        )
    elif prolific_session and st.session_state.get("saved"):
        st.error(t("prolific.completion_not_configured"))


__all__ = [
    "render_done_page",
]

