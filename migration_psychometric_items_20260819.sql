-- Additive migration for the 19.08.26 psychometric items.
--
-- This migration does not drop tables, rows, keys, or questionnaire data.
-- Existing answers remain unchanged. The application still validates each
-- question's own scale; only score_check uses values 6 and 7.

BEGIN;

-- The existing post table was created with answer_value BETWEEN 1 AND 5.
-- Remove the existing answer-range check regardless of its generated name,
-- then replace it with the wider range required by score_check.
DO $$
DECLARE
    constraint_name TEXT;
BEGIN
    FOR constraint_name IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'public.psychometric_post_answers'::regclass
          AND contype = 'c'
          AND pg_get_constraintdef(oid) ILIKE '%answer_value%'
    LOOP
        EXECUTE format(
            'ALTER TABLE public.psychometric_post_answers DROP CONSTRAINT %I',
            constraint_name
        );
    END LOOP;
END
$$;

ALTER TABLE public.psychometric_post_answers
    ADD CONSTRAINT psychometric_post_answers_answer_value_check
    CHECK (answer_value BETWEEN 1 AND 7);

COMMIT;

-- No question_number constraint is changed here. The application persists
-- legacy post-question numbers unchanged and assigns 36-45 to the new items,
-- so the existing UNIQUE (session_id, question_number) constraint remains
-- safe for active legacy sessions.
