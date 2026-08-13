"""Strict HTTP request and participant-safe response DTOs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VersionedCommandRequest(StrictModel):
    expected_version: int = Field(ge=0)


class CreateSessionRequest(VersionedCommandRequest):
    expected_version: int = Field(ge=0, le=0)
    language: Literal["en", "ro"] = "en"


class ConsentRequest(VersionedCommandRequest):
    accepted: bool
    anti_ai_declaration: bool = False


class LanguageRequest(VersionedCommandRequest):
    language: Literal["en", "ro"]


class DemographicsRequest(VersionedCommandRequest):
    demo_age: int = Field(ge=18, le=75)
    demo_gender: str = Field(min_length=1)
    demo_education: str = Field(min_length=1)
    demo_field: str = Field(min_length=1)
    demo_occupation: str = Field(min_length=1)
    demo_income: str = Field(min_length=1)
    demo_financial_decisions: str = Field(min_length=1)
    demo_credit_experience: str = Field(min_length=1)
    demo_financial_familiarity: str = Field(min_length=1)
    demo_living_situation: str = Field(min_length=1)
    demo_recurring_responsibilities: str = Field(min_length=1)
    demo_country: str = Field(min_length=1)


class QuestionnaireSectionRequest(VersionedCommandRequest):
    answers: dict[str, str]
    attention_response: str | None = None
    feedback: str | None = None
    strategy_feedback: str | None = None


class ComprehensionRequest(VersionedCommandRequest):
    responses: dict[str, str]


class StudySessionBindingRequest(VersionedCommandRequest):
    session_code: str = Field(min_length=1, max_length=6)
    participant_code: str = Field(min_length=1, max_length=4)


class MonthDecisionRequest(VersionedCommandRequest):
    payment: float | None = Field(default=None, ge=0)


class FeedbackAcknowledgementRequest(VersionedCommandRequest):
    pass


class FinalizeRequest(VersionedCommandRequest):
    pass


class AdminCreateSessionRequest(StrictModel):
    experimental_condition: Literal["C1", "C2", "C3", "C4"]


class AdminPayoutView(StrictModel):
    final_score: float
    performance_bonus_gbp: float
    total_payout_gbp: float
    payment_status: str
    prolific_bonus_status: str


class AdminParticipantView(StrictModel):
    participant_code: str | None
    stage: str
    page_label: str
    progress_percent: int
    status: str
    payout: AdminPayoutView | None
    updated_at: str | None


class AdminStudySessionView(StrictModel):
    id: str
    session_code: str
    experimental_condition: Literal["C1", "C2", "C3", "C4"]
    status: str
    created_at: str | None
    participants: list[AdminParticipantView]


class HomeView(StrictModel):
    type: Literal["home"]
    title: str
    body: str
    info: str
    framing_notice: str
    study_session_available: bool


class StudySessionView(StrictModel):
    type: Literal["study_session"]
    title: str
    body: str


class ConsentView(StrictModel):
    type: Literal["consent"]
    content: str
    items: list[str]
    anti_ai_declaration_required: bool
    framing_notice: str


class ConsentDeclinedView(StrictModel):
    type: Literal["consent_declined"]
    title: str
    body: str


class DemographicsView(StrictModel):
    type: Literal["demographics"]
    title: str
    intro: str
    values: dict[str, Any]
    options: dict[str, list[str]]
    age_range: dict[str, int]


class QuestionnaireQuestion(StrictModel):
    key: str
    number: int = Field(ge=1)
    prompt: str
    options: list[str]


class AttentionCheck(StrictModel):
    prompt: str
    options: list[str]


class QuestionnaireSectionView(StrictModel):
    type: Literal["questionnaire_section"]
    phase: Literal["pre", "post"]
    section_index: int
    section_count: int
    title: str | None = None
    instruction: str | None = None
    questions: list[QuestionnaireQuestion]
    values: dict[str, str]
    attention_check: AttentionCheck | None = None
    optional_feedback: dict[str, str] | None = None


class InstructionsView(StrictModel):
    type: Literal["instructions"]
    content: str


class ComprehensionQuestion(StrictModel):
    id: str
    prompt: str
    options: list[str]


class ComprehensionView(StrictModel):
    type: Literal["comprehension"]
    title: str
    intro: str
    attempts: int
    questions: list[ComprehensionQuestion]


class ProfileView(StrictModel):
    type: Literal["profile"]
    title: str
    intro: str
    sections: list[dict[str, str]]


class MoneyItem(StrictModel):
    category: str
    value: float


class SimulationSummary(StrictModel):
    opening_balance: float | None
    income_total: float
    expenses_total: float
    credit_interest: float
    overdraft_interest: float
    remaining_credit: float
    used_overdraft: float
    available_before_payment: float
    contract_payment: float


class PaymentInputView(StrictModel):
    required: bool
    blocked: bool
    minimum: int


class SimulationView(StrictModel):
    type: Literal["simulation"]
    month: int
    narrative: str
    income: list[MoneyItem]
    expenses: list[MoneyItem]
    summary: SimulationSummary
    payment: PaymentInputView


class FinancialResultView(StrictModel):
    payment_input: float | None
    accepted_payment: float | None
    cash_final: float | None
    credit_final: float | None
    overdraft_final: float | None
    credit_interest: float | None
    overdraft_interest: float | None
    penalties: float | None


class FeedbackMessageView(StrictModel):
    tone: Literal["success", "warning", "error"]
    message: str


class DisplayedScoreView(StrictModel):
    repayment: float | None
    liquidity: float | None
    overdraft: float | None
    monthly_score: float | None = None
    monthly_loss: float | None = None


class MonthFeedbackView(StrictModel):
    type: Literal["month_feedback"]
    month: int | None
    financial_result: FinancialResultView
    feedback: FeedbackMessageView
    score: DisplayedScoreView | None = None


class FinalScoreView(StrictModel):
    type: Literal["final_score"]
    final_score: float | None
    bonus: dict[str, float | int | None]
    summary: dict[str, float | None]
    info: str


class CompletionView(StrictModel):
    type: Literal["completion"]
    saved: bool
    final_score: float | None
    participant_code: str | None
    bonus: dict[str, float | int | None]
    remaining_credit: float
    remaining_overdraft: float
    prolific_completion: dict[str, str | None] | None = None


class SimpleMessageView(StrictModel):
    type: Literal["already_completed", "prolific_error", "prolific_return"]
    title: str | None = None
    body: str | None = None
    message: str | None = None


class UnavailableView(StrictModel):
    type: Literal["unavailable", "questionnaire_unavailable", "feedback_unavailable"]
    phase: str | None = None


ParticipantView = (
    HomeView
    | StudySessionView
    | ConsentView
    | ConsentDeclinedView
    | DemographicsView
    | QuestionnaireSectionView
    | InstructionsView
    | ComprehensionView
    | ProfileView
    | SimulationView
    | MonthFeedbackView
    | FinalScoreView
    | CompletionView
    | SimpleMessageView
    | UnavailableView
)


class ParticipantSessionResponse(StrictModel):
    session_id: str
    state_version: int
    stage: str
    month: int
    language: Literal["en", "ro"]
    labels: dict[str, Any]
    view: ParticipantView = Field(discriminator="type")
    idempotency_replayed: bool = False


class ApiErrorDetail(StrictModel):
    code: str
    message: str
    retryable: bool
    request_id: str
    authoritative_version: int | None = None


class ApiErrorResponse(StrictModel):
    error: ApiErrorDetail


__all__ = [name for name in globals() if name.endswith(("Request", "Response", "View"))]
