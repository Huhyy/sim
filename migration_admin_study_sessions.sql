-- Additive production migration for the administrator session monitor.
-- Run once in the Supabase SQL editor or with a privileged PostgreSQL connection.

CREATE TABLE IF NOT EXISTS public.admin_study_sessions (
  id UUID PRIMARY KEY,
  session_code TEXT NOT NULL UNIQUE CHECK (session_code ~ '^[0-9]{6}$'),
  created_by_email TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  experimental_condition TEXT NOT NULL DEFAULT 'C1'
    CHECK (experimental_condition IN ('C1', 'C2', 'C3', 'C4')),
  score_frame TEXT NOT NULL DEFAULT 'gain_frame'
    CHECK (score_frame IN ('gain_frame', 'loss_frame')),
  monthly_score_feedback TEXT NOT NULL DEFAULT 'displayed'
    CHECK (monthly_score_feedback IN ('displayed', 'hidden')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.admin_study_sessions
  ADD COLUMN IF NOT EXISTS experimental_condition TEXT NOT NULL DEFAULT 'C1';
ALTER TABLE public.admin_study_sessions
  ADD COLUMN IF NOT EXISTS score_frame TEXT NOT NULL DEFAULT 'gain_frame';
ALTER TABLE public.admin_study_sessions
  ADD COLUMN IF NOT EXISTS monthly_score_feedback TEXT NOT NULL DEFAULT 'displayed';
ALTER TABLE public.admin_study_sessions ENABLE ROW LEVEL SECURITY;
