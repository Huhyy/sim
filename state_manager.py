import importlib
import os
import uuid

import streamlit as st

from auth_manager import current_account_key
from loan import Loan
from overdraft import Overdraft
import db as db_module


db_module = importlib.reload(db_module)
load_session_checkpoint = getattr(db_module, "load_session_checkpoint", lambda *_args, **_kwargs: None)
save_session_checkpoint = getattr(db_module, "save_session_checkpoint", lambda *_args, **_kwargs: None)
account_has_completed = getattr(db_module, "account_has_completed", lambda *_args, **_kwargs: False)
load_linked_session_id = getattr(db_module, "load_linked_session_id", lambda *_args, **_kwargs: None)
save_resume_link = getattr(db_module, "save_resume_link", lambda *_args, **_kwargs: None)
db_save_month_result = getattr(db_module, "save_month_result", lambda *_args, **_kwargs: None)
db_save_psychometric_answers = getattr(db_module, "save_psychometric_answers", lambda *_args, **_kwargs: None)
db_save_session_summary = getattr(db_module, "save_session_summary", lambda *_args, **_kwargs: None)
db_finalize_participation = getattr(db_module, "finalize_participation")
load_admin_study_session_by_code = getattr(db_module, "load_admin_study_session_by_code", lambda *_args, **_kwargs: None)
create_admin_study_session = getattr(db_module, "create_admin_study_session", lambda *_args, **_kwargs: None)
list_admin_study_sessions = getattr(db_module, "list_admin_study_sessions", lambda *_args, **_kwargs: [])
cancel_admin_study_session = getattr(db_module, "cancel_admin_study_session", lambda *_args, **_kwargs: None)


def _feature_flag(name, default):
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = os.getenv(name, default)
    return str(value).lower() == "true"


REPEAT_SCENARIO_DEV_MODE = _feature_flag("ALLOW_REPEAT_PARTICIPATION", "true")
SCENARIO_VERSION = "income-baseline-1000-720-initial-150"


def clear_payment_values():
    for key in list(st.session_state.keys()):
        if key.startswith("payment_"):
            del st.session_state[key]


def get_query_param(name):
    try:
        value = st.query_params.get(name)
        if isinstance(value, list):
            return value[0] if value else None
        return value
    except Exception:
        params = st.experimental_get_query_params()
        value = params.get(name)
        if isinstance(value, list):
            return value[0] if value else None
        return value



def set_query_param(name, value):
    try:
        st.query_params[name] = value
    except Exception:
        st.experimental_set_query_params(**{name: value})

    script = f"""
<script>
(function() {{
  try {{
    var url = new URL(window.top.location.href);
    url.searchParams.set({name!r}, {value!r});
    window.top.history.replaceState({{}}, "", url.toString());
  }} catch (e) {{}}
}})();
</script>
"""
    st.components.v1.html(script, height=1)


def clear_query_param(name):
    try:
        if name in st.query_params:
            del st.query_params[name]
    except Exception:
        params = st.experimental_get_query_params()
        params.pop(name, None)
        st.experimental_set_query_params(**params)


def resolve_session_id():
    session_id = st.session_state.get("session_id")
    if session_id:
        return session_id

    candidates = [
        get_query_param("sid"),
        (st.session_state.get("checkpoint_last_load") or {}).get("session_id"),
        (st.session_state.get("checkpoint_last_save") or {}).get("session_id"),
    ]
    for candidate in candidates:
        if candidate:
            st.session_state.session_id = candidate
            return candidate

    return None


def persist_month_result_snapshot(result, bonus_max_session=12.0):
    session_id = resolve_session_id()
    if not session_id:
        return False

    try:
        db_save_month_result(session_id, result, bonus_max_session=bonus_max_session)
        st.session_state.month_snapshot_last_save = {
            "ok": True,
            "session_id": session_id,
            "month": result.get("month"),
        }
        return True
    except Exception as e:
        st.session_state.month_snapshot_last_save = {
            "ok": False,
            "session_id": session_id,
            "month": result.get("month"),
            "error": str(e),
        }
        return False


def persist_psychometric_answers_snapshot(answers, pre_sections=None, post_sections=None):
    session_id = resolve_session_id()
    if not session_id:
        return False

    try:
        db_save_psychometric_answers(
            session_id,
            answers,
            pre_sections=pre_sections,
            post_sections=post_sections,
        )
        st.session_state.psychometric_snapshot_last_save = {
            "ok": True,
            "session_id": session_id,
        }
        return True
    except Exception as e:
        st.session_state.psychometric_snapshot_last_save = {
            "ok": False,
            "session_id": session_id,
            "error": str(e),
        }
        return False


def persist_session_summary_snapshot(summary, feedback=None):
    session_id = resolve_session_id()
    if not session_id:
        return False

    try:
        db_save_session_summary(session_id, summary, feedback=feedback)
        st.session_state.summary_snapshot_last_save = {
            "ok": True,
            "session_id": session_id,
        }
        return True
    except Exception as e:
        st.session_state.summary_snapshot_last_save = {
            "ok": False,
            "session_id": session_id,
            "error": str(e),
        }
        return False


