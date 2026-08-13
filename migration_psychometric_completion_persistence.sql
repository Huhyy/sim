-- Persist structured psychometric answers when each questionnaire phase ends.
--
-- The existing v3 transition remains authoritative for versioning,
-- idempotency, checkpoint progression, and quality-event persistence. These
-- v4 wrappers execute it and the structured-answer upsert in one PostgreSQL
-- transaction, so neither side can commit without the other.

CREATE OR REPLACE FUNCTION public.persist_psychometric_answers_v4(
  p_session_id UUID,
  p_pre_answers JSONB,
  p_post_answers JSONB
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_answer JSONB;
BEGIN
  FOR v_answer IN
    SELECT value FROM jsonb_array_elements(COALESCE(p_pre_answers, '[]'::JSONB))
  LOOP
    INSERT INTO public.psychometric_pre_answers(
      session_id, study_session_id, study_session_code, participant_code,
      section_number, question_number, question_key, question_text,
      answer_value, updated_at
    ) VALUES (
      p_session_id, NULLIF(v_answer->>'study_session_id', '')::UUID,
      v_answer->>'study_session_code', v_answer->>'participant_code',
      (v_answer->>'section_number')::INTEGER,
      (v_answer->>'question_number')::INTEGER,
      v_answer->>'question_key', v_answer->>'question_text',
      (v_answer->>'answer_value')::SMALLINT, NOW()
    )
    ON CONFLICT(session_id, question_key) DO UPDATE SET
      answer_value = EXCLUDED.answer_value,
      updated_at = NOW();
  END LOOP;

  FOR v_answer IN
    SELECT value FROM jsonb_array_elements(COALESCE(p_post_answers, '[]'::JSONB))
  LOOP
    INSERT INTO public.psychometric_post_answers(
      session_id, study_session_id, study_session_code, participant_code,
      section_number, question_number, question_key, question_text,
      answer_value, updated_at
    ) VALUES (
      p_session_id, NULLIF(v_answer->>'study_session_id', '')::UUID,
      v_answer->>'study_session_code', v_answer->>'participant_code',
      (v_answer->>'section_number')::INTEGER,
      (v_answer->>'question_number')::INTEGER,
      v_answer->>'question_key', v_answer->>'question_text',
      (v_answer->>'answer_value')::SMALLINT, NOW()
    )
    ON CONFLICT(session_id, question_key) DO UPDATE SET
      answer_value = EXCLUDED.answer_value,
      updated_at = NOW();
  END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION public.commit_stage_transition_v4(
  p_session_id UUID,
  p_expected_version BIGINT,
  p_request_id TEXT,
  p_payload_hash TEXT,
  p_state JSONB,
  p_pre_answers JSONB,
  p_post_answers JSONB
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_response JSONB;
BEGIN
  v_response := public.commit_stage_transition_v3(
    p_session_id, p_expected_version, p_request_id, p_payload_hash, p_state
  );
  PERFORM public.persist_psychometric_answers_v4(
    p_session_id, p_pre_answers, p_post_answers
  );
  RETURN v_response;
END;
$$;

CREATE OR REPLACE FUNCTION public.commit_quality_transition_v4(
  p_session_id UUID,
  p_expected_version BIGINT,
  p_request_id TEXT,
  p_payload_hash TEXT,
  p_state JSONB,
  p_events JSONB,
  p_pre_answers JSONB,
  p_post_answers JSONB
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_response JSONB;
BEGIN
  v_response := public.commit_quality_transition_v3(
    p_session_id, p_expected_version, p_request_id, p_payload_hash, p_state,
    p_events
  );
  PERFORM public.persist_psychometric_answers_v4(
    p_session_id, p_pre_answers, p_post_answers
  );
  RETURN v_response;
END;
$$;

REVOKE ALL ON FUNCTION public.persist_psychometric_answers_v4(UUID,JSONB,JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.commit_stage_transition_v4(UUID,BIGINT,TEXT,TEXT,JSONB,JSONB,JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.commit_quality_transition_v4(UUID,BIGINT,TEXT,TEXT,JSONB,JSONB,JSONB,JSONB) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.commit_stage_transition_v4(UUID,BIGINT,TEXT,TEXT,JSONB,JSONB,JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION public.commit_quality_transition_v4(UUID,BIGINT,TEXT,TEXT,JSONB,JSONB,JSONB,JSONB) TO service_role;
