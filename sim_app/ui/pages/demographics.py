"""Demographic profile page."""

from sim_app.application.commands import submit_demographics
from sim_app.application.progression import required_page_before_demographics
from sim_app.session.streamlit_state import read_participant_state
from sim_app.ui.components.quiz import demographics_complete
from sim_app.ui.styles import DEMOGRAPHICS_CSS, apply_css


def _radio_index(st, key, options):
    current = st.session_state.answers.get(key)
    return options.index(current) if current in options else None


def render_demographics_page(ctx):
    st = ctx.st
    t = ctx.t
    ctx.scroll_top_anchor()
    required_page = required_page_before_demographics(read_participant_state(st.session_state))
    if required_page:
        ctx.goto(required_page)

    apply_css(st, DEMOGRAPHICS_CSS)

    st.markdown(
        f"""
<div class="demographics-page">
<h2>{t("demographics.title")}</h2>
<p>{t("demographics.intro")}</p>
</div>
""",
        unsafe_allow_html=True,
    )

    gender_options = t("demographics.options.gender")
    education_options = t("demographics.options.education")
    field_options = t("demographics.options.field")
    occupation_options = t("demographics.options.occupation")
    income_options = t("demographics.options.income")
    frequency_options = t("demographics.options.frequency")
    credit_options = t("demographics.options.credit")
    familiarity_options = t("demographics.options.familiarity")
    living_options = t("demographics.options.living")
    yes_no_options = t("demographics.options.yes_no")

    st.markdown(f"**{t('demographics.age_title')}**")
    st.caption(t("demographics.age_caption"))
    age = st.number_input(
        t("demographics.age_prompt"),
        min_value=18,
        max_value=75,
        step=1,
        value=st.session_state.answers.get("demo_age"),
        key="demo_age_input",
    )
    st.caption(t("demographics.age_note"))

    st.markdown(f"**{t('demographics.gender_title')}**")
    gender = st.radio(t("demographics.gender_prompt"), gender_options, index=_radio_index(st, "demo_gender", gender_options), key="demo_gender_input")

    st.markdown(f"**{t('demographics.education_title')}**")
    education = st.radio(t("demographics.education_prompt"), education_options, index=_radio_index(st, "demo_education", education_options), key="demo_education_input")

    st.markdown(f"**{t('demographics.field_title')}**")
    field = st.radio(t("demographics.field_prompt"), field_options, index=_radio_index(st, "demo_field", field_options), key="demo_field_input")

    st.markdown(f"**{t('demographics.occupation_title')}**")
    occupation = st.radio(t("demographics.occupation_prompt"), occupation_options, index=_radio_index(st, "demo_occupation", occupation_options), key="demo_occupation_input")

    st.markdown(f"**{t('demographics.income_title')}**")
    income = st.radio(t("demographics.income_prompt"), income_options, index=_radio_index(st, "demo_income", income_options), key="demo_income_input")

    st.markdown(f"**{t('demographics.financial_decisions_title')}**")
    financial_decisions = st.radio(t("demographics.financial_decisions_prompt"), frequency_options, index=_radio_index(st, "demo_financial_decisions", frequency_options), key="demo_financial_decisions_input")

    st.markdown(f"**{t('demographics.credit_experience_title')}**")
    credit_experience = st.radio(t("demographics.credit_experience_prompt"), credit_options, index=_radio_index(st, "demo_credit_experience", credit_options), key="demo_credit_experience_input")

    st.markdown(f"**{t('demographics.financial_familiarity_title')}**")
    financial_familiarity = st.radio(t("demographics.financial_familiarity_prompt"), familiarity_options, index=_radio_index(st, "demo_financial_familiarity", familiarity_options), key="demo_financial_familiarity_input")

    st.markdown(f"**{t('demographics.living_title')}**")
    living_situation = st.radio(t("demographics.living_prompt"), living_options, index=_radio_index(st, "demo_living_situation", living_options), key="demo_living_situation_input")

    st.markdown(f"**{t('demographics.responsibilities_title')}**")
    recurring_responsibilities = st.radio(t("demographics.responsibilities_prompt"), yes_no_options, index=_radio_index(st, "demo_recurring_responsibilities", yes_no_options), key="demo_recurring_responsibilities_input")

    st.markdown(f"**{t('demographics.country_title')}**")
    st.caption(t("demographics.country_caption"))
    country = st.text_input(t("demographics.country_prompt"), value=st.session_state.answers.get("demo_country", ""), key="demo_country_input")

    if st.button(t("demographics.continue_button"), type="primary", use_container_width=True, key="demographics_continue"):
        values = {
            "demo_age": int(age) if age is not None else None,
            "demo_gender": gender,
            "demo_education": education,
            "demo_field": field,
            "demo_occupation": occupation,
            "demo_income": income,
            "demo_financial_decisions": financial_decisions,
            "demo_credit_experience": credit_experience,
            "demo_financial_familiarity": financial_familiarity,
            "demo_living_situation": living_situation,
            "demo_recurring_responsibilities": recurring_responsibilities,
            "demo_country": country.strip(),
        }
        if any(value in (None, "") for value in values.values()):
            st.warning(t("demographics.warning"))
            st.stop()

        command = submit_demographics(read_participant_state(st.session_state), values)
        ctx.commit_command(command, operation="demographics:submit")


__all__ = [
    "demographics_complete",
    "render_demographics_page",
]

