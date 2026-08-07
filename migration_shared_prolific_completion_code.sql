-- Prolific completion codes belong to the study, so every participant in the
-- same study can legitimately use the same code.
ALTER TABLE public.participant_sessions
  DROP CONSTRAINT IF EXISTS participant_sessions_completion_code_key;

ALTER TABLE public.participant_sessions
  ADD COLUMN IF NOT EXISTS completion_code TEXT;
