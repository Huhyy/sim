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

CREATE TABLE IF NOT EXISTS psychometric_pre_answers (
  session_id UUID NOT NULL REFERENCES participant_sessions(id) ON DELETE CASCADE,
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

CREATE TABLE IF NOT EXISTS psychometric_post_answers (
  session_id UUID NOT NULL REFERENCES participant_sessions(id) ON DELETE CASCADE,
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

CREATE TABLE IF NOT EXISTS month_results (
  session_id UUID NOT NULL REFERENCES participant_sessions(id) ON DELETE CASCADE,
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

CREATE TABLE IF NOT EXISTS session_summaries (
  session_id UUID PRIMARY KEY REFERENCES participant_sessions(id) ON DELETE CASCADE,
  months_completed INTEGER NOT NULL DEFAULT 0,
  monthly_score_sum NUMERIC(8,2),
  final_score NUMERIC(6,2),
  bonus_max_session NUMERIC(12,2),
  bonus_final NUMERIC(12,2),
  total_repaid NUMERIC(12,2),
  remaining_credit NUMERIC(12,2),
  remaining_overdraft NUMERIC(12,2),
  credit_interest_total NUMERIC(12,2),
  overdraft_interest_total NUMERIC(12,2),
  interest_total NUMERIC(12,2),
  study_session_id UUID,
  study_session_code TEXT,
  feedback TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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
