"""Monthly feedback page."""

from sim_app.ui.formatting import display_euro, display_number


def render_month_feedback_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()

    result = st.session_state.get("pending_month_result")
    if not result:
        ctx.goto("simulation")
    result = ctx.normalize_month_result_score(result)
    st.session_state.pending_month_result = result

    month = result["month"]
    st.title(t("simulation.feedback_title", month=month))

    st.markdown(t("simulation.decision_result_heading"))
    st.write(t("simulation.payment_entered", value=display_euro(result["payment_input"])))
    st.write(t("simulation.payment_accepted", value=display_euro(result["accepted_payment"])))
    st.write(t("simulation.cash_after_payment", value=display_euro(result["cash_final"])))
    st.write(t("simulation.credit_remaining", value=display_euro(result["credit_final"])))
    st.write(t("simulation.overdraft_final", value=display_euro(result["overdraft_final"])))
    st.write(t("simulation.credit_interest_month", value=display_euro(result["credit_interest"])))
    st.write(t("simulation.overdraft_interest_month", value=display_euro(result["overdraft_interest"])))
    if result["penalties"] > 0:
        st.write(t("simulation.penalties_month", value=display_euro(result["penalties"])))

    if st.session_state.get("monthly_score_feedback", "displayed") == "displayed":
        st.markdown(t("simulation.monthly_score_heading"))
        score_cols = st.columns(3)
        score_cols[0].metric(t("simulation.score_credit_metric"), f"{display_number(result['score_repayment'])} / 40")
        score_cols[1].metric(t("simulation.score_liquidity_metric"), f"{display_number(result['score_liquidity'])} / 30")
        score_cols[2].metric(t("simulation.score_overdraft_metric"), f"{display_number(result['score_overdraft'])} / 30")
        if st.session_state.get("score_frame") == "loss_frame":
            monthly_loss = max(0.0, 100.0 - float(result["monthly_score"]))
            st.metric(t("simulation.monthly_score_lost_metric"), f"{display_number(monthly_loss)} / 100")
        else:
            st.metric(t("simulation.monthly_score_metric"), f"{display_number(result['monthly_score'])} / 100")

    if result["pre_credit_impossible"]:
        st.error(result["feedback_message"])
    elif result["payment_valid"]:
        st.success(result["feedback_message"])
    else:
        st.warning(result["feedback_message"])

    if st.button(t("simulation.continue_month_button"), type="primary"):
        st.session_state.loan.balance = result["credit_final"]
        st.session_state.overdraft.balance = result["overdraft_final"]
        st.session_state.total_score += result["monthly_score"]
        st.session_state.monthly_points += result["monthly_score"]
        st.session_state.accumulated_costs += result["costs_this_month"]
        st.session_state.monthly_results.append(result)
        if int(result.get("month", 0)) >= 24:
            try:
                ctx.save_month_results(
                    st.session_state.session_id,
                    [
                        ctx.normalize_month_result_score(month_result)
                        for month_result in st.session_state.get("monthly_results", [])
                    ],
                    bonus_max_session=ctx.get_bonus_max_session(),
                    metadata={
                        "study_session_id": st.session_state.get("study_session_id"),
                        "study_session_code": st.session_state.get("study_session_code"),
                        "participant_code": st.session_state.get("participant_code"),
                    },
                )
                st.session_state.month_results_last_save = {
                    "ok": True,
                    "session_id": st.session_state.session_id,
                    "months": len(st.session_state.get("monthly_results", [])),
                }
            except Exception as e:
                st.session_state.month_results_last_save = {
                    "ok": False,
                    "session_id": st.session_state.session_id,
                    "error": str(e),
                }
        st.session_state.pending_month_result = None
        st.session_state.month += 1
        ctx.goto("simulation")


__all__ = [
    "render_month_feedback_page",
]
