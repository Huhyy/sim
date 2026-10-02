-- Run before deploying C5-C8 so existing production check constraints accept them.
BEGIN;

DO $$
DECLARE
  target_table text;
  old_constraint record;
BEGIN
  FOREACH target_table IN ARRAY ARRAY['participant_sessions', 'admin_study_sessions', 'session_summaries']
  LOOP
    FOR old_constraint IN
      SELECT c.conname
      FROM pg_constraint c
      JOIN pg_class t ON t.oid = c.conrelid
      JOIN pg_namespace n ON n.oid = t.relnamespace
      WHERE n.nspname = 'public'
        AND t.relname = target_table
        AND c.contype = 'c'
        AND pg_get_constraintdef(c.oid) LIKE '%experimental_condition%'
    LOOP
      EXECUTE format('ALTER TABLE public.%I DROP CONSTRAINT %I', target_table, old_constraint.conname);
    END LOOP;

    EXECUTE format(
      'ALTER TABLE public.%I ADD CONSTRAINT %I CHECK (experimental_condition IN (''C1'', ''C2'', ''C3'', ''C4'', ''C5'', ''C6'', ''C7'', ''C8''))',
      target_table, target_table || '_experimental_condition_check'
    );
  END LOOP;
END $$;

COMMIT;
