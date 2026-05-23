CREATE TABLE legacy_responses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed BOOLEAN DEFAULT FALSE,
  final_score NUMERIC(6,2),
  feedback TEXT,
  dopa_0 SMALLINT, dopa_1 SMALLINT, dopa_2 SMALLINT, dopa_3 SMALLINT, dopa_4 SMALLINT, dopa_5 SMALLINT, dopa_6 SMALLINT,
  sero_0 SMALLINT, sero_1 SMALLINT, sero_2 SMALLINT, sero_3 SMALLINT, sero_4 SMALLINT, sero_5 SMALLINT, sero_6 SMALLINT,
  oxyt_0 SMALLINT, oxyt_1 SMALLINT, oxyt_2 SMALLINT, oxyt_3 SMALLINT, oxyt_4 SMALLINT, oxyt_5 SMALLINT, oxyt_6 SMALLINT,
  endo_0 SMALLINT, endo_1 SMALLINT, endo_2 SMALLINT, endo_3 SMALLINT, endo_4 SMALLINT, endo_5 SMALLINT, endo_6 SMALLINT,
  bis_0 SMALLINT, bis_1 SMALLINT, bis_2 SMALLINT, bis_3 SMALLINT, bis_4 SMALLINT, bis_5 SMALLINT, bis_6 SMALLINT,
  bis_7 SMALLINT, bis_8 SMALLINT, bis_9 SMALLINT, bis_10 SMALLINT, bis_11 SMALLINT, bis_12 SMALLINT, bis_13 SMALLINT,
  bis_14 SMALLINT, bis_15 SMALLINT, bis_16 SMALLINT, bis_17 SMALLINT, bis_18 SMALLINT, bis_19 SMALLINT, bis_20 SMALLINT,
  bis_21 SMALLINT, bis_22 SMALLINT, bis_23 SMALLINT, bis_24 SMALLINT, bis_25 SMALLINT, bis_26 SMALLINT, bis_27 SMALLINT,
  bis_28 SMALLINT, bis_29 SMALLINT,
  swl_0 SMALLINT, swl_1 SMALLINT, swl_2 SMALLINT, swl_3 SMALLINT, swl_4 SMALLINT,
  who5_0 SMALLINT, who5_1 SMALLINT, who5_2 SMALLINT, who5_3 SMALLINT, who5_4 SMALLINT, who5_5 SMALLINT, who5_6 SMALLINT,
  neg_aff_0 SMALLINT, neg_aff_1 SMALLINT, neg_aff_2 SMALLINT, neg_aff_3 SMALLINT, neg_aff_4 SMALLINT, neg_aff_5 SMALLINT, neg_aff_6 SMALLINT,
  euda_0 SMALLINT, euda_1 SMALLINT, euda_2 SMALLINT, euda_3 SMALLINT, euda_4 SMALLINT, euda_5 SMALLINT,
  resil_0 SMALLINT, resil_1 SMALLINT, resil_2 SMALLINT, resil_3 SMALLINT, resil_4 SMALLINT,
  pss_0 SMALLINT, pss_1 SMALLINT, pss_2 SMALLINT, pss_3 SMALLINT, pss_4 SMALLINT, pss_5 SMALLINT, pss_6 SMALLINT,
  mood_neg_0 SMALLINT, mood_neg_1 SMALLINT, mood_neg_2 SMALLINT, mood_neg_3 SMALLINT, mood_neg_4 SMALLINT, mood_neg_5 SMALLINT,
  mood_pos_0 SMALLINT, mood_pos_1 SMALLINT, mood_pos_2 SMALLINT, mood_pos_3 SMALLINT, mood_pos_4 SMALLINT, mood_pos_5 SMALLINT,
  physio_0 SMALLINT, physio_1 SMALLINT, physio_2 SMALLINT, physio_3 SMALLINT, physio_4 SMALLINT, physio_5 SMALLINT,
  reapp_0 SMALLINT, reapp_1 SMALLINT, reapp_2 SMALLINT, reapp_3 SMALLINT, reapp_4 SMALLINT,
  suppr_0 SMALLINT, suppr_1 SMALLINT, suppr_2 SMALLINT, suppr_3 SMALLINT, suppr_4 SMALLINT,
  emo_imp_0 SMALLINT, emo_imp_1 SMALLINT, emo_imp_2 SMALLINT, emo_imp_3 SMALLINT, emo_imp_4 SMALLINT,
  emo_aware_0 SMALLINT, emo_aware_1 SMALLINT, emo_aware_2 SMALLINT, emo_aware_3 SMALLINT, emo_aware_4 SMALLINT,
  emo_acc_0 SMALLINT, emo_acc_1 SMALLINT, emo_acc_2 SMALLINT, emo_acc_3 SMALLINT, emo_acc_4 SMALLINT, emo_acc_5 SMALLINT,
  emo_reg_0 SMALLINT, emo_reg_1 SMALLINT, emo_reg_2 SMALLINT, emo_reg_3 SMALLINT, emo_reg_4 SMALLINT,
  emo_reg_5 SMALLINT, emo_reg_6 SMALLINT, emo_reg_7 SMALLINT, emo_reg_8 SMALLINT, emo_reg_9 SMALLINT,
  open_0 SMALLINT, open_1 SMALLINT, open_2 SMALLINT, open_3 SMALLINT,
  cons_0 SMALLINT, cons_1 SMALLINT, cons_2 SMALLINT, cons_3 SMALLINT,
  extra_0 SMALLINT, extra_1 SMALLINT, extra_2 SMALLINT, extra_3 SMALLINT,
  agree_0 SMALLINT, agree_1 SMALLINT, agree_2 SMALLINT, agree_3 SMALLINT,
  neuro_0 SMALLINT, neuro_1 SMALLINT, neuro_2 SMALLINT, neuro_3 SMALLINT,
  dark_0 SMALLINT, dark_1 SMALLINT, dark_2 SMALLINT, dark_3 SMALLINT, dark_4 SMALLINT, dark_5 SMALLINT,
  dark_6 SMALLINT, dark_7 SMALLINT, dark_8 SMALLINT, dark_9 SMALLINT, dark_10 SMALLINT, dark_11 SMALLINT,
  post_0 SMALLINT, post_1 SMALLINT, post_2 SMALLINT, post_3 SMALLINT, post_4 SMALLINT,
  post_5 SMALLINT, post_6 SMALLINT, post_7 SMALLINT, post_8 SMALLINT
);

ALTER TABLE legacy_responses ENABLE ROW LEVEL SECURITY;

CREATE TABLE participant_sessions (
  id UUID PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'in_progress',
  current_page TEXT,
  checkpoint JSONB NOT NULL DEFAULT '{}'::jsonb
);

ALTER TABLE participant_sessions ENABLE ROW LEVEL SECURITY;

-- Identity separation and duplicate-prevention layer.
-- The legacy_responses table above is retained only for backwards compatibility with existing exports.
CREATE TABLE study_responses (
  response_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  final_score NUMERIC(6,2) NOT NULL,
  feedback TEXT,
  answers JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE resume_links (
  account_key TEXT PRIMARY KEY CHECK (char_length(account_key) = 64),
  session_id UUID NOT NULL UNIQUE REFERENCES participant_sessions(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE completed_accounts (
  account_key TEXT PRIMARY KEY CHECK (char_length(account_key) = 64),
  completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE legacy_responses ENABLE ROW LEVEL SECURITY;
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
