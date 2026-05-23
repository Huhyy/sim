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
db_finalize_participation = getattr(db_module, "finalize_participation")


def _feature_flag(name, default):
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = os.getenv(name, default)
    return str(value).lower() == "true"


REPEAT_SCENARIO_DEV_MODE = _feature_flag("ALLOW_REPEAT_PARTICIPATION", "true")


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


def finalize_participant(session_id, answers, final_score):
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
    )
    st.session_state.submission_finalized = True
    clear_query_param("sid")
    return response



def runtime_defaults():
    return {
        "page": "home",
        "session_id": None,
        "month": 1,
        "loan": Loan(balance=7000.0, annual_interest=0.0835, months=24),
        "overdraft": Overdraft(limit=3000.0, annual_interest=0.24),
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
    }



def collect_checkpoint():
    payment_values = {
        key: value
        for key, value in st.session_state.items()
        if key.startswith("payment_")
    }

    return {
        "page": st.session_state.get("page", "home"),
        "month": st.session_state.get("month", 1),
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
    st.session_state.month = int(checkpoint.get("month", 1))
    st.session_state.loan = Loan(
        balance=float(checkpoint.get("loan_balance", 7000.0)),
        annual_interest=0.0835,
        months=24,
    )
    st.session_state.overdraft = Overdraft(
        limit=3000.0,
        annual_interest=0.24,
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



def bootstrap_authenticated_session():
    account_key = current_account_key()
    if not account_key:
        raise RuntimeError("Authentication is required before starting the scenario.")

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
    is_new_session = not linked_session_id and not url_session_id

    if linked_session_id:
        session_id = linked_session_id
    elif url_session_id:
        session_id = url_session_id
        # Claim an existing URL checkpoint before loading any sensitive answers.
        save_resume_link(account_key, session_id)
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
        for key, value in defaults.items():
            if key not in ("loan", "overdraft", "session_id"):
                st.session_state[key] = value
        st.session_state.session_id = session_id
        st.session_state.loan = defaults["loan"]
        st.session_state.overdraft = defaults["overdraft"]
        persist_checkpoint()

    if is_new_session:
        save_resume_link(account_key, session_id)


def start_new_scenario():
    if not REPEAT_SCENARIO_DEV_MODE:
        raise RuntimeError("Repeat participation is disabled.")

    account_key = current_account_key()
    if not account_key:
        raise RuntimeError("Authentication is required before starting a new scenario.")

    defaults = runtime_defaults()
    for key, value in defaults.items():
        st.session_state[key] = value

    session_id = str(uuid.uuid4())
    st.session_state.session_id = session_id
    set_query_param("sid", session_id)
    persist_checkpoint()
    save_resume_link(account_key, session_id)
