"""Final score preview page."""

from sim_app.ui.formatting import display_euro, display_number


def render_final_score_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()

    st.session_state.final_score = ctx.compute_final_score()

    breakdown = ctx.get_final_score_breakdown()

    st.title(t("final_score.title"))
    st.markdown(t("final_score.intro"))
    st.markdown(t("final_score.heading"))
    st.markdown(
        f"""
<div class="final-score-card">
  <span class="final-score-label">{t("final_score.card_label")}</span>
  <span class="final-score-value">{display_number(breakdown["final_score"])} / 100</span>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
**{t("final_score.bonus_label")}:** {display_euro(breakdown["bonus_final"])}

{t("final_score.summary_heading")}

**{t("final_score.total_repaid")}:** {display_euro(breakdown["total_repaid"])}

**{t("final_score.remaining_credit")}:** {display_euro(breakdown["remaining_credit"])}

**{t("final_score.remaining_overdraft")}:** {display_euro(breakdown["remaining_overdraft"])}

**{t("final_score.interest_total")}:** {display_euro(breakdown["interest_total"])}
"""
    )
    st.info(t("final_score.info"))
    st.caption(t("final_score.caption"))

    if st.button(t("final_score.button"), type="primary"):
        st.session_state.scroll_to_top = True
        ctx.goto("done")


__all__ = [
    "render_final_score_page",
]

