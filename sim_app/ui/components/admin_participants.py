"""Admin participant progress list."""

from html import escape


STAGE_CONFIG = {
    "pre": {
        "label_key": "admin.participant_stage_pre",
        "class_name": "admin-participant-progress-fill pre",
    },
    "months": {
        "label_key": "admin.participant_stage_months",
        "class_name": "admin-participant-progress-fill months",
    },
    "post": {
        "label_key": "admin.participant_stage_post",
        "class_name": "admin-participant-progress-fill post",
    },
}


ADMIN_PARTICIPANTS_CSS = """
<style>
.admin-participants {
    margin: 0.4rem 0 1.1rem;
    padding: 0.75rem 0.85rem;
    border: 1px solid #e1dac8;
    border-radius: 0.75rem;
    background: rgba(255, 250, 240, 0.62);
}
.admin-participants-title {
    margin-bottom: 0.55rem;
    color: #172b29;
    font: 800 0.82rem/1.2 'Manrope', sans-serif;
}
.admin-participant-row {
    display: grid;
    grid-template-columns: minmax(4.5rem, 0.7fr) minmax(7rem, 1fr) minmax(12rem, 3fr) minmax(8.5rem, 1.2fr);
    align-items: center;
    gap: 0.75rem;
    margin: 0.4rem 0;
}
.admin-participant-code {
    color: #172b29;
    font: 800 0.84rem/1.2 'Manrope', sans-serif;
}
.admin-participant-stage {
    color: #586564;
    font: 700 0.74rem/1.2 'Manrope', sans-serif;
}
.admin-participant-progress {
    height: 0.78rem;
    border-radius: 999px;
    background: #e6dfcf;
    overflow: hidden;
}
.admin-participant-progress-fill {
    height: 100%;
    min-width: 0.55rem;
    border-radius: inherit;
}
.admin-participant-progress-fill.pre {
    background: #2f9e44;
}
.admin-participant-progress-fill.months {
    background: #d6a21e;
}
.admin-participant-progress-fill.post {
    background: #d94841;
}
.admin-participant-payout {
    min-height: 1.8rem;
    color: #172b29;
    font: 700 0.74rem/1.35 'Manrope', sans-serif;
}
.admin-participant-payout span {
    display: block;
}
.admin-participant-payment-status {
    color: #6f7774;
    font-weight: 600;
}
@media (max-width: 640px) {
    .admin-participant-row {
        grid-template-columns: 1fr;
        gap: 0.24rem;
    }
}
</style>
"""


def participant_page(row):
    checkpoint = row.get("checkpoint") or {}
    if row.get("status") == "completed":
        return "done"
    return checkpoint.get("page") or row.get("current_page") or "unknown"


def participant_month(row):
    checkpoint = row.get("checkpoint") or {}
    try:
        return int(checkpoint.get("month") or 1)
    except (TypeError, ValueError):
        return 1


def participant_stage(row):
    page = participant_page(row)
    if page.startswith("post_question_") or page in ("final_score", "done"):
        return "post"
    if page in ("instructions", "profile", "simulation", "month_feedback"):
        return "months"
    return "pre"


def participant_progress_percent(row, pre_count=0, post_count=0):
    page = participant_page(row)
    month = participant_month(row)

    if page == "done":
        return 100
    if page == "final_score":
        return 96
    if page.startswith("post_question_"):
        index = _page_index(page)
        denominator = max(1, post_count)
        return min(95, 82 + int(((index + 1) / denominator) * 12))
    if page == "month_feedback":
        return min(80, 30 + int((max(1, month) / 24) * 50))
    if page == "simulation":
        return min(78, 30 + int(((max(1, month) - 1) / 24) * 50))
    if page == "profile":
        return 30
    if page == "instructions":
        return 27
    if page.startswith("pre_question_"):
        index = _page_index(page)
        denominator = max(1, pre_count)
        return min(25, 14 + int(((index + 1) / denominator) * 11))
    if page == "demographics":
        return 12
    if page == "consent":
        return 8
    if page == "home":
        return 5
    return 3


def exact_page_label(row):
    page = participant_page(row)
    month = participant_month(row)
    if page in ("simulation", "month_feedback"):
        return f"{page} - month {month}"
    return page


def participant_payout_summary(row):
    summary = _participant_summary_source(row)
    final_score = summary.get("final_score")
    performance_bonus_eur = summary.get("performance_bonus_eur")
    if final_score is None or performance_bonus_eur is None:
        return None
    return {
        "final_score": _display_number(final_score),
        "performance_bonus_eur": int(float(performance_bonus_eur)),
        "payment_status": summary.get("payment_status") or "unpaid",
    }


def render_admin_participants(ctx, participants):
    st = ctx.st
    t = ctx.t
    st.markdown(ADMIN_PARTICIPANTS_CSS, unsafe_allow_html=True)

    if not participants:
        st.caption(t("admin.no_participants"))
        return

    rows = [f'<div class="admin-participants-title">{escape(t("admin.participants_title"))}</div>']
    pre_count = len(getattr(ctx, "pre_sections_ro", None) or [])
    post_count = len(getattr(ctx, "post_sections_ro", None) or [])

    for participant in participants:
        code = escape(participant.get("participant_code") or "-")
        stage = participant_stage(participant)
        stage_config = STAGE_CONFIG[stage]
        stage_label = escape(t(stage_config["label_key"]))
        percent = participant_progress_percent(participant, pre_count=pre_count, post_count=post_count)
        title = escape(exact_page_label(participant), quote=True)
        payout = participant_payout_summary(participant)
        payout_html = ""
        if payout:
            payout_html = (
                f'<span>{escape(t("admin.final_score_label"))}: {escape(payout["final_score"])} / 100</span>'
                f'<span>{escape(t("admin.payout_label"))}: {payout["performance_bonus_eur"]} EUR</span>'
                f'<span class="admin-participant-payment-status">{escape(t("admin.payment_status_label"))}: '
                f'{escape(str(payout["payment_status"]))}</span>'
            )
        rows.append(
            f"""
<div class="admin-participant-row">
  <div class="admin-participant-code">{code}</div>
  <div class="admin-participant-stage">{stage_label}</div>
  <div class="admin-participant-progress" title="{title}">
    <div class="{stage_config["class_name"]}" style="width: {percent}%"></div>
  </div>
  <div class="admin-participant-payout">{payout_html}</div>
</div>
"""
        )

    st.markdown(f'<div class="admin-participants">{"".join(rows)}</div>', unsafe_allow_html=True)


def _page_index(page):
    try:
        return int(str(page).rsplit("_", 1)[1])
    except (IndexError, TypeError, ValueError):
        return 0


def _display_number(value):
    number = round(float(value), 2)
    if number == int(number):
        return str(int(number))
    return f"{number:.2f}"


def _participant_summary_source(row):
    summary = row.get("summary") or {}
    if summary.get("final_score") is not None and summary.get("performance_bonus_eur") is not None:
        return summary
    checkpoint = row.get("checkpoint") or {}
    return checkpoint.get("final_score_breakdown") or {}


__all__ = [
    "exact_page_label",
    "participant_payout_summary",
    "participant_progress_percent",
    "participant_stage",
    "render_admin_participants",
]