def finalize_participant(
    session_id,
    answers,
    final_score,
    monthly_results=None,
    summary=None,
    pre_sections=None,
    post_sections=None,
):
    resolved_session_id = session_id or resolve_session_id()
    if not resolved_session_id:
        raise ValueError("Missing session_id")

    account_key = current_account_key()
    if not account_key:
        raise ValueError("Missing authenticated account")

    response = db_finalize_participation(
        account_key,
        resolved_session_id,
        answers,
        final_score,
        allow_repeat=REPEAT_SCENARIO_DEV_MODE,
        monthly_results=monthly_results,
        summary=summary,
        pre_sections=pre_sections,
        post_sections=post_sections,
    )
    st.session_state.submission_finalized = True
    clear_query_param("sid")
    return response



def runtime_defaults():
    return {
        "page": "home",
        "session_id": None,
        "language": "en",
        "month": 1,
        "study_session_id": None,
        "study_session_code": None,
        "loan": Loan(balance=7000.0, annual_interest=0.0835, months=24),
        "overdraft": Overdraft(limit=3000.0, annual_interest=0.18),
        "savings": None,
        "total_score": 0,
        "monthly_points": 0.0,
        "accumulated_costs": 0.0,
        "monthly_results": [],
        "pending_month_result": None,
        "final_score": None,
        "answers": {},
        "scroll_to_top": False,
        "submission_finalized": False,
        "already_completed": False,
        "saved": False,
        "scenario_version": SCENARIO_VERSION,
    }



def collect_checkpoint():
    payment_values = {
        key: value
        for key, value in st.session_state.items()
        if key.startswith("payment_")
    }

    return {
        "scenario_version": SCENARIO_VERSION,
        "page": st.session_state.get("page", "home"),
        "admin_return_page": st.session_state.get("admin_return_page"),
        "language": st.session_state.get("language", "en"),
        "month": st.session_state.get("month", 1),
        "study_session_id": st.session_state.get("study_session_id"),
        "study_session_code": st.session_state.get("study_session_code"),
        "loan_balance": st.session_state.loan.balance,
        "overdraft_balance": st.session_state.overdraft.balance,
        "savings": st.session_state.get("savings"),
        "total_score": st.session_state.get("total_score", 0),
        "monthly_points": st.session_state.get("monthly_points", 0.0),
        "accumulated_costs": st.session_state.get("accumulated_costs", 0.0),
        "monthly_results": st.session_state.get("monthly_results", []),
        "pending_month_result": st.session_state.get("pending_month_result"),
        "final_score": st.session_state.get("final_score"),
        "answers": st.session_state.get("answers", {}),
        "payment_values": payment_values,
    }



def persist_checkpoint(status=None):
    if st.session_state.get("submission_finalized") or st.session_state.get("already_completed"):
        return True

    session_id = resolve_session_id()
    if not session_id:
        st.session_state.checkpoint_last_save = {
            "ok": False,
            "error": "Missing session_id",
        }
        return False

    checkpoint = collect_checkpoint()
    resolved_status = status or ("completed" if checkpoint.get("page") == "done" else "in_progress")

    try:
        save_session_checkpoint(session_id, checkpoint, status=resolved_status)
        st.session_state.checkpoint_last_save = {
            "ok": True,
            "session_id": session_id,
            "status": resolved_status,
            "page": checkpoint.get("page"),
            "month": checkpoint.get("month"),
        }
        st.session_state.checkpoint_last_error = None
        return True
    except Exception as e:
        st.session_state.checkpoint_last_save = {
            "ok": False,
            "session_id": session_id,
            "status": resolved_status,
            "page": checkpoint.get("page"),
            "month": checkpoint.get("month"),
            "error": str(e),
        }
        st.session_state.checkpoint_last_error = str(e)
        return False



def hydrate_from_checkpoint(checkpoint):
    defaults = runtime_defaults()
    clear_payment_values()
    for key, value in defaults.items():
        if key not in ("loan", "overdraft", "session_id"):
            st.session_state[key] = value

    page = checkpoint.get("page", "home")
    if page == "pre_questions":
        page = "pre_question_0"
    elif page == "post_questions":
        page = "post_question_0"
    elif page == "month_feedback" and not checkpoint.get("pending_month_result"):
        page = "simulation"

    st.session_state.page = page
    st.session_state.admin_return_page = checkpoint.get("admin_return_page")
    st.session_state.language = checkpoint.get("language", "en")
    st.session_state.month = int(checkpoint.get("month", 1))
    st.session_state.study_session_id = checkpoint.get("study_session_id")
    st.session_state.study_session_code = checkpoint.get("study_session_code")
    st.session_state.loan = Loan(
        balance=float(checkpoint.get("loan_balance", 7000.0)),
        annual_interest=0.0835,
        months=24,
    )
    st.session_state.overdraft = Overdraft(
        limit=3000.0,
        annual_interest=0.18,
    )
    st.session_state.overdraft.balance = round(float(checkpoint.get("overdraft_balance", 0.0)), 2)
    st.session_state.savings = checkpoint.get("savings")
    st.session_state.total_score = checkpoint.get("total_score", 0)
    st.session_state.monthly_points = checkpoint.get("monthly_points", 0.0)
    st.session_state.accumulated_costs = checkpoint.get("accumulated_costs", 0.0)
    st.session_state.monthly_results = checkpoint.get("monthly_results", [])
    st.session_state.pending_month_result = checkpoint.get("pending_month_result")
    st.session_state.final_score = checkpoint.get("final_score")
    st.session_state.answers = checkpoint.get("answers", {})

    for key, value in (checkpoint.get("payment_values") or {}).items():
        st.session_state[key] = value


