"""Monthly simulation decision page."""

import re

from sim_app.application.progression import redirect_before_simulation
from sim_app.domain.simulation import compute_month_preview
from sim_app.session.streamlit_service import submit_month_decision
from sim_app.session.streamlit_state import read_participant_state
from sim_app.ui.formatting import display_euro, display_number, display_value_table


def render_simulation_page(ctx):
    st = ctx.st
    t = ctx.t
    participant_state = read_participant_state(st.session_state)

    redirect_page = redirect_before_simulation(participant_state.month)
    if redirect_page:
        ctx.goto(redirect_page)

    ctx.scroll_top_anchor()

    month = participant_state.month
    loan = participant_state.loan
    overdraft = participant_state.overdraft

    data = ctx.get_month(month)
    preview = compute_month_preview(
        month,
        data,
        loan,
        overdraft,
        monthly_results=participant_state.monthly_results,
    )
    income_total = preview["income_total"]
    expenses_total = preview["expenses_total"]
    opening_balance = preview["opening_balance"]
    loan_obligation = preview["loan_obligation"]
    no_loan_due = preview["no_loan_due"]
    credit_interest = preview["credit_interest"]
    overdraft_interest = preview["overdraft_interest"]
    liquidity_after_charges = preview["liquidity_after_charges"]
    blocked = preview["blocked"]

    st.title(t("simulation.month_title", month=month))

    with st.expander(t("simulation.narrative_expander"), expanded=True):
        narrative = re.sub(r'^(\S+)', r'<strong>\1</strong>', ctx.get_localized_narrative(month))
        st.markdown(
            f'<div style="text-align: justify">{narrative}</div>',
            unsafe_allow_html=True,
        )
    ctx.auto_open_context_narrativ(t("simulation.narrative_expander"))

    with st.expander(t("simulation.budget_expander")):
        st.markdown(t("simulation.income_header"))
        st.table(display_value_table(data["income"], ctx.get_category_label, t("table.category"), t("table.value")))
        st.write(t("simulation.income_total", value=display_number(income_total)))

        st.markdown(t("simulation.expenses_header"))
        st.table(display_value_table(data["expenses"], ctx.get_category_label, t("table.category"), t("table.value")))
        st.write(t("simulation.expenses_total", value=display_number(expenses_total)))

    opening_balance_html = (
        f'<div class="decision-row positive"><strong>{t("simulation.opening_balance")}:</strong> {display_euro(opening_balance)}</div>'
        if month == 1
        else ""
    )

    st.markdown(
        f"""
<div class="decision-card">
<div class="decision-card-title">{t("simulation.decision_title")}</div>
{opening_balance_html}
<div class="decision-row positive"><strong>{t("simulation.income_total_label")}:</strong> {display_euro(income_total)}</div>
<div class="decision-row risk"><strong>{t("simulation.expenses_total_label")}:</strong> {display_euro(expenses_total)}</div>
<div class="decision-row risk"><strong>{t("simulation.overdraft_interest_label")}:</strong> {display_euro(overdraft_interest)} | <strong>{t("simulation.credit_interest_label")}:</strong> {display_euro(credit_interest)}</div>
<div class="decision-row risk"><strong>{t("simulation.remaining_credit_label")}:</strong> {display_euro(loan.balance)} | <strong>{t("simulation.used_overdraft_label")}:</strong> {display_euro(overdraft.balance)}</div>
<div class="decision-row positive"><strong>{t("simulation.available_before_payment_label")}:</strong> {display_euro(liquidity_after_charges)}</div>
<div class="decision-row formula">{t("simulation.available_before_payment_formula")}</div>
<div class="decision-row primary"><strong>{t("simulation.contract_rate_label")}:</strong> {display_euro(loan_obligation)}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    if blocked:
        st.error(t("simulation.blocked_error"))

    payment = None
    if no_loan_due:
        st.info(t("simulation.no_payment_due_notice"))
    else:
        st.markdown(f'<div class="payment-label">{t("simulation.payment_label")}</div>', unsafe_allow_html=True)
        payment = st.number_input(
            t("simulation.payment_label"),
            min_value=0.0,
            step=1.0,
            value=None,
            format="%g",
            placeholder=t("simulation.payment_placeholder"),
            key=f"payment_{month}",
            label_visibility="collapsed",
        )
        ctx.attach_payment_keyboard_bridge()
        st.markdown(
            f"""
<div class="auth-info payment-note">
  <span class="auth-info-icon">i</span>
  <span>{t("simulation.payment_note")}</span>
</div>
""",
            unsafe_allow_html=True,
        )
    st.markdown('<div class="payment-button-gap"></div>', unsafe_allow_html=True)

    button_label = t("simulation.continue_month_button") if no_loan_due else t("simulation.confirm_button")
    if st.button(button_label, type="primary"):
        if not no_loan_due and payment is None:
            st.warning(t("simulation.payment_validation_warning"))
            st.stop()

        submit_month_decision(
            st,
            ctx.experiment_service,
            payment=payment,
            translate=t,
        )


__all__ = [
    "render_simulation_page",
]

