"""Monthly feedback page."""

from sim_app.application.commands import normalize_pending_month_feedback
from sim_app.application.progression import redirect_before_month_feedback
from sim_app.session.streamlit_service import acknowledge_month_feedback
from sim_app.session.streamlit_state import apply_participant_state, read_participant_state
from sim_app.ui.formatting import display_euro, display_number


def render_month_feedback_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()

    participant_state = read_participant_state(st.session_state)
    result = participant_state.pending_month_result
    redirect_page = redirect_before_month_feedback(bool(result))
    if redirect_page:
        ctx.goto(redirect_page)
    participant_state = normalize_pending_month_feedback(participant_state)
    apply_participant_state(st.session_state, participant_state)
    result = participant_state.pending_month_result

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

    continue_label = (
        t("simulation.continue_next_page_button")
        if int(result.get("month", 0)) >= 24
        else t("simulation.continue_month_button")
    )
    if st.button(continue_label, type="primary"):
        acknowledge_month_feedback(st, ctx.experiment_service)


__all__ = [
    "render_month_feedback_page",
]
