-- Run this once in Supabase SQL Editor before enabling Google authentication.
-- Auth identity is stored only as a peppered HMAC key; final responses contain no identity or session id.

CREATE TABLE IF NOT EXISTS study_responses (
  response_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  final_score NUMERIC(6,2) NOT NULL,
  feedback TEXT,
  answers JSONB NOT NULL DEFAULT '{}'::jsonb
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

-- The Streamlit server writes with the backend secret key; no browser/API user should read these tables.
-- Existing participants rows remain as protected legacy response data until deployment is complete.
ALTER TABLE IF EXISTS participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE participant_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE study_responses ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE completed_accounts ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION finalize_study_response(
  p_account_key TEXT,
  p_session_id UUID,
  p_final_score NUMERIC,
  p_feedback TEXT,
  p_answers JSONB
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_response_id UUID;
BEGIN
  IF EXISTS (
    SELECT 1 FROM completed_accounts WHERE account_key = p_account_key
  ) THEN
    RAISE EXCEPTION 'This participant has already completed the study.';
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM resume_links
    WHERE account_key = p_account_key AND session_id = p_session_id
  ) THEN
    RAISE EXCEPTION 'No active session is associated with this participant.';
  END IF;

  INSERT INTO study_responses (final_score, feedback, answers)
  VALUES (p_final_score, p_feedback, COALESCE(p_answers, '{}'::jsonb))
  RETURNING response_id INTO v_response_id;

  INSERT INTO completed_accounts (account_key) VALUES (p_account_key);

  DELETE FROM resume_links
  WHERE account_key = p_account_key AND session_id = p_session_id;

  DELETE FROM participant_sessions
  WHERE id = p_session_id;

  RETURN v_response_id;
END;
$$;

REVOKE ALL ON FUNCTION finalize_study_response(TEXT, UUID, NUMERIC, TEXT, JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION finalize_study_response(TEXT, UUID, NUMERIC, TEXT, JSONB) FROM anon;
REVOKE ALL ON FUNCTION finalize_study_response(TEXT, UUID, NUMERIC, TEXT, JSONB) FROM authenticated;
GRANT EXECUTE ON FUNCTION finalize_study_response(TEXT, UUID, NUMERIC, TEXT, JSONB) TO service_role;
