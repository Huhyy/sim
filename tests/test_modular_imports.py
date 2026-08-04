def test_persistence_modules_expose_database_functions():
    from sim_app.persistence import (
        account_has_completed,
        finalize_participation,
        load_linked_session_id,
        list_participant_sessions_for_study_session,
        load_session_checkpoint,
        save_month_result,
        save_resume_link,
        save_session_checkpoint,
    )

    assert callable(account_has_completed)
    assert callable(finalize_participation)
    assert callable(load_linked_session_id)
    assert callable(list_participant_sessions_for_study_session)
    assert callable(load_session_checkpoint)
    assert callable(save_month_result)
    assert callable(save_resume_link)
    assert callable(save_session_checkpoint)


def test_session_and_state_modules_expose_state_functions():
    from sim_app.session import bootstrap_authenticated_session, finalize_participant, start_new_scenario
    from sim_app.state import collect_checkpoint, hydrate_from_checkpoint, runtime_defaults

    assert callable(bootstrap_authenticated_session)
    assert callable(finalize_participant)
    assert callable(start_new_scenario)
    assert callable(collect_checkpoint)
    assert callable(hydrate_from_checkpoint)
    assert callable(runtime_defaults)


def test_auth_modules_expose_auth_functions():
    from sim_app.auth import current_account_key, current_user_email, is_admin_user, is_logged_in

    assert callable(current_account_key)
    assert callable(current_user_email)
    assert callable(is_admin_user)
    assert callable(is_logged_in)


def test_domain_modules_expose_models():
    from sim_app.domain import Loan as PackageLoan
    from sim_app.domain import Overdraft as PackageOverdraft
    from sim_app.domain import condition_config, performance_bonus

    package_loan = PackageLoan(balance=7000.0, annual_interest=0.0835, months=24)
    assert package_loan.get_state() == {"balance": 7000.0, "required_payment": 317.71}
    assert package_loan.apply_interest() == 48.71
    assert package_loan.apply_payment(250.0) == {"interest": 0.0, "principal": 250.0}
    assert package_loan.get_state() == {"balance": 6750.0, "required_payment": 317.71}

    package_overdraft = PackageOverdraft(limit=3000.0, annual_interest=0.18)
    assert package_overdraft.get_state() == {"balance": 0.0, "limit": 3000.0}
    assert package_overdraft.cover_deficit(-120.0) == 0.0
    assert package_overdraft.apply_interest() == 1.8
    assert package_overdraft.get_state() == {"balance": 120.0, "limit": 3000.0}

    assert condition_config("C1") == {
        "experimental_condition": "C1",
        "score_frame": "gain_frame",
        "monthly_score_feedback": "displayed",
    }
    assert condition_config("C4") == {
        "experimental_condition": "C4",
        "score_frame": "loss_frame",
        "monthly_score_feedback": "hidden",
    }
    assert performance_bonus(80) == {"performance_bonus_gbp": 1, "loss_amount_gbp": 2}
    assert performance_bonus(94.99) == {"performance_bonus_gbp": 2, "loss_amount_gbp": 1}
    assert performance_bonus(95) == {"performance_bonus_gbp": 3, "loss_amount_gbp": 0}


def test_prolific_helpers_are_deterministic(monkeypatch):
    from sim_app.prolific.identity import assign_prolific_condition, completion_redirect_url

    first = assign_prolific_condition("pid-1", "study-1")
    second = assign_prolific_condition("pid-1", "study-1")
    assert first == second


    assert first["experimental_condition"] in {"C1", "C2", "C3", "C4"}

    monkeypatch.setattr(
        "sim_app.prolific.identity._get_secret",
        lambda name: "https://app.prolific.com/submissions/complete?cc={completion_code}" if name == "PROLIFIC_COMPLETION_URL" else None,
    )
    assert completion_redirect_url("FIN-123") == "https://app.prolific.com/submissions/complete?cc=FIN-123"


def test_prolific_params_survive_query_string_loss(monkeypatch):
    import sim_app.prolific.identity as identity

    identity.st.session_state.clear()
    values = iter(["", "", ""])
    monkeypatch.setattr(identity, "get_query_param", lambda _name: next(values))
    identity.st.session_state._prolific_params = {
        "PROLIFIC_PID": "pid-1",
        "STUDY_ID": "study-1",
        "SESSION_ID": "submission-1",
    }

    assert identity.load_prolific_params() == {
        "PROLIFIC_PID": "pid-1",
        "STUDY_ID": "study-1",
        "SESSION_ID": "submission-1",
    }


