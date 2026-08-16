-- Align PostgreSQL final-score validation with the authoritative Python
-- binary-float rounding behavior at exact half-cent boundaries.
-- Safe to apply repeatedly.

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
  v_reported_score NUMERIC;
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
  SELECT COUNT(*), LEAST(100,GREATEST(0,COALESCE(SUM(monthly_score),0)/24.0))
    INTO v_months,v_score FROM public.month_results WHERE session_id=p_session_id;
  IF v_months<>24 THEN RAISE EXCEPTION 'SIM_CONFLICT: finalization requires 24 months'; END IF;
  v_reported_score := ROUND((p_summary->>'final_score')::NUMERIC,2);
  -- Python is the authoritative scoring implementation. Its binary-float
  -- rounding can differ from PostgreSQL NUMERIC rounding at exact half-cent
  -- boundaries (for example 79.675 -> 79.67 in Python, 79.68 in Postgres).
  IF v_reported_score IS NULL OR ABS(v_score-v_reported_score)>0.005 THEN
    RAISE EXCEPTION 'SIM_CONFLICT: final score does not match durable ledger';
  END IF;
  v_score := v_reported_score;

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


REVOKE ALL ON FUNCTION public.finalize_experiment_v3(UUID,BIGINT,TEXT,TEXT,TEXT,JSONB,JSONB,JSONB,JSONB,JSONB,TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.finalize_experiment_v3(UUID,BIGINT,TEXT,TEXT,TEXT,JSONB,JSONB,JSONB,JSONB,JSONB,TEXT) TO service_role;
