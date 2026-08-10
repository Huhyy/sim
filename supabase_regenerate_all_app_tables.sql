-- Behavioral Credit Simulator: destructive development regeneration
-- Run only after supabase_drop_all_app_tables.sql against the intended development project.
-- Canonical order: base schema -> structured results -> Phase 3 hardening.

-- Current Supabase schema for the scenario app.
-- This is intentionally structured only: no legacy participants/months/study_responses blob tables.

DROP FUNCTION IF EXISTS finalize_study_response(TEXT, UUID, NUMERIC, TEXT, JSONB);
DROP TABLE IF EXISTS legacy_responses CASCADE;
DROP TABLE IF EXISTS study_responses CASCADE;
DROP TABLE IF EXISTS participants CASCADE;
DROP TABLE IF EXISTS months CASCADE;

CREATE TABLE IF NOT EXISTS participant_sessions (
  id UUID PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'in_progress',
  current_page TEXT,
  checkpoint JSONB NOT NULL DEFAULT '{}'::jsonb,
  demographics JSONB NOT NULL DEFAULT '{}'::jsonb,
  study_session_id UUID,
  study_session_code TEXT,
  participant_code TEXT CHECK (participant_code IS NULL OR participant_code ~ '^P[0-9]{3}$'),
  experimental_condition TEXT NOT NULL DEFAULT 'C1' CHECK (experimental_condition IN ('C1', 'C2', 'C3', 'C4')),
  score_frame TEXT NOT NULL DEFAULT 'gain_frame' CHECK (score_frame IN ('gain_frame', 'loss_frame')),
  monthly_score_feedback TEXT NOT NULL DEFAULT 'displayed' CHECK (monthly_score_feedback IN ('displayed', 'hidden')),
  UNIQUE (study_session_id, participant_code)
);