def test_prolific_flow_guard_requires_prior_steps():
    from sim_app.prolific.flow import prolific_required_page_before

    pre_sections = [{"key_prefix": "dopa", "questions": ["a", "b"]}]
    post_sections = [{"key_prefix": "post", "questions": ["a"]}]
    state = {
        "prolific_mode": True,
        "answers": {"consent_agreed": "1 - Da", "anti_ai_declaration": True},
    }

    assert prolific_required_page_before("profile", state, pre_sections=pre_sections, post_sections=post_sections) == "demographics"

    state["answers"].update(
        {
            "demo_age": 30,
            "demo_gender": "x",
            "demo_education": "x",
            "demo_field": "x",
            "demo_occupation": "x",
            "demo_financial_decisions": "x",
            "demo_credit_experience": "x",
            "demo_financial_familiarity": "x",
            "demo_living_situation": "x",
            "demo_recurring_responsibilities": "x",
            "demo_country": "x",
            "demo_income": "x",
        }
    )
    assert prolific_required_page_before("profile", state, pre_sections=pre_sections, post_sections=post_sections) == "pre_question_0"

    state["answers"].update({"dopa_0": "x", "dopa_1": "x"})
    assert prolific_required_page_before("profile", state, pre_sections=pre_sections, post_sections=post_sections) == "instructions"

    state["comprehension_passed"] = True
    assert prolific_required_page_before("final_score", state, pre_sections=pre_sections, post_sections=post_sections) == "simulation"


def test_persistence_mappers_shape_rows(monkeypatch):
    import sim_app.persistence.mappers as mappers

    now = "2026-06-15T00:00:00+00:00"
    monkeypatch.setattr(mappers, "_utcnow", lambda: now)

    answers = {
        "consent_agreed": "1 - Da",
        "demo_age": 34,
        "unrelated": "ignored",
        "pre_0": "5 - Strong",
    }
    sections = [{"key_prefix": "pre", "questions": ["Question one", "Question two"]}]
    result = {
        "month": 1,
        "monthly_score": "80",
        "payment_valid": True,
        "liquidity_after_charges": "120.5",
    }

    assert mappers._demographic_answers(answers) == {
        "consent_agreed": "1 - Da",
        "demo_age": 34,
    }
    assert mappers._psychometric_rows("session-1", answers, sections) == [
        {
            "session_id": "session-1",
            "section_number": 1,
            "question_number": 1,
            "question_key": "pre_0",
            "question_text": "Question one",
            "answer_value": 5,
            "updated_at": now,
        }
    ]
    month_row = mappers._month_result_row("session-1", result)
    assert month_row["session_id"] == "session-1"
    assert month_row["month_number"] == 1
    assert month_row["monthly_score"] == 80.0
    assert month_row["bonus_lunar"] == 0.4
    assert month_row["liquidity_before_payment"] == 120.5

    metadata = {
        "study_session_id": "study-session-1",
        "study_session_code": "123456",
        "participant_code": "P001",
    }
    psychometric_rows = mappers._psychometric_rows("session-1", answers, sections, metadata=metadata)
    assert psychometric_rows[0]["study_session_id"] == "study-session-1"
    assert psychometric_rows[0]["study_session_code"] == "123456"
    assert psychometric_rows[0]["participant_code"] == "P001"

    month_row_with_metadata = mappers._month_result_row("session-1", result, metadata=metadata)
    assert month_row_with_metadata["study_session_id"] == "study-session-1"
    assert month_row_with_metadata["study_session_code"] == "123456"
    assert month_row_with_metadata["participant_code"] == "P001"


def test_auth_admin_parser():
    import sim_app.auth.admin as admin

    assert admin._parse_admin_emails(None) == set()
    assert admin._parse_admin_emails("a@example.com,b@example.com") == {"a@example.com", "b@example.com"}
    assert admin._parse_admin_emails("a@example.com; b@example.com") == {"a@example.com", "b@example.com"}
    assert admin._parse_admin_emails("['a@example.com', 'b@example.com']") == {"a@example.com", "b@example.com"}
    assert admin._parse_admin_emails(["a@example.com", " b@example.com "]) == {"a@example.com", "b@example.com"}


def test_study_session_participant_filter():
    import sim_app.persistence.study_sessions as study_sessions

    assert study_sessions._with_participant_codes(
        [
            {"participant_code": "P001"},
            {"participant_code": None},
            {"participant_code": ""},
        ]
    ) == [{"participant_code": "P001"}]


def test_study_session_participants_merge_session_summaries():
    import sim_app.persistence.study_sessions as study_sessions

    class FakeQuery:
        def __init__(self, data):
            self.data = data
            self.session_ids = None

        def select(self, _columns):
            return self

        def in_(self, _column, values):
            self.session_ids = values
            return self

        def execute(self):
            return type("Response", (), {"data": self.data})()

    class FakeClient:
        def __init__(self, data):
            self.query = FakeQuery(data)

        def table(self, name):
            assert name == "session_summaries"
            return self.query

    rows = [{"id": "session-1", "participant_code": "P001"}]
    client = FakeClient(
        [
            {
                "session_id": "session-1",
                "final_score": 95,
                "performance_bonus_gbp": 3,
                "payment_status": "unpaid",
            }
        ]
    )

    assert study_sessions._with_session_summaries(client, rows) == [
        {
            "id": "session-1",
            "participant_code": "P001",
            "summary": {
                "session_id": "session-1",
                "final_score": 95,
                "performance_bonus_gbp": 3,
                "payment_status": "unpaid",
            },
        }
    ]
    assert client.query.session_ids == ["session-1"]


def test_content_modules_load_packaged_content():
    import sim_app.content.narratives as package_narratives
    import sim_app.content.tables as package_tables

    assert package_tables.get_month(1)["position"]["initial"] == 150
    assert "Ianuarie" in package_narratives.get_narrative(1)
