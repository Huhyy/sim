import streamlit as st
from supabase import create_client

@st.cache_resource
def get_client():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def _parse(value):
    if value is None:
        return None
    try:
        return int(str(value).split(" - ")[0].strip())
    except Exception:
        return None


def save_participant(session_id: str, answers: dict, final_score: float):
    row = {
        "id": session_id,
        "completed": True,
        "final_score": float(final_score),
        "feedback": answers.get("feedback") or None,
    }
    for key, value in answers.items():
        if key == "feedback":
            continue
        row[key] = _parse(value)

    get_client().table("participants").upsert(row).execute()