CREATE TABLE IF NOT EXISTS admin_study_sessions (
  id UUID PRIMARY KEY,
  session_code TEXT NOT NULL UNIQUE CHECK (session_code ~ '^[0-9]{6}$'),
  created_by_email TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  experimental_condition TEXT NOT NULL DEFAULT 'C1' CHECK (experimental_condition IN ('C1', 'C2', 'C3', 'C4')),
  score_frame TEXT NOT NULL DEFAULT 'gain_frame' CHECK (score_frame IN ('gain_frame', 'loss_frame')),
  monthly_score_feedback TEXT NOT NULL DEFAULT 'displayed' CHECK (monthly_score_feedback IN ('displayed', 'hidden')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS psychometric_pre_answers (
  session_id UUID NOT NULL REFERENCES participant_sessions(id) ON DELETE CASCADE,
  study_session_id UUID,
  study_session_code TEXT,
  participant_code TEXT CHECK (participant_code IS NULL OR participant_code ~ '^P[0-9]{3}$'),
  section_number INTEGER NOT NULL,
  question_number INTEGER NOT NULL,
  question_key TEXT NOT NULL,
  question_text TEXT NOT NULL,
  answer_value SMALLINT NOT NULL CHECK (answer_value BETWEEN 1 AND 5),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (session_id, question_key),
  UNIQUE (session_id, question_number)
);
CREATE INDEX IF NOT EXISTS psychometric_pre_answers_study_participant_idx
  ON psychometric_pre_answers (study_session_id, participant_code);

CREATE TABLE IF NOT EXISTS psychometric_post_answers (
  session_id UUID NOT NULL REFERENCES participant_sessions(id) ON DELETE CASCADE,
  study_session_id UUID,
  study_session_code TEXT,
  participant_code TEXT CHECK (participant_code IS NULL OR participant_code ~ '^P[0-9]{3}$'),
  section_number INTEGER NOT NULL,
  question_number INTEGER NOT NULL,
  question_key TEXT NOT NULL,
  question_text TEXT NOT NULL,
  answer_value SMALLINT NOT NULL CHECK (answer_value BETWEEN 1 AND 5),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (session_id, question_key),
  UNIQUE (session_id, question_number)
);
CREATE INDEX IF NOT EXISTS psychometric_post_answers_study_participant_idx
  ON psychometric_post_answers (study_session_id, participant_code);

CREATE TABLE IF NOT EXISTS month_results (
  session_id UUID NOT NULL REFERENCES participant_sessions(id) ON DELETE CASCADE,
  study_session_id UUID,
  study_session_code TEXT,
  participant_code TEXT CHECK (participant_code IS NULL OR participant_code ~ '^P[0-9]{3}$'),
  month_number SMALLINT NOT NULL CHECK (month_number BETWEEN 1 AND 24),
  opening_balance NUMERIC(12,2),
  income_total NUMERIC(12,2),
  expenses_total NUMERIC(12,2),
  loan_obligation NUMERIC(12,2),
  credit_interest NUMERIC(12,2),
  overdraft_interest NUMERIC(12,2),
  penalties NUMERIC(12,2),
  available_total NUMERIC(12,2),
  outflows_before_credit NUMERIC(12,2),
  deficit_before_credit NUMERIC(12,2),
  liquidity_before_payment NUMERIC(12,2),
  overdraft_after_charges NUMERIC(12,2),
  overdraft_remaining NUMERIC(12,2),
  max_payment NUMERIC(12,2),
  payment_input NUMERIC(12,2),
  accepted_payment NUMERIC(12,2),
  overdraft_from_payment NUMERIC(12,2),
  overdraft_final NUMERIC(12,2),
  cash_final NUMERIC(12,2),
  credit_final NUMERIC(12,2),
  score_repayment NUMERIC(6,2),
  score_liquidity NUMERIC(6,2),
  score_overdraft NUMERIC(6,2),
  monthly_score NUMERIC(6,2),
  bonus_lunar NUMERIC(12,4),
  costs_this_month NUMERIC(12,2),
  feedback_message TEXT,
  invalid_reason TEXT,
  pre_credit_impossible BOOLEAN,
  payment_valid BOOLEAN,
  score_model TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (session_id, month_number)
);
CREATE INDEX IF NOT EXISTS month_results_study_participant_idx
  ON month_results (study_session_id, participant_code);

CREATE TABLE IF NOT EXISTS session_summaries (
  session_id UUID PRIMARY KEY REFERENCES participant_sessions(id) ON DELETE CASCADE,
  months_completed INTEGER NOT NULL DEFAULT 0,
  monthly_score_sum NUMERIC(8,2),
  final_score NUMERIC(6,2),
  bonus_max_session NUMERIC(12,2),
  bonus_final NUMERIC(12,2),
  experimental_condition TEXT NOT NULL DEFAULT 'C1' CHECK (experimental_condition IN ('C1', 'C2', 'C3', 'C4')),
  score_frame TEXT NOT NULL DEFAULT 'gain_frame' CHECK (score_frame IN ('gain_frame', 'loss_frame')),
  monthly_score_feedback TEXT NOT NULL DEFAULT 'displayed' CHECK (monthly_score_feedback IN ('displayed', 'hidden')),
  performance_bonus_czk INTEGER NOT NULL DEFAULT 0,
  loss_amount_czk INTEGER NOT NULL DEFAULT 0,
  completion_timestamp TIMESTAMPTZ,
  payment_status TEXT NOT NULL DEFAULT 'unpaid',
  total_repaid NUMERIC(12,2),
  remaining_credit NUMERIC(12,2),
  remaining_overdraft NUMERIC(12,2),
  credit_interest_total NUMERIC(12,2),
  overdraft_interest_total NUMERIC(12,2),
  interest_total NUMERIC(12,2),
  study_session_id UUID,
  study_session_code TEXT,
  participant_code TEXT CHECK (participant_code IS NULL OR participant_code ~ '^P[0-9]{3}$'),
  feedback TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS session_summaries_study_participant_idx
  ON session_summaries (study_session_id, participant_code);

CREATE TABLE IF NOT EXISTS resume_links (
  account_key TEXT PRIMARY KEY CHECK (char_length(account_key) = 64),
  session_id UUID NOT NULL UNIQUE REFERENCES participant_sessions(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS completed_accounts (
  account_key TEXT PRIMARY KEY CHECK (char_length(account_key) = 64),
  completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE participant_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_study_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE psychometric_pre_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE psychometric_post_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE month_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE completed_accounts ENABLE ROW LEVEL SECURITY;

-- ===== STRUCTURED RESULTS MIGRATION =====

-- Structured result storage for the experiment app.
-- Run this once in Supabase SQL Editor before deploying the matching app code.

DROP FUNCTION IF EXISTS finalize_study_response(TEXT, UUID, NUMERIC, TEXT, JSONB);
DROP TABLE IF EXISTS legacy_responses CASCADE;
DROP TABLE IF EXISTS study_responses CASCADE;
DROP TABLE IF EXISTS participants CASCADE;
DROP TABLE IF EXISTS months CASCADE;

CREATE TABLE IF NOT EXISTS participant_sessions (
  id UUID PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'in_progress',
  current_page TEXT,
  checkpoint JSONB NOT NULL DEFAULT '{}'::jsonb
);

ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS demographics JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS study_session_id UUID;
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS study_session_code TEXT;
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS participant_code TEXT CHECK (participant_code IS NULL OR participant_code ~ '^P[0-9]{3}$');
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS experimental_condition TEXT NOT NULL DEFAULT 'C1' CHECK (experimental_condition IN ('C1', 'C2', 'C3', 'C4'));
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS score_frame TEXT NOT NULL DEFAULT 'gain_frame' CHECK (score_frame IN ('gain_frame', 'loss_frame'));
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS monthly_score_feedback TEXT NOT NULL DEFAULT 'displayed' CHECK (monthly_score_feedback IN ('displayed', 'hidden'));
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS prolific_pid TEXT;
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS prolific_study_id TEXT;
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS prolific_session_id TEXT;
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS prolific_account_key TEXT;
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS prolific_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS prolific_finished_at TIMESTAMPTZ;
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS prolific_completion_redirected_at TIMESTAMPTZ;
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS completion_code TEXT;
ALTER TABLE participant_sessions
  DROP CONSTRAINT IF EXISTS participant_sessions_completion_code_key;
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS duplicate_entry BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS missing_prolific_params BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS anti_ai_declaration BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS anti_ai_declared_at TIMESTAMPTZ;
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS comprehension_attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS comprehension_passed BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE participant_sessions
  ADD COLUMN IF NOT EXISTS attention_failed_count INTEGER NOT NULL DEFAULT 0;
CREATE UNIQUE INDEX IF NOT EXISTS participant_sessions_study_participant_code_idx
  ON participant_sessions (study_session_id, participant_code)
  WHERE study_session_id IS NOT NULL AND participant_code IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS participant_sessions_prolific_unique_idx
  ON participant_sessions (prolific_pid, prolific_study_id)
  WHERE prolific_pid IS NOT NULL AND prolific_study_id IS NOT NULL;

ALTER TABLE participant_sessions ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS admin_study_sessions (
  id UUID PRIMARY KEY,
  session_code TEXT NOT NULL UNIQUE CHECK (session_code ~ '^[0-9]{6}$'),
  created_by_email TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE admin_study_sessions ENABLE ROW LEVEL SECURITY;

ALTER TABLE admin_study_sessions
  ADD COLUMN IF NOT EXISTS experimental_condition TEXT NOT NULL DEFAULT 'C1' CHECK (experimental_condition IN ('C1', 'C2', 'C3', 'C4'));
ALTER TABLE admin_study_sessions
  ADD COLUMN IF NOT EXISTS score_frame TEXT NOT NULL DEFAULT 'gain_frame' CHECK (score_frame IN ('gain_frame', 'loss_frame'));
ALTER TABLE admin_study_sessions
  ADD COLUMN IF NOT EXISTS monthly_score_feedback TEXT NOT NULL DEFAULT 'displayed' CHECK (monthly_score_feedback IN ('displayed', 'hidden'));

CREATE TABLE IF NOT EXISTS psychometric_pre_answers (
  session_id UUID NOT NULL REFERENCES participant_sessions(id) ON DELETE CASCADE,
  study_session_id UUID,
  study_session_code TEXT,
  participant_code TEXT CHECK (participant_code IS NULL OR participant_code ~ '^P[0-9]{3}$'),
  section_number INTEGER NOT NULL,
  question_number INTEGER NOT NULL,
  question_key TEXT NOT NULL,
  question_text TEXT NOT NULL,
  answer_value SMALLINT NOT NULL CHECK (answer_value BETWEEN 1 AND 5),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (session_id, question_key),
  UNIQUE (session_id, question_number)
);
CREATE INDEX IF NOT EXISTS psychometric_pre_answers_study_participant_idx
  ON psychometric_pre_answers (study_session_id, participant_code);

CREATE TABLE IF NOT EXISTS psychometric_post_answers (
  session_id UUID NOT NULL REFERENCES participant_sessions(id) ON DELETE CASCADE,
  study_session_id UUID,
  study_session_code TEXT,
  participant_code TEXT CHECK (participant_code IS NULL OR participant_code ~ '^P[0-9]{3}$'),
  section_number INTEGER NOT NULL,
  question_number INTEGER NOT NULL,
  question_key TEXT NOT NULL,
  question_text TEXT NOT NULL,
  answer_value SMALLINT NOT NULL CHECK (answer_value BETWEEN 1 AND 5),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (session_id, question_key),
  UNIQUE (session_id, question_number)
);
CREATE INDEX IF NOT EXISTS psychometric_post_answers_study_participant_idx
  ON psychometric_post_answers (study_session_id, participant_code);

CREATE TABLE IF NOT EXISTS month_results (
  session_id UUID NOT NULL REFERENCES participant_sessions(id) ON DELETE CASCADE,
  study_session_id UUID,
  study_session_code TEXT,
  participant_code TEXT CHECK (participant_code IS NULL OR participant_code ~ '^P[0-9]{3}$'),
  month_number SMALLINT NOT NULL CHECK (month_number BETWEEN 1 AND 24),
  opening_balance NUMERIC(12,2),
  income_total NUMERIC(12,2),
  expenses_total NUMERIC(12,2),
  loan_obligation NUMERIC(12,2),
  credit_interest NUMERIC(12,2),
  overdraft_interest NUMERIC(12,2),
  penalties NUMERIC(12,2),
  available_total NUMERIC(12,2),
  outflows_before_credit NUMERIC(12,2),
  deficit_before_credit NUMERIC(12,2),
  liquidity_before_payment NUMERIC(12,2),
  overdraft_after_charges NUMERIC(12,2),
  overdraft_remaining NUMERIC(12,2),
  max_payment NUMERIC(12,2),
  payment_input NUMERIC(12,2),
  accepted_payment NUMERIC(12,2),
  overdraft_from_payment NUMERIC(12,2),
  overdraft_final NUMERIC(12,2),
  cash_final NUMERIC(12,2),
  credit_final NUMERIC(12,2),
  score_repayment NUMERIC(6,2),
  score_liquidity NUMERIC(6,2),
  score_overdraft NUMERIC(6,2),
  monthly_score NUMERIC(6,2),
  bonus_lunar NUMERIC(12,4),
  costs_this_month NUMERIC(12,2),
  feedback_message TEXT,
  invalid_reason TEXT,
  pre_credit_impossible BOOLEAN,
  payment_valid BOOLEAN,
  score_model TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (session_id, month_number)
);
CREATE INDEX IF NOT EXISTS month_results_study_participant_idx
  ON month_results (study_session_id, participant_code);

CREATE TABLE IF NOT EXISTS session_summaries (
  session_id UUID PRIMARY KEY REFERENCES participant_sessions(id) ON DELETE CASCADE,
  months_completed INTEGER NOT NULL DEFAULT 0,
  monthly_score_sum NUMERIC(8,2),
  final_score NUMERIC(6,2),
  bonus_max_session NUMERIC(12,2),
  bonus_final NUMERIC(12,2),
  experimental_condition TEXT NOT NULL DEFAULT 'C1' CHECK (experimental_condition IN ('C1', 'C2', 'C3', 'C4')),
  score_frame TEXT NOT NULL DEFAULT 'gain_frame' CHECK (score_frame IN ('gain_frame', 'loss_frame')),
  monthly_score_feedback TEXT NOT NULL DEFAULT 'displayed' CHECK (monthly_score_feedback IN ('displayed', 'hidden')),
  performance_bonus_gbp NUMERIC(6,2) NOT NULL DEFAULT 0,
  loss_amount_gbp NUMERIC(6,2) NOT NULL DEFAULT 0,
  prolific_base_reward_gbp NUMERIC(6,2) NOT NULL DEFAULT 5,
  total_payout_gbp NUMERIC(6,2) NOT NULL DEFAULT 5,
  prolific_bonus_status TEXT NOT NULL DEFAULT 'not_applicable',
  prolific_bonus_payment_id TEXT,
  prolific_bonus_created_at TIMESTAMPTZ,
  prolific_bonus_paid_at TIMESTAMPTZ,
  prolific_bonus_error TEXT,
  completion_timestamp TIMESTAMPTZ,
  payment_status TEXT NOT NULL DEFAULT 'unpaid',
  total_repaid NUMERIC(12,2),
  remaining_credit NUMERIC(12,2),
  remaining_overdraft NUMERIC(12,2),
  credit_interest_total NUMERIC(12,2),
  overdraft_interest_total NUMERIC(12,2),
  interest_total NUMERIC(12,2),
  study_session_id UUID,
  study_session_code TEXT,
  participant_code TEXT CHECK (participant_code IS NULL OR participant_code ~ '^P[0-9]{3}$'),
  prolific_pid TEXT,
  prolific_study_id TEXT,
  prolific_session_id TEXT,
  completion_code TEXT,
  feedback TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS session_summaries_study_participant_idx
  ON session_summaries (study_session_id, participant_code);

CREATE TABLE IF NOT EXISTS resume_links (
  account_key TEXT PRIMARY KEY CHECK (char_length(account_key) = 64),
  session_id UUID NOT NULL UNIQUE REFERENCES participant_sessions(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS completed_accounts (
  account_key TEXT PRIMARY KEY CHECK (char_length(account_key) = 64),
  completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE psychometric_pre_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE psychometric_post_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE month_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_summaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE completed_accounts ENABLE ROW LEVEL SECURITY;

ALTER TABLE psychometric_pre_answers
  ADD COLUMN IF NOT EXISTS study_session_id UUID;
ALTER TABLE psychometric_pre_answers
  ADD COLUMN IF NOT EXISTS study_session_code TEXT;
ALTER TABLE psychometric_pre_answers
  ADD COLUMN IF NOT EXISTS participant_code TEXT CHECK (participant_code IS NULL OR participant_code ~ '^P[0-9]{3}$');

ALTER TABLE psychometric_post_answers
  ADD COLUMN IF NOT EXISTS study_session_id UUID;
ALTER TABLE psychometric_post_answers
  ADD COLUMN IF NOT EXISTS study_session_code TEXT;
ALTER TABLE psychometric_post_answers
  ADD COLUMN IF NOT EXISTS participant_code TEXT CHECK (participant_code IS NULL OR participant_code ~ '^P[0-9]{3}$');

ALTER TABLE month_results
  ADD COLUMN IF NOT EXISTS study_session_id UUID;
ALTER TABLE month_results
  ADD COLUMN IF NOT EXISTS study_session_code TEXT;
ALTER TABLE month_results
  ADD COLUMN IF NOT EXISTS participant_code TEXT CHECK (participant_code IS NULL OR participant_code ~ '^P[0-9]{3}$');

ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS participant_code TEXT CHECK (participant_code IS NULL OR participant_code ~ '^P[0-9]{3}$');
ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS experimental_condition TEXT NOT NULL DEFAULT 'C1' CHECK (experimental_condition IN ('C1', 'C2', 'C3', 'C4'));
ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS score_frame TEXT NOT NULL DEFAULT 'gain_frame' CHECK (score_frame IN ('gain_frame', 'loss_frame'));
ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS monthly_score_feedback TEXT NOT NULL DEFAULT 'displayed' CHECK (monthly_score_feedback IN ('displayed', 'hidden'));
ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS performance_bonus_gbp NUMERIC(6,2) NOT NULL DEFAULT 0;
ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS loss_amount_gbp NUMERIC(6,2) NOT NULL DEFAULT 0;
ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS prolific_base_reward_gbp NUMERIC(6,2) NOT NULL DEFAULT 5;
ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS total_payout_gbp NUMERIC(6,2) NOT NULL DEFAULT 5;
ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS prolific_bonus_status TEXT NOT NULL DEFAULT 'not_applicable';
ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS prolific_bonus_payment_id TEXT;
ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS prolific_bonus_created_at TIMESTAMPTZ;
ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS prolific_bonus_paid_at TIMESTAMPTZ;
ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS prolific_bonus_error TEXT;
ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS completion_timestamp TIMESTAMPTZ;
ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS payment_status TEXT NOT NULL DEFAULT 'unpaid';
ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS prolific_pid TEXT;
ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS prolific_study_id TEXT;
ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS prolific_session_id TEXT;
ALTER TABLE session_summaries
  ADD COLUMN IF NOT EXISTS completion_code TEXT;

CREATE TABLE IF NOT EXISTS quality_checks (
  id BIGSERIAL PRIMARY KEY,
  app_session_id UUID REFERENCES participant_sessions(id) ON DELETE CASCADE,
  prolific_pid TEXT,
  study_id TEXT,
  session_id TEXT,
  page_id TEXT,
  check_type TEXT NOT NULL,
  check_id TEXT NOT NULL,
  attempt_number INTEGER NOT NULL DEFAULT 1,
  passed BOOLEAN NOT NULL,
  response_value TEXT,
  response_time_ms INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS quality_checks_app_session_idx
  ON quality_checks (app_session_id);
CREATE INDEX IF NOT EXISTS quality_checks_prolific_idx
  ON quality_checks (prolific_pid, study_id, session_id);

CREATE TABLE IF NOT EXISTS page_progress (
  id BIGSERIAL PRIMARY KEY,
  app_session_id UUID REFERENCES participant_sessions(id) ON DELETE CASCADE,
  prolific_pid TEXT,
  study_id TEXT,
  session_id TEXT,
  page_order INTEGER NOT NULL,
  page_id TEXT NOT NULL,
  entered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  completed BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS page_progress_app_session_idx
  ON page_progress (app_session_id, page_order);

ALTER TABLE quality_checks ENABLE ROW LEVEL SECURITY;
ALTER TABLE page_progress ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS psychometric_pre_answers_study_participant_idx
  ON psychometric_pre_answers (study_session_id, participant_code);
CREATE INDEX IF NOT EXISTS psychometric_post_answers_study_participant_idx
  ON psychometric_post_answers (study_session_id, participant_code);
CREATE INDEX IF NOT EXISTS month_results_study_participant_idx
  ON month_results (study_session_id, participant_code);
CREATE INDEX IF NOT EXISTS session_summaries_study_participant_idx
  ON session_summaries (study_session_id, participant_code);


-- ===== PHASE 3 PERSISTENCE HARDENING =====

-- Phase 3: atomic, versioned and idempotent experiment persistence.
-- Apply after setup.sql and migration_structured_results.sql.
-- This migration is additive and preserves existing research rows.

BEGIN;

ALTER TABLE public.participant_sessions
  ADD COLUMN IF NOT EXISTS state_version BIGINT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS current_month SMALLINT NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS loan_balance NUMERIC(12,2) NOT NULL DEFAULT 7000.00,
  ADD COLUMN IF NOT EXISTS overdraft_balance NUMERIC(12,2) NOT NULL DEFAULT 0.00,
  ADD COLUMN IF NOT EXISTS total_score NUMERIC(12,2) NOT NULL DEFAULT 0.00,
  ADD COLUMN IF NOT EXISTS monthly_points NUMERIC(12,2) NOT NULL DEFAULT 0.00,
  ADD COLUMN IF NOT EXISTS accumulated_costs NUMERIC(12,2) NOT NULL DEFAULT 0.00,
  ADD COLUMN IF NOT EXISTS pending_month_number SMALLINT,
  ADD COLUMN IF NOT EXISTS treatment_bound BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS completion_status TEXT NOT NULL DEFAULT 'not_started',
  ADD COLUMN IF NOT EXISTS finalization_request_id TEXT,
  ADD COLUMN IF NOT EXISTS last_transition_at TIMESTAMPTZ;

ALTER TABLE public.participant_sessions
  DROP CONSTRAINT IF EXISTS participant_sessions_current_month_check,
  ADD CONSTRAINT participant_sessions_current_month_check CHECK (current_month BETWEEN 1 AND 25),
  DROP CONSTRAINT IF EXISTS participant_sessions_pending_month_check,
  ADD CONSTRAINT participant_sessions_pending_month_check CHECK (pending_month_number IS NULL OR pending_month_number BETWEEN 1 AND 24),
  DROP CONSTRAINT IF EXISTS participant_sessions_completion_status_check,
  ADD CONSTRAINT participant_sessions_completion_status_check CHECK (
    completion_status IN ('not_started', 'internal_finalized', 'payment_pending', 'payment_processing', 'payment_manual_review', 'complete')
  );

ALTER TABLE public.month_results
  ADD COLUMN IF NOT EXISTS loan_balance_before_payment NUMERIC(12,2),
  ADD COLUMN IF NOT EXISTS result_json JSONB,
  ADD COLUMN IF NOT EXISTS decision_request_id TEXT,
  ADD COLUMN IF NOT EXISTS committed_state_version BIGINT;

CREATE UNIQUE INDEX IF NOT EXISTS month_results_decision_request_idx
  ON public.month_results (session_id, decision_request_id)
  WHERE decision_request_id IS NOT NULL;

ALTER TABLE public.quality_checks
  ADD COLUMN IF NOT EXISTS request_id TEXT,
  ADD COLUMN IF NOT EXISTS event_index INTEGER;

CREATE UNIQUE INDEX IF NOT EXISTS quality_checks_request_event_idx
  ON public.quality_checks (app_session_id, request_id, event_index)
  WHERE request_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.experiment_idempotency (
  session_id UUID NOT NULL REFERENCES public.participant_sessions(id) ON DELETE CASCADE,
  operation TEXT NOT NULL,
  request_id TEXT NOT NULL,
  payload_hash TEXT NOT NULL CHECK (char_length(payload_hash) = 64),
  response_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (session_id, operation, request_id)
);
CREATE INDEX IF NOT EXISTS experiment_idempotency_created_idx
  ON public.experiment_idempotency (created_at);

ALTER TABLE public.session_summaries
  ADD COLUMN IF NOT EXISTS finalization_status TEXT NOT NULL DEFAULT 'not_started',
  ADD COLUMN IF NOT EXISTS finalization_request_id TEXT,
  ADD COLUMN IF NOT EXISTS payment_idempotency_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS session_summaries_finalization_request_idx
  ON public.session_summaries (session_id, finalization_request_id)
  WHERE finalization_request_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.prolific_payment_attempts (
  session_id UUID PRIMARY KEY REFERENCES public.participant_sessions(id) ON DELETE CASCADE,
  request_id TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL CHECK (status IN ('pending', 'processing', 'succeeded', 'manual_review', 'not_applicable', 'not_configured')),
  external_reference TEXT,
  response_json JSONB,
  last_error TEXT,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Existing sessions with a durable binding must not be rebound.
UPDATE public.participant_sessions
SET treatment_bound = TRUE
WHERE treatment_bound = FALSE
  AND (prolific_pid IS NOT NULL OR study_session_id IS NOT NULL OR COALESCE((checkpoint->>'month')::INTEGER, 1) > 1);

CREATE OR REPLACE FUNCTION public.prevent_treatment_rebinding_v3()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF OLD.treatment_bound AND (
    NEW.experimental_condition IS DISTINCT FROM OLD.experimental_condition OR
    NEW.score_frame IS DISTINCT FROM OLD.score_frame OR
    NEW.monthly_score_feedback IS DISTINCT FROM OLD.monthly_score_feedback OR
    NEW.study_session_id IS DISTINCT FROM OLD.study_session_id OR
    NEW.participant_code IS DISTINCT FROM OLD.participant_code
  ) THEN
    RAISE EXCEPTION 'SIM_TREATMENT_CONFLICT: treatment is already bound';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS participant_sessions_treatment_immutable_v3 ON public.participant_sessions;
CREATE TRIGGER participant_sessions_treatment_immutable_v3
BEFORE UPDATE ON public.participant_sessions
FOR EACH ROW EXECUTE FUNCTION public.prevent_treatment_rebinding_v3();

CREATE OR REPLACE FUNCTION public.insert_month_result_v3(p_session_id UUID, p_result JSONB)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
  INSERT INTO public.month_results (
    session_id, study_session_id, study_session_code, participant_code,
    month_number, opening_balance, income_total, expenses_total,
    loan_balance_before_payment, loan_obligation, credit_interest,
    overdraft_interest, penalties, available_total, outflows_before_credit,
    deficit_before_credit, liquidity_before_payment, overdraft_after_charges,
    overdraft_remaining, max_payment, payment_input, accepted_payment,
    overdraft_from_payment, overdraft_final, cash_final, credit_final,
    score_repayment, score_liquidity, score_overdraft, monthly_score,
    bonus_lunar, costs_this_month, feedback_message, invalid_reason,
    pre_credit_impossible, payment_valid, score_model, result_json,
    decision_request_id, committed_state_version, updated_at
  ) VALUES (
    p_session_id,
    NULLIF(p_result->>'study_session_id', '')::UUID,
    p_result->>'study_session_code', p_result->>'participant_code',
    (p_result->>'month_number')::SMALLINT,
    (p_result->>'opening_balance')::NUMERIC,
    (p_result->>'income_total')::NUMERIC,
    (p_result->>'expenses_total')::NUMERIC,
    (p_result->>'loan_balance_before_payment')::NUMERIC,
    (p_result->>'loan_obligation')::NUMERIC,
    (p_result->>'credit_interest')::NUMERIC,
    (p_result->>'overdraft_interest')::NUMERIC,
    (p_result->>'penalties')::NUMERIC,
    (p_result->>'available_total')::NUMERIC,
    (p_result->>'outflows_before_credit')::NUMERIC,
    (p_result->>'deficit_before_credit')::NUMERIC,
    (p_result->>'liquidity_before_payment')::NUMERIC,
    (p_result->>'overdraft_after_charges')::NUMERIC,
    (p_result->>'overdraft_remaining')::NUMERIC,
    (p_result->>'max_payment')::NUMERIC,
    (p_result->>'payment_input')::NUMERIC,
    (p_result->>'accepted_payment')::NUMERIC,
    (p_result->>'overdraft_from_payment')::NUMERIC,
    (p_result->>'overdraft_final')::NUMERIC,
    (p_result->>'cash_final')::NUMERIC,
    (p_result->>'credit_final')::NUMERIC,
    (p_result->>'score_repayment')::NUMERIC,
    (p_result->>'score_liquidity')::NUMERIC,
    (p_result->>'score_overdraft')::NUMERIC,
    (p_result->>'monthly_score')::NUMERIC,
    (p_result->>'bonus_lunar')::NUMERIC,
    (p_result->>'costs_this_month')::NUMERIC,
    p_result->>'feedback_message', p_result->>'invalid_reason',
    (p_result->>'pre_credit_impossible')::BOOLEAN,
    (p_result->>'payment_valid')::BOOLEAN,
    p_result->>'score_model',
    COALESCE(p_result->'result_json', p_result),
    p_result->>'decision_request_id',
    (p_result->>'committed_state_version')::BIGINT,
    COALESCE((p_result->>'updated_at')::TIMESTAMPTZ, NOW())
  )
  ON CONFLICT (session_id, month_number) DO NOTHING;
END;
$$;

CREATE OR REPLACE FUNCTION public.claim_participant_session_v3(
  p_session_id UUID,
  p_account_key TEXT,
  p_request_id TEXT,
  p_payload_hash TEXT,
  p_state JSONB
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_linked UUID;
  v_response JSONB;
BEGIN
  PERFORM pg_advisory_xact_lock(hashtextextended(p_account_key, 0));
  SELECT session_id INTO v_linked FROM public.resume_links WHERE account_key = p_account_key FOR UPDATE;
  IF v_linked IS NOT NULL THEN
    RETURN jsonb_build_object('session_id', v_linked, 'idempotency_hit', TRUE);
  END IF;

  INSERT INTO public.participant_sessions (
    id, status, current_page, checkpoint, state_version, current_month,
    loan_balance, overdraft_balance, total_score, monthly_points,
    accumulated_costs, study_session_id, study_session_code, participant_code,
    prolific_pid, prolific_study_id, prolific_session_id,
    experimental_condition, score_frame, monthly_score_feedback,
    treatment_bound, completion_status, updated_at
  ) VALUES (
    p_session_id, 'in_progress', COALESCE(p_state->>'page', 'home'),
    COALESCE(p_state->'resume_projection', '{}'::JSONB), 0,
    COALESCE((p_state->>'current_month')::SMALLINT, 1),
    COALESCE((p_state->>'loan_balance')::NUMERIC, 7000),
    COALESCE((p_state->>'overdraft_balance')::NUMERIC, 0),
    COALESCE((p_state->>'total_score')::NUMERIC, 0),
    COALESCE((p_state->>'monthly_points')::NUMERIC, 0),
    COALESCE((p_state->>'accumulated_costs')::NUMERIC, 0),
    NULLIF(p_state->>'study_session_id', '')::UUID,
    p_state->>'study_session_code', p_state->>'participant_code',
    p_state->>'prolific_pid', p_state->>'prolific_study_id', p_state->>'prolific_session_id',
    COALESCE(p_state->>'experimental_condition', 'C1'),
    COALESCE(p_state->>'score_frame', 'gain_frame'),
    COALESCE(p_state->>'monthly_score_feedback', 'displayed'),
    COALESCE((p_state->>'treatment_bound')::BOOLEAN, FALSE),
    'not_started', NOW()
  ) ON CONFLICT (id) DO NOTHING;

  INSERT INTO public.resume_links (account_key, session_id, updated_at)
  VALUES (p_account_key, p_session_id, NOW());

  v_response := jsonb_build_object('session_id', p_session_id, 'state_version', 0, 'idempotency_hit', FALSE);
  INSERT INTO public.experiment_idempotency(session_id, operation, request_id, payload_hash, response_json)
  VALUES (p_session_id, 'create_session', p_request_id, p_payload_hash, v_response)
  ON CONFLICT DO NOTHING;
  RETURN v_response;
END;
$$;

CREATE OR REPLACE FUNCTION public.commit_stage_transition_v3(
  p_session_id UUID,
  p_expected_version BIGINT,
  p_request_id TEXT,
  p_payload_hash TEXT,
  p_state JSONB
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row public.participant_sessions%ROWTYPE;
  v_idem public.experiment_idempotency%ROWTYPE;
  v_response JSONB;
BEGIN
  SELECT * INTO v_idem FROM public.experiment_idempotency
   WHERE session_id=p_session_id AND operation='save_stage' AND request_id=p_request_id;
  IF FOUND THEN
    IF v_idem.payload_hash <> p_payload_hash THEN RAISE EXCEPTION 'SIM_IDEMPOTENCY_CONFLICT'; END IF;
    RETURN v_idem.response_json || jsonb_build_object('idempotency_hit', TRUE);
  END IF;

  SELECT * INTO v_row FROM public.participant_sessions WHERE id=p_session_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'SIM_NOT_FOUND'; END IF;
  SELECT * INTO v_idem FROM public.experiment_idempotency
   WHERE session_id=p_session_id AND operation='save_stage' AND request_id=p_request_id;
  IF FOUND THEN
    IF v_idem.payload_hash <> p_payload_hash THEN RAISE EXCEPTION 'SIM_IDEMPOTENCY_CONFLICT'; END IF;
    RETURN v_idem.response_json || jsonb_build_object('idempotency_hit', TRUE);
  END IF;
  IF v_row.status='completed' THEN RAISE EXCEPTION 'SIM_CONFLICT: completed participant state is immutable'; END IF;
  IF v_row.state_version <> p_expected_version THEN RAISE EXCEPTION 'SIM_CONFLICT: stale state version'; END IF;
  IF v_row.treatment_bound AND (
    v_row.experimental_condition IS DISTINCT FROM p_state->>'experimental_condition' OR
    v_row.score_frame IS DISTINCT FROM p_state->>'score_frame' OR
    v_row.monthly_score_feedback IS DISTINCT FROM p_state->>'monthly_score_feedback'
  ) THEN RAISE EXCEPTION 'SIM_TREATMENT_CONFLICT'; END IF;

  UPDATE public.participant_sessions SET
    current_page=COALESCE(p_state->>'page', current_page),
    checkpoint=COALESCE(p_state->'resume_projection', checkpoint),
    study_session_id=CASE WHEN treatment_bound THEN study_session_id ELSE NULLIF(p_state->>'study_session_id','')::UUID END,
    study_session_code=CASE WHEN treatment_bound THEN study_session_code ELSE p_state->>'study_session_code' END,
    participant_code=CASE WHEN treatment_bound THEN participant_code ELSE p_state->>'participant_code' END,
    prolific_pid=COALESCE(prolific_pid, p_state->>'prolific_pid'),
    prolific_study_id=COALESCE(prolific_study_id, p_state->>'prolific_study_id'),
    prolific_session_id=COALESCE(prolific_session_id, p_state->>'prolific_session_id'),
    experimental_condition=CASE WHEN treatment_bound THEN experimental_condition ELSE COALESCE(p_state->>'experimental_condition', experimental_condition) END,
    score_frame=CASE WHEN treatment_bound THEN score_frame ELSE COALESCE(p_state->>'score_frame', score_frame) END,
    monthly_score_feedback=CASE WHEN treatment_bound THEN monthly_score_feedback ELSE COALESCE(p_state->>'monthly_score_feedback', monthly_score_feedback) END,
    treatment_bound=treatment_bound OR COALESCE((p_state->>'treatment_bound')::BOOLEAN,FALSE),
    comprehension_attempts=COALESCE((p_state->'resume_projection'->>'comprehension_attempts')::INTEGER, comprehension_attempts),
    comprehension_passed=COALESCE((p_state->'resume_projection'->>'comprehension_passed')::BOOLEAN, comprehension_passed),
    attention_failed_count=COALESCE((p_state->'resume_projection'->>'attention_failed_count')::INTEGER, attention_failed_count),
    state_version=state_version+1, last_transition_at=NOW(), updated_at=NOW()
  WHERE id=p_session_id;

  v_response := jsonb_build_object('session_id',p_session_id,'state_version',p_expected_version+1,'idempotency_hit',FALSE);
  INSERT INTO public.experiment_idempotency VALUES (p_session_id,'save_stage',p_request_id,p_payload_hash,v_response,NOW());
  RETURN v_response;
END;
$$;

CREATE OR REPLACE FUNCTION public.commit_quality_transition_v3(
  p_session_id UUID,
  p_expected_version BIGINT,
  p_request_id TEXT,
  p_payload_hash TEXT,
  p_state JSONB,
  p_events JSONB
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row public.participant_sessions%ROWTYPE;
  v_idem public.experiment_idempotency%ROWTYPE;
  v_event JSONB;
  v_event_index INTEGER;
  v_response JSONB;
BEGIN
  SELECT * INTO v_idem FROM public.experiment_idempotency
   WHERE session_id=p_session_id AND operation='quality_transition' AND request_id=p_request_id;
  IF FOUND THEN
    IF v_idem.payload_hash <> p_payload_hash THEN RAISE EXCEPTION 'SIM_IDEMPOTENCY_CONFLICT'; END IF;
    RETURN v_idem.response_json || jsonb_build_object('idempotency_hit', TRUE);
  END IF;

  SELECT * INTO v_row FROM public.participant_sessions WHERE id=p_session_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'SIM_NOT_FOUND'; END IF;
  SELECT * INTO v_idem FROM public.experiment_idempotency
   WHERE session_id=p_session_id AND operation='quality_transition' AND request_id=p_request_id;
  IF FOUND THEN
    IF v_idem.payload_hash <> p_payload_hash THEN RAISE EXCEPTION 'SIM_IDEMPOTENCY_CONFLICT'; END IF;
    RETURN v_idem.response_json || jsonb_build_object('idempotency_hit', TRUE);
  END IF;
  IF v_row.status='completed' THEN RAISE EXCEPTION 'SIM_CONFLICT: completed participant state is immutable'; END IF;
  IF v_row.state_version <> p_expected_version THEN RAISE EXCEPTION 'SIM_CONFLICT: stale quality transition'; END IF;

  FOR v_event, v_event_index IN
    SELECT value, ordinality::INTEGER
    FROM jsonb_array_elements(COALESCE(p_events, '[]'::JSONB)) WITH ORDINALITY
  LOOP
    INSERT INTO public.quality_checks (
      app_session_id, prolific_pid, study_id, session_id, page_id,
      check_type, check_id, attempt_number, passed, response_value,
      response_time_ms, request_id, event_index, created_at
    ) VALUES (
      p_session_id, p_state->>'prolific_pid', p_state->>'prolific_study_id',
      p_state->>'prolific_session_id', v_event->>'page_id',
      v_event->>'check_type', v_event->>'check_id',
      COALESCE((v_event->>'attempt_number')::INTEGER, 1),
      COALESCE((v_event->>'passed')::BOOLEAN, FALSE),
      v_event->>'response_value', (v_event->>'response_time_ms')::INTEGER,
      p_request_id, v_event_index, NOW()
    );
  END LOOP;

  UPDATE public.participant_sessions SET
    current_page=COALESCE(p_state->>'page', current_page),
    checkpoint=COALESCE(p_state->'resume_projection', checkpoint),
    comprehension_attempts=COALESCE((p_state->'resume_projection'->>'comprehension_attempts')::INTEGER, comprehension_attempts),
    comprehension_passed=COALESCE((p_state->'resume_projection'->>'comprehension_passed')::BOOLEAN, comprehension_passed),
    attention_failed_count=COALESCE((p_state->'resume_projection'->>'attention_failed_count')::INTEGER, attention_failed_count),
    state_version=state_version+1, last_transition_at=NOW(), updated_at=NOW()
  WHERE id=p_session_id;

  v_response := jsonb_build_object(
    'session_id', p_session_id, 'state_version', p_expected_version+1,
    'quality_event_count', jsonb_array_length(COALESCE(p_events, '[]'::JSONB)),
    'idempotency_hit', FALSE
  );
  INSERT INTO public.experiment_idempotency
    VALUES (p_session_id,'quality_transition',p_request_id,p_payload_hash,v_response,NOW());
  RETURN v_response;
END;
$$;

CREATE OR REPLACE FUNCTION public.commit_month_decision_v3(
  p_session_id UUID,
  p_expected_version BIGINT,
  p_expected_month SMALLINT,
  p_request_id TEXT,
  p_payload_hash TEXT,
  p_state JSONB,
  p_result JSONB
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row public.participant_sessions%ROWTYPE;
  v_idem public.experiment_idempotency%ROWTYPE;
  v_response JSONB;
BEGIN
  SELECT * INTO v_idem FROM public.experiment_idempotency
   WHERE session_id=p_session_id AND operation='month_decision' AND request_id=p_request_id;
  IF FOUND THEN
    IF v_idem.payload_hash <> p_payload_hash THEN RAISE EXCEPTION 'SIM_IDEMPOTENCY_CONFLICT'; END IF;
    RETURN v_idem.response_json || jsonb_build_object('idempotency_hit',TRUE);
  END IF;
  SELECT * INTO v_row FROM public.participant_sessions WHERE id=p_session_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'SIM_NOT_FOUND'; END IF;
  SELECT * INTO v_idem FROM public.experiment_idempotency
   WHERE session_id=p_session_id AND operation='month_decision' AND request_id=p_request_id;
  IF FOUND THEN
    IF v_idem.payload_hash <> p_payload_hash THEN RAISE EXCEPTION 'SIM_IDEMPOTENCY_CONFLICT'; END IF;
    RETURN v_idem.response_json || jsonb_build_object('idempotency_hit',TRUE);
  END IF;
  IF v_row.state_version <> p_expected_version OR v_row.current_month <> p_expected_month THEN
    RAISE EXCEPTION 'SIM_MONTH_CONFLICT: stale version or month';
  END IF;
  IF v_row.status='completed' OR v_row.current_page<>'simulation' OR v_row.pending_month_number IS NOT NULL THEN
    RAISE EXCEPTION 'SIM_CONFLICT: invalid month-decision stage';
  END IF;
  IF v_row.treatment_bound AND v_row.experimental_condition IS DISTINCT FROM p_state->>'experimental_condition' THEN
    RAISE EXCEPTION 'SIM_TREATMENT_CONFLICT';
  END IF;
  IF EXISTS (SELECT 1 FROM public.month_results WHERE session_id=p_session_id AND month_number=p_expected_month) THEN
    RAISE EXCEPTION 'SIM_MONTH_CONFLICT: result already exists';
  END IF;

  PERFORM public.insert_month_result_v3(p_session_id, p_result);
  UPDATE public.participant_sessions SET
    current_page='month_feedback', checkpoint=COALESCE(p_state->'resume_projection','{}'::JSONB),
    loan_balance=(p_state->>'loan_balance')::NUMERIC,
    overdraft_balance=(p_state->>'overdraft_balance')::NUMERIC,
    total_score=(p_state->>'total_score')::NUMERIC,
    monthly_points=(p_state->>'monthly_points')::NUMERIC,
    accumulated_costs=(p_state->>'accumulated_costs')::NUMERIC,
    pending_month_number=p_expected_month,
    experimental_condition=CASE WHEN treatment_bound THEN experimental_condition ELSE p_state->>'experimental_condition' END,
    score_frame=CASE WHEN treatment_bound THEN score_frame ELSE p_state->>'score_frame' END,
    monthly_score_feedback=CASE WHEN treatment_bound THEN monthly_score_feedback ELSE p_state->>'monthly_score_feedback' END,
    treatment_bound=TRUE, state_version=state_version+1, last_transition_at=NOW(), updated_at=NOW()
  WHERE id=p_session_id;

  v_response := jsonb_build_object(
    'session_id',p_session_id,'state_version',p_expected_version+1,
    'result',COALESCE(p_result->'result_json',p_result),'idempotency_hit',FALSE
  );
  INSERT INTO public.experiment_idempotency VALUES (p_session_id,'month_decision',p_request_id,p_payload_hash,v_response,NOW());
  RETURN v_response;
END;
$$;

CREATE OR REPLACE FUNCTION public.acknowledge_month_feedback_v3(
  p_session_id UUID,
  p_expected_version BIGINT,
  p_expected_month SMALLINT,
  p_request_id TEXT,
  p_payload_hash TEXT,
  p_state JSONB
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row public.participant_sessions%ROWTYPE;
  v_idem public.experiment_idempotency%ROWTYPE;
  v_result JSONB;
  v_response JSONB;
BEGIN
  SELECT * INTO v_idem FROM public.experiment_idempotency
   WHERE session_id=p_session_id AND operation='feedback_ack' AND request_id=p_request_id;
  IF FOUND THEN
    IF v_idem.payload_hash <> p_payload_hash THEN RAISE EXCEPTION 'SIM_IDEMPOTENCY_CONFLICT'; END IF;
    RETURN v_idem.response_json || jsonb_build_object('idempotency_hit',TRUE);
  END IF;
  SELECT * INTO v_row FROM public.participant_sessions WHERE id=p_session_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'SIM_NOT_FOUND'; END IF;
  SELECT * INTO v_idem FROM public.experiment_idempotency
   WHERE session_id=p_session_id AND operation='feedback_ack' AND request_id=p_request_id;
  IF FOUND THEN
    IF v_idem.payload_hash <> p_payload_hash THEN RAISE EXCEPTION 'SIM_IDEMPOTENCY_CONFLICT'; END IF;
    RETURN v_idem.response_json || jsonb_build_object('idempotency_hit',TRUE);
  END IF;
  IF v_row.state_version<>p_expected_version OR v_row.current_page<>'month_feedback' OR
     v_row.current_month<>p_expected_month OR v_row.pending_month_number<>p_expected_month THEN
    RAISE EXCEPTION 'SIM_MONTH_CONFLICT: feedback is no longer pending';
  END IF;
  SELECT COALESCE(result_json,to_jsonb(m)) INTO v_result FROM public.month_results m
   WHERE session_id=p_session_id AND month_number=p_expected_month;
  IF v_result IS NULL THEN RAISE EXCEPTION 'SIM_CONFLICT: durable month result missing'; END IF;

  UPDATE public.participant_sessions SET
    current_page='simulation', current_month=p_expected_month+1,
    pending_month_number=NULL, checkpoint=COALESCE(p_state->'resume_projection','{}'::JSONB),
    state_version=state_version+1, last_transition_at=NOW(), updated_at=NOW()
  WHERE id=p_session_id;
  v_response := jsonb_build_object('session_id',p_session_id,'state_version',p_expected_version+1,'result',v_result,'idempotency_hit',FALSE);
  INSERT INTO public.experiment_idempotency VALUES (p_session_id,'feedback_ack',p_request_id,p_payload_hash,v_response,NOW());
  RETURN v_response;
END;
$$;

CREATE OR REPLACE FUNCTION public.backfill_legacy_session_v3(
  p_session_id UUID,
  p_checkpoint JSONB,
  p_results JSONB
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row public.participant_sessions%ROWTYPE;
  v_existing_month public.month_results%ROWTYPE;
  v_item JSONB;
  v_index INTEGER := 0;
  v_inserted INTEGER := 0;
  v_needs_hydration BOOLEAN := p_checkpoint ? 'monthly_results' OR p_checkpoint ? 'pending_month_result';
BEGIN
  SELECT * INTO v_row FROM public.participant_sessions WHERE id=p_session_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'SIM_NOT_FOUND'; END IF;
  FOR v_item IN SELECT value FROM jsonb_array_elements(COALESCE(p_results,'[]'::JSONB)) LOOP
    v_index := v_index + 1;
    IF (v_item->>'month_number')::INTEGER <> v_index THEN
      RAISE EXCEPTION 'SIM_CONFLICT: legacy months are not consecutive';
    END IF;
    SELECT * INTO v_existing_month FROM public.month_results
     WHERE session_id=p_session_id AND month_number=v_index;
    IF NOT FOUND THEN
      PERFORM public.insert_month_result_v3(p_session_id,v_item);
      v_inserted := v_inserted + 1;
    ELSIF v_existing_month.result_json IS NOT NULL AND
          v_existing_month.result_json IS DISTINCT FROM v_item->'result_json' THEN
      RAISE EXCEPTION 'SIM_CONFLICT: legacy month % differs from durable result', v_index;
    ELSIF v_existing_month.result_json IS NULL AND (
      v_existing_month.monthly_score IS DISTINCT FROM (v_item->>'monthly_score')::NUMERIC OR
      v_existing_month.accepted_payment IS DISTINCT FROM (v_item->>'accepted_payment')::NUMERIC OR
      v_existing_month.credit_final IS DISTINCT FROM (v_item->>'credit_final')::NUMERIC OR
      v_existing_month.overdraft_final IS DISTINCT FROM (v_item->>'overdraft_final')::NUMERIC
    ) THEN
      RAISE EXCEPTION 'SIM_CONFLICT: legacy month % differs from structured result', v_index;
    END IF;
  END LOOP;
  IF v_inserted > 0 OR v_needs_hydration THEN
    UPDATE public.participant_sessions SET
      current_page=COALESCE(p_checkpoint->>'page',current_page),
      current_month=COALESCE((p_checkpoint->>'month')::SMALLINT,current_month),
      loan_balance=COALESCE((p_checkpoint->>'loan_balance')::NUMERIC,loan_balance),
      overdraft_balance=COALESCE((p_checkpoint->>'overdraft_balance')::NUMERIC,overdraft_balance),
      total_score=COALESCE((p_checkpoint->>'total_score')::NUMERIC,total_score),
      monthly_points=COALESCE((p_checkpoint->>'monthly_points')::NUMERIC,monthly_points),
      accumulated_costs=COALESCE((p_checkpoint->>'accumulated_costs')::NUMERIC,accumulated_costs),
      pending_month_number=CASE WHEN p_checkpoint->'pending_month_result' IS NULL THEN NULL ELSE (p_checkpoint->'pending_month_result'->>'month')::SMALLINT END,
      experimental_condition=COALESCE(p_checkpoint->>'experimental_condition',experimental_condition),
      score_frame=COALESCE(p_checkpoint->>'score_frame',score_frame),
      monthly_score_feedback=COALESCE(p_checkpoint->>'monthly_score_feedback',monthly_score_feedback),
      treatment_bound=(
        treatment_bound OR prolific_pid IS NOT NULL OR study_session_id IS NOT NULL OR
        v_index>0 OR COALESCE((p_checkpoint->>'month')::INTEGER,1)>1
      ),
      comprehension_attempts=COALESCE((p_checkpoint->>'comprehension_attempts')::INTEGER,comprehension_attempts),
      comprehension_passed=COALESCE((p_checkpoint->>'comprehension_passed')::BOOLEAN,comprehension_passed),
      attention_failed_count=COALESCE((p_checkpoint->>'attention_failed_count')::INTEGER,attention_failed_count),
      checkpoint=p_checkpoint - 'monthly_results' - 'pending_month_result' - 'loan_balance' - 'overdraft_balance' - 'total_score' - 'monthly_points' - 'accumulated_costs' - 'final_score' - 'final_score_breakdown' - 'experimental_condition' - 'score_frame' - 'monthly_score_feedback',
      state_version=state_version+1,last_transition_at=NOW(),updated_at=NOW()
    WHERE id=p_session_id;
  END IF;
  RETURN jsonb_build_object(
    'session_id',p_session_id,'backfilled',v_inserted,
    'state_version',v_row.state_version+CASE WHEN v_inserted>0 OR v_needs_hydration THEN 1 ELSE 0 END
  );
END;
$$;

CREATE OR REPLACE FUNCTION public.finalize_experiment_v3(
  p_session_id UUID,
  p_expected_version BIGINT,
  p_account_key TEXT,
  p_request_id TEXT,
  p_payload_hash TEXT,
  p_state JSONB,
  p_summary JSONB,
  p_demographics JSONB,
  p_pre_answers JSONB,
  p_post_answers JSONB,
  p_feedback TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row public.participant_sessions%ROWTYPE;
  v_idem public.experiment_idempotency%ROWTYPE;
  v_answer JSONB;
  v_months INTEGER;
  v_score NUMERIC;
  v_response JSONB;
  v_prolific BOOLEAN;
BEGIN
  SELECT * INTO v_idem FROM public.experiment_idempotency
   WHERE session_id=p_session_id AND operation='finalize' AND request_id=p_request_id;
  IF FOUND THEN
    IF v_idem.payload_hash<>p_payload_hash THEN RAISE EXCEPTION 'SIM_IDEMPOTENCY_CONFLICT'; END IF;
    RETURN v_idem.response_json || jsonb_build_object('idempotency_hit',TRUE);
  END IF;
  SELECT * INTO v_row FROM public.participant_sessions WHERE id=p_session_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'SIM_NOT_FOUND'; END IF;
  SELECT * INTO v_idem FROM public.experiment_idempotency
   WHERE session_id=p_session_id AND operation='finalize' AND request_id=p_request_id;
  IF FOUND THEN
    IF v_idem.payload_hash<>p_payload_hash THEN RAISE EXCEPTION 'SIM_IDEMPOTENCY_CONFLICT'; END IF;
    RETURN v_idem.response_json || jsonb_build_object('idempotency_hit',TRUE);
  END IF;
  IF v_row.status='completed' AND v_row.finalization_request_id IS NOT NULL THEN
    SELECT * INTO v_idem FROM public.experiment_idempotency
     WHERE session_id=p_session_id AND operation='finalize' AND request_id=v_row.finalization_request_id;
    IF FOUND THEN
      RETURN v_idem.response_json || jsonb_build_object('idempotency_hit',TRUE);
    END IF;
    RETURN jsonb_build_object(
      'session_id',p_session_id,'state_version',v_row.state_version,
      'idempotency_hit',TRUE
    );
  END IF;
  IF v_row.state_version<>p_expected_version THEN RAISE EXCEPTION 'SIM_CONFLICT: stale finalization version'; END IF;
  SELECT COUNT(*), ROUND(LEAST(100,GREATEST(0,COALESCE(SUM(monthly_score),0)/24.0)),2)
    INTO v_months,v_score FROM public.month_results WHERE session_id=p_session_id;
  IF v_months<>24 THEN RAISE EXCEPTION 'SIM_CONFLICT: finalization requires 24 months'; END IF;
  IF v_score IS DISTINCT FROM ROUND((p_summary->>'final_score')::NUMERIC,2) THEN
    RAISE EXCEPTION 'SIM_CONFLICT: final score does not match durable ledger';
  END IF;

  FOR v_answer IN SELECT value FROM jsonb_array_elements(COALESCE(p_pre_answers,'[]'::JSONB)) LOOP
    INSERT INTO public.psychometric_pre_answers(session_id,study_session_id,study_session_code,participant_code,section_number,question_number,question_key,question_text,answer_value,updated_at)
    VALUES(p_session_id,NULLIF(v_answer->>'study_session_id','')::UUID,v_answer->>'study_session_code',v_answer->>'participant_code',(v_answer->>'section_number')::INTEGER,(v_answer->>'question_number')::INTEGER,v_answer->>'question_key',v_answer->>'question_text',(v_answer->>'answer_value')::SMALLINT,NOW())
    ON CONFLICT(session_id,question_key) DO UPDATE SET answer_value=EXCLUDED.answer_value,updated_at=NOW();
  END LOOP;
  FOR v_answer IN SELECT value FROM jsonb_array_elements(COALESCE(p_post_answers,'[]'::JSONB)) LOOP
    INSERT INTO public.psychometric_post_answers(session_id,study_session_id,study_session_code,participant_code,section_number,question_number,question_key,question_text,answer_value,updated_at)
    VALUES(p_session_id,NULLIF(v_answer->>'study_session_id','')::UUID,v_answer->>'study_session_code',v_answer->>'participant_code',(v_answer->>'section_number')::INTEGER,(v_answer->>'question_number')::INTEGER,v_answer->>'question_key',v_answer->>'question_text',(v_answer->>'answer_value')::SMALLINT,NOW())
    ON CONFLICT(session_id,question_key) DO UPDATE SET answer_value=EXCLUDED.answer_value,updated_at=NOW();
  END LOOP;

  v_prolific := COALESCE(p_summary->>'prolific_pid','')<>'' AND COALESCE(p_summary->>'prolific_session_id','')<>'';
  INSERT INTO public.session_summaries(
    session_id,months_completed,monthly_score_sum,final_score,bonus_max_session,bonus_final,
    experimental_condition,score_frame,monthly_score_feedback,performance_bonus_gbp,
    loss_amount_gbp,prolific_base_reward_gbp,total_payout_gbp,prolific_bonus_status,
    completion_timestamp,payment_status,total_repaid,remaining_credit,remaining_overdraft,
    credit_interest_total,overdraft_interest_total,interest_total,study_session_id,
    study_session_code,participant_code,prolific_pid,prolific_study_id,prolific_session_id,
    completion_code,feedback,finalization_status,finalization_request_id,payment_idempotency_key,updated_at
  ) VALUES (
    p_session_id,v_months,(p_summary->>'monthly_score_sum')::NUMERIC,v_score,
    (p_summary->>'bonus_max_session')::NUMERIC,(p_summary->>'bonus_final')::NUMERIC,
    p_summary->>'experimental_condition',p_summary->>'score_frame',p_summary->>'monthly_score_feedback',
    (p_summary->>'performance_bonus_gbp')::NUMERIC,(p_summary->>'loss_amount_gbp')::NUMERIC,
    (p_summary->>'prolific_base_reward_gbp')::NUMERIC,(p_summary->>'total_payout_gbp')::NUMERIC,
    CASE WHEN v_prolific THEN 'pending' ELSE 'not_applicable' END,NOW(),
    COALESCE(p_summary->>'payment_status','unpaid'),(p_summary->>'total_repaid')::NUMERIC,
    (p_summary->>'remaining_credit')::NUMERIC,(p_summary->>'remaining_overdraft')::NUMERIC,
    (p_summary->>'credit_interest_total')::NUMERIC,(p_summary->>'overdraft_interest_total')::NUMERIC,
    (p_summary->>'interest_total')::NUMERIC,NULLIF(p_summary->>'study_session_id','')::UUID,
    p_summary->>'study_session_code',p_summary->>'participant_code',p_summary->>'prolific_pid',
    p_summary->>'prolific_study_id',p_summary->>'prolific_session_id',p_summary->>'completion_code',
    p_feedback,'internal_finalized',p_request_id,'payment:'||p_request_id,NOW()
  ) ON CONFLICT(session_id) DO UPDATE SET
    months_completed=EXCLUDED.months_completed,monthly_score_sum=EXCLUDED.monthly_score_sum,
    final_score=EXCLUDED.final_score,bonus_max_session=EXCLUDED.bonus_max_session,
    bonus_final=EXCLUDED.bonus_final,experimental_condition=EXCLUDED.experimental_condition,
    score_frame=EXCLUDED.score_frame,monthly_score_feedback=EXCLUDED.monthly_score_feedback,
    performance_bonus_gbp=EXCLUDED.performance_bonus_gbp,loss_amount_gbp=EXCLUDED.loss_amount_gbp,
    prolific_base_reward_gbp=EXCLUDED.prolific_base_reward_gbp,total_payout_gbp=EXCLUDED.total_payout_gbp,
    prolific_bonus_status=EXCLUDED.prolific_bonus_status,completion_timestamp=EXCLUDED.completion_timestamp,
    payment_status=EXCLUDED.payment_status,total_repaid=EXCLUDED.total_repaid,
    remaining_credit=EXCLUDED.remaining_credit,remaining_overdraft=EXCLUDED.remaining_overdraft,
    credit_interest_total=EXCLUDED.credit_interest_total,
    overdraft_interest_total=EXCLUDED.overdraft_interest_total,interest_total=EXCLUDED.interest_total,
    study_session_id=EXCLUDED.study_session_id,study_session_code=EXCLUDED.study_session_code,
    participant_code=EXCLUDED.participant_code,prolific_pid=EXCLUDED.prolific_pid,
    prolific_study_id=EXCLUDED.prolific_study_id,prolific_session_id=EXCLUDED.prolific_session_id,
    completion_code=EXCLUDED.completion_code,feedback=EXCLUDED.feedback,
    finalization_status=EXCLUDED.finalization_status,finalization_request_id=EXCLUDED.finalization_request_id,
    payment_idempotency_key=EXCLUDED.payment_idempotency_key,
    updated_at=NOW();

  UPDATE public.participant_sessions SET
    status='completed',current_page='done',completed_at=COALESCE(completed_at,NOW()),
    demographics=COALESCE(p_demographics,'{}'::JSONB),checkpoint=COALESCE(p_state->'resume_projection','{}'::JSONB),
    completion_code=p_summary->>'completion_code',finalization_request_id=p_request_id,
    completion_status=CASE WHEN v_prolific THEN 'payment_pending' ELSE 'complete' END,
    state_version=state_version+1,last_transition_at=NOW(),updated_at=NOW()
  WHERE id=p_session_id;
  INSERT INTO public.completed_accounts(account_key,completed_at) VALUES(p_account_key,NOW())
    ON CONFLICT(account_key) DO UPDATE SET completed_at=EXCLUDED.completed_at;
  DELETE FROM public.resume_links WHERE account_key=p_account_key AND session_id=p_session_id;
  IF v_prolific THEN
    INSERT INTO public.prolific_payment_attempts(session_id,request_id,status)
    VALUES(p_session_id,'payment:'||p_request_id,'pending') ON CONFLICT(session_id) DO NOTHING;
  END IF;

  v_response:=jsonb_build_object('session_id',p_session_id,'state_version',p_expected_version+1,'final_score',v_score,'idempotency_hit',FALSE);
  INSERT INTO public.experiment_idempotency VALUES(p_session_id,'finalize',p_request_id,p_payload_hash,v_response,NOW());
  RETURN v_response;
END;
$$;

CREATE OR REPLACE FUNCTION public.claim_prolific_payment_v3(
  p_session_id UUID,
  p_request_id TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_attempt public.prolific_payment_attempts%ROWTYPE;
BEGIN
  SELECT * INTO v_attempt FROM public.prolific_payment_attempts
   WHERE session_id=p_session_id FOR UPDATE;
  IF NOT FOUND OR v_attempt.request_id<>p_request_id THEN
    RAISE EXCEPTION 'SIM_CONFLICT: payment attempt was not initialized';
  END IF;
  IF v_attempt.status<>'pending' THEN
    RETURN jsonb_build_object('claimed',FALSE,'status',v_attempt.status,'attempt_count',v_attempt.attempt_count);
  END IF;

  UPDATE public.prolific_payment_attempts SET
    status='processing',attempt_count=attempt_count+1,updated_at=NOW()
  WHERE session_id=p_session_id;
  UPDATE public.session_summaries SET
    prolific_bonus_status='processing',updated_at=NOW()
  WHERE session_id=p_session_id;
  UPDATE public.participant_sessions SET
    completion_status='payment_processing',updated_at=NOW()
  WHERE id=p_session_id;
  RETURN jsonb_build_object('claimed',TRUE,'status','processing','attempt_count',v_attempt.attempt_count+1);
END;
$$;

CREATE OR REPLACE FUNCTION public.finish_prolific_payment_v3(
  p_session_id UUID,
  p_request_id TEXT,
  p_attempt_status TEXT,
  p_bonus_status TEXT,
  p_payment_status TEXT,
  p_error TEXT,
  p_response JSONB,
  p_created_at TIMESTAMPTZ DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_attempt public.prolific_payment_attempts%ROWTYPE;
BEGIN
  IF p_attempt_status NOT IN ('succeeded','manual_review','not_configured','not_applicable') THEN
    RAISE EXCEPTION 'SIM_CONFLICT: invalid terminal payment status';
  END IF;
  SELECT * INTO v_attempt FROM public.prolific_payment_attempts
   WHERE session_id=p_session_id FOR UPDATE;
  IF NOT FOUND OR v_attempt.request_id<>p_request_id THEN
    RAISE EXCEPTION 'SIM_CONFLICT: payment attempt was not initialized';
  END IF;
  IF v_attempt.status IN ('succeeded','manual_review','not_configured','not_applicable') THEN
    RETURN jsonb_build_object('updated',FALSE,'status',v_attempt.status);
  END IF;

  UPDATE public.prolific_payment_attempts SET
    status=p_attempt_status,response_json=p_response,last_error=LEFT(p_error,1000),updated_at=NOW()
  WHERE session_id=p_session_id;
  UPDATE public.session_summaries SET
    prolific_bonus_status=p_bonus_status,payment_status=p_payment_status,
    prolific_bonus_created_at=COALESCE(p_created_at,prolific_bonus_created_at),
    prolific_bonus_error=LEFT(p_error,1000),updated_at=NOW()
  WHERE session_id=p_session_id;
  UPDATE public.participant_sessions SET
    completion_status='payment_manual_review',updated_at=NOW()
  WHERE id=p_session_id;
  RETURN jsonb_build_object('updated',TRUE,'status',p_attempt_status);
END;
$$;

ALTER TABLE public.experiment_idempotency ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.prolific_payment_attempts ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON FUNCTION public.claim_participant_session_v3(UUID,TEXT,TEXT,TEXT,JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.commit_stage_transition_v3(UUID,BIGINT,TEXT,TEXT,JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.commit_quality_transition_v3(UUID,BIGINT,TEXT,TEXT,JSONB,JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.commit_month_decision_v3(UUID,BIGINT,SMALLINT,TEXT,TEXT,JSONB,JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.acknowledge_month_feedback_v3(UUID,BIGINT,SMALLINT,TEXT,TEXT,JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.backfill_legacy_session_v3(UUID,JSONB,JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.finalize_experiment_v3(UUID,BIGINT,TEXT,TEXT,TEXT,JSONB,JSONB,JSONB,JSONB,JSONB,TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.claim_prolific_payment_v3(UUID,TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.finish_prolific_payment_v3(UUID,TEXT,TEXT,TEXT,TEXT,TEXT,JSONB,TIMESTAMPTZ) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.claim_participant_session_v3(UUID,TEXT,TEXT,TEXT,JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION public.commit_stage_transition_v3(UUID,BIGINT,TEXT,TEXT,JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION public.commit_quality_transition_v3(UUID,BIGINT,TEXT,TEXT,JSONB,JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION public.commit_month_decision_v3(UUID,BIGINT,SMALLINT,TEXT,TEXT,JSONB,JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION public.acknowledge_month_feedback_v3(UUID,BIGINT,SMALLINT,TEXT,TEXT,JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION public.backfill_legacy_session_v3(UUID,JSONB,JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION public.finalize_experiment_v3(UUID,BIGINT,TEXT,TEXT,TEXT,JSONB,JSONB,JSONB,JSONB,JSONB,TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.claim_prolific_payment_v3(UUID,TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.finish_prolific_payment_v3(UUID,TEXT,TEXT,TEXT,TEXT,TEXT,JSONB,TIMESTAMPTZ) TO service_role;

COMMIT;

-- Downgrade notes:
-- 1. Deploy the Phase 2 application before dropping these RPCs/columns.
-- 2. Keep month_results rows; they are research data and must never be removed.
-- 3. The additive columns/tables can then be dropped after confirming no active
--    session has state_version > 0 and no payment attempt is pending/processing.