def reset_current_session_for_scenario_version():
    session_id = resolve_session_id()
    clear_payment_values()
    defaults = runtime_defaults()
    for key, value in defaults.items():
        if key not in ("session_id",):
            st.session_state[key] = value
    st.session_state.session_id = session_id
    persist_checkpoint()
    st.session_state.checkpoint_last_load = {
        "ok": False,
        "source": "supabase",
        "session_id": session_id,
        "reset_reason": "Experiment data changed; old checkpoint was reset.",
        "scenario_version": SCENARIO_VERSION,
    }


def ensure_current_scenario_version():
    current_version = st.session_state.get("scenario_version")
    if current_version == SCENARIO_VERSION:
        return
    reset_current_session_for_scenario_version()



def bootstrap_authenticated_session():
    account_key = current_account_key()
    if not account_key:
        raise RuntimeError("Authentication is required before starting the experiment.")

    if not REPEAT_SCENARIO_DEV_MODE and account_has_completed(account_key):
        defaults = runtime_defaults()
        for key, value in defaults.items():
            st.session_state[key] = value
        st.session_state.page = "already_completed"
        st.session_state.already_completed = True
        clear_query_param("sid")
        return

    linked_session_id = load_linked_session_id(account_key)
    url_session_id = get_query_param("sid")
    unsafe_url_session_id = bool(url_session_id and not linked_session_id)
    is_new_session = not linked_session_id

    if linked_session_id:
        session_id = linked_session_id
    else:
        session_id = str(uuid.uuid4())

    if get_query_param("sid") != session_id:
        set_query_param("sid", session_id)

    st.session_state.session_id = session_id
    st.session_state.checkpoint_last_load = {"ok": False, "source": "supabase", "session_id": session_id}

    try:
        checkpoint = load_session_checkpoint(session_id)
    except Exception as e:
        st.session_state.checkpoint_last_load = {
            "ok": False,
            "source": "supabase",
            "session_id": session_id,
            "error": str(e),
        }
        checkpoint = None

    checkpoint_reset = False
    if checkpoint and checkpoint.get("scenario_version") != SCENARIO_VERSION:
        checkpoint = None
        checkpoint_reset = True

    if checkpoint:
        hydrate_from_checkpoint(checkpoint)
        st.session_state.session_id = session_id
        st.session_state.checkpoint_last_load = {
            "ok": True,
            "source": "supabase",
            "session_id": session_id,
            "page": checkpoint.get("page"),
            "month": checkpoint.get("month"),
        }
    else:
        defaults = runtime_defaults()
        clear_payment_values()
        for key, value in defaults.items():
            if key not in ("loan", "overdraft", "session_id"):
                st.session_state[key] = value
        st.session_state.session_id = session_id
        st.session_state.loan = defaults["loan"]
        st.session_state.overdraft = defaults["overdraft"]
        persist_checkpoint()
        if checkpoint_reset:
            st.session_state.checkpoint_last_load = {
                "ok": False,
                "source": "supabase",
                "session_id": session_id,
                "reset_reason": "Experiment data changed; old checkpoint was reset.",
                "scenario_version": SCENARIO_VERSION,
            }

    if is_new_session:
        save_resume_link(account_key, session_id)
        if unsafe_url_session_id:
            st.session_state.checkpoint_last_load = {
                "ok": False,
                "source": "supabase",
                "session_id": session_id,
                "ignored_url_session_id": url_session_id,
                "reset_reason": "URL session id was not linked to this account, so a fresh session was created.",
            }


def start_new_scenario():
    if not REPEAT_SCENARIO_DEV_MODE:
        raise RuntimeError("Repeat participation is disabled.")

    account_key = current_account_key()
    if not account_key:
        raise RuntimeError("Authentication is required before starting a new experiment.")

    current_study_session_id = st.session_state.get("study_session_id")
    current_study_session_code = st.session_state.get("study_session_code")
    defaults = runtime_defaults()
    clear_payment_values()
    for key, value in defaults.items():
        st.session_state[key] = value
    st.session_state.study_session_id = current_study_session_id
    st.session_state.study_session_code = current_study_session_code

    session_id = str(uuid.uuid4())
    st.session_state.session_id = session_id
    set_query_param("sid", session_id)
    persist_checkpoint()
    save_resume_link(account_key, session_id)
