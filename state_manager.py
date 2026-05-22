import importlib
import uuid

import streamlit as st

from loan import Loan
from overdraft import Overdraft
import db as db_module


db_module = importlib.reload(db_module)
load_session_checkpoint = getattr(db_module, "load_session_checkpoint", lambda *_args, **_kwargs: None)
save_participant = getattr(db_module, "save_participant")
save_session_checkpoint = getattr(db_module, "save_session_checkpoint", lambda *_args, **_kwargs: None)


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
    session_id = st.session_state.get("session_id")
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
            "status": resolved_status,
            "page": checkpoint.get("page"),
            "month": checkpoint.get("month"),
        }
        st.session_state.checkpoint_last_error = None
        return True
    except Exception as e:
        st.session_state.checkpoint_last_save = {
            "ok": False,
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



def bootstrap_anonymous_session():
    session_id = get_query_param("sid")
    if not session_id:
        session_id = str(uuid.uuid4())
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
