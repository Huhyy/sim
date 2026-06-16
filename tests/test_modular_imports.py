import auth_manager
import db
import state_manager
from loan import Loan
from overdraft import Overdraft


def test_persistence_modules_expose_database_functions():
    from sim_app.persistence import (
        account_has_completed,
        finalize_participation,
        load_linked_session_id,
        load_session_checkpoint,
        save_month_result,
        save_resume_link,
        save_session_checkpoint,
    )

    assert callable(account_has_completed)
    assert callable(finalize_participation)
    assert callable(load_linked_session_id)
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


def test_domain_modules_expose_existing_models():
    from sim_app.domain import Loan as PackageLoan
    from sim_app.domain import Overdraft as PackageOverdraft

    package_loan = PackageLoan(balance=7000.0, annual_interest=0.0835, months=24)
    legacy_loan = Loan(balance=7000.0, annual_interest=0.0835, months=24)
    assert package_loan.get_state() == legacy_loan.get_state()
    assert package_loan.apply_interest() == legacy_loan.apply_interest()
    assert package_loan.apply_payment(250.0) == legacy_loan.apply_payment(250.0)
    assert package_loan.get_state() == legacy_loan.get_state()

    package_overdraft = PackageOverdraft(limit=3000.0, annual_interest=0.18)
    legacy_overdraft = Overdraft(limit=3000.0, annual_interest=0.18)
    assert package_overdraft.get_state() == legacy_overdraft.get_state()
    assert package_overdraft.cover_deficit(-120.0) == legacy_overdraft.cover_deficit(-120.0)
    assert package_overdraft.apply_interest() == legacy_overdraft.apply_interest()
    assert package_overdraft.get_state() == legacy_overdraft.get_state()


def test_persistence_mappers_match_legacy_db_behavior(monkeypatch):
    import sim_app.persistence.mappers as mappers

    now = "2026-06-15T00:00:00+00:00"
    monkeypatch.setattr(db, "_utcnow", lambda: now)
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

    assert mappers._demographic_answers(answers) == db._demographic_answers(answers)
    assert mappers._psychometric_rows("session-1", answers, sections) == db._psychometric_rows("session-1", answers, sections)
    assert mappers._month_result_row("session-1", result) == db._month_result_row("session-1", result)


def test_auth_admin_parser_matches_legacy_behavior():
    import sim_app.auth.admin as admin

    values = [
        None,
        "a@example.com,b@example.com",
        "a@example.com; b@example.com",
        "['a@example.com', 'b@example.com']",
        ["a@example.com", " b@example.com "],
    ]

    for value in values:
        assert admin._parse_admin_emails(value) == auth_manager._parse_admin_emails(value)


def test_content_modules_match_legacy_content():
    import narratives
    import tables
    import sim_app.content.narratives as package_narratives
    import sim_app.content.tables as package_tables

    assert package_tables.get_month(1) == tables.get_month(1)
    assert package_narratives.get_narrative(1) == narratives.get_narrative(1)
