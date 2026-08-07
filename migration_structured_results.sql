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

