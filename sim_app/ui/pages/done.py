"""Completion page."""

from sim_app.ui.formatting import display_euro, display_number
from sim_app.ui.pages.final_score import render_performance_bonus_summary


def render_done_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()
    st.session_state.final_score = ctx.compute_final_score()
    breakdown = ctx.get_final_score_breakdown()
    st.session_state.answers["financial_summary"] = breakdown

    if not st.session_state.get("saved"):
        try:
            ctx.finalize_participant(
                st.session_state.session_id,
                st.session_state.answers,
                st.session_state.final_score,
                monthly_results=[
                    ctx.normalize_month_result_score(result)
                    for result in st.session_state.get("monthly_results", [])
                ],
                summary={
                    **breakdown,
                    "scenario_version": ctx.scenario_version,
                },
                pre_sections=ctx.pre_sections_ro,
                post_sections=ctx.post_sections_ro,
            )
            st.session_state.saved = True
        except Exception as e:
            st.error(t("done.save_error", error=e))

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

{t("done.registered_text")}

{t("done.contact")}: coita.iflorina@gmail.com
"""
    )


__all__ = [
    "render_done_page",
]

