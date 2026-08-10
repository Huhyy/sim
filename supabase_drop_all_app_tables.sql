-- DESTRUCTIVE RESET FOR THE BEHAVIORAL CREDIT SIMULATOR ONLY.
--
-- This permanently deletes all application research/participant data listed
-- below. It deliberately does NOT drop the public schema, Supabase auth,
-- storage, extensions, or unrelated public tables.
--
-- Take a database backup before running this in the Supabase SQL Editor.

BEGIN;

-- Remove application RPCs explicitly before their table row types disappear.
DROP FUNCTION IF EXISTS public.finish_prolific_payment_v3(UUID, TEXT, TEXT, TEXT, TEXT, TEXT, JSONB, TIMESTAMPTZ);
DROP FUNCTION IF EXISTS public.claim_prolific_payment_v3(UUID, TEXT);
DROP FUNCTION IF EXISTS public.finalize_experiment_v3(UUID, BIGINT, TEXT, TEXT, TEXT, JSONB, JSONB, JSONB, JSONB, JSONB, TEXT);
DROP FUNCTION IF EXISTS public.backfill_legacy_session_v3(UUID, JSONB, JSONB);
DROP FUNCTION IF EXISTS public.acknowledge_month_feedback_v3(UUID, BIGINT, SMALLINT, TEXT, TEXT, JSONB);
DROP FUNCTION IF EXISTS public.commit_month_decision_v3(UUID, BIGINT, SMALLINT, TEXT, TEXT, JSONB, JSONB);
DROP FUNCTION IF EXISTS public.commit_quality_transition_v3(UUID, BIGINT, TEXT, TEXT, JSONB, JSONB);
DROP FUNCTION IF EXISTS public.commit_stage_transition_v3(UUID, BIGINT, TEXT, TEXT, JSONB);
DROP FUNCTION IF EXISTS public.claim_participant_session_v3(UUID, TEXT, TEXT, TEXT, JSONB);
DROP FUNCTION IF EXISTS public.insert_month_result_v3(UUID, JSONB);
DROP FUNCTION IF EXISTS public.prevent_treatment_rebinding_v3() CASCADE;
DROP FUNCTION IF EXISTS public.finalize_study_response(TEXT, UUID, NUMERIC, TEXT, JSONB);

-- Child/ledger tables first, then participant/session roots.
DROP TABLE IF EXISTS public.experiment_idempotency CASCADE;
DROP TABLE IF EXISTS public.prolific_payment_attempts CASCADE;
DROP TABLE IF EXISTS public.quality_checks CASCADE;
DROP TABLE IF EXISTS public.page_progress CASCADE;
DROP TABLE IF EXISTS public.psychometric_pre_answers CASCADE;
DROP TABLE IF EXISTS public.psychometric_post_answers CASCADE;
DROP TABLE IF EXISTS public.month_results CASCADE;
DROP TABLE IF EXISTS public.session_summaries CASCADE;
DROP TABLE IF EXISTS public.resume_links CASCADE;
DROP TABLE IF EXISTS public.completed_accounts CASCADE;
DROP TABLE IF EXISTS public.participant_sessions CASCADE;
DROP TABLE IF EXISTS public.admin_study_sessions CASCADE;

-- Historical app tables, if an older deployment still has them.
DROP TABLE IF EXISTS public.legacy_responses CASCADE;
DROP TABLE IF EXISTS public.study_responses CASCADE;
DROP TABLE IF EXISTS public.participants CASCADE;
DROP TABLE IF EXISTS public.months CASCADE;

COMMIT;
