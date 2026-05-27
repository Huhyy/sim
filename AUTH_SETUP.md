# Google Authentication Setup

The app uses Google authentication only to resume unfinished participation and prevent duplicate submissions. It stores a peppered HMAC account key in Supabase, never the participant's email or Google profile beside experimental answers.

## 1. Run The Supabase Schema

Run `setup.sql` or `migration_structured_results.sql` once in the Supabase SQL Editor before allowing participants to use the app.

The schema:

- creates `participant_sessions` as the session connector and recovery checkpoint table;
- creates `psychometric_pre_answers` with one row per pre-questionnaire answer;
- creates `psychometric_post_answers` with one row per post-questionnaire answer;
- creates `month_results` with one row per session and month, including `cash_final`;
- creates `session_summaries` for final score, bonus, and financial totals;
- creates `resume_links` for temporary in-progress recovery;
- creates `completed_accounts` for duplicate prevention only;
- drops old legacy result tables/functions: `participants`, `months`, `legacy_responses`, `study_responses`, and `finalize_study_response`;
- enables Row Level Security on all app tables.

## 2. Configure Google OIDC

In Google Auth Platform, create a Web application OAuth client and add the deployed Streamlit callback URL as an authorized redirect URI. On Streamlit Community Cloud, use the hosted callback route:

```text
https://<your-app-domain>/~/+/oauth2callback
```

For local testing, additionally allow:

```text
http://localhost:8501/oauth2callback
```

## 3. Configure Streamlit Secrets

Set these values in Streamlit Community Cloud app secrets:

```toml
SUPABASE_URL = "https://<project-ref>.supabase.co"
SUPABASE_SECRET_KEY = "sb_secret_<server-only-key>"
ACCOUNT_KEY_PEPPER = "<long-random-secret-generated-once>"
ALLOW_REPEAT_PARTICIPATION = false

[auth]
redirect_uri = "https://<your-app-domain>/~/+/oauth2callback"
cookie_secret = "<long-random-cookie-secret>"
client_id = "<google-oauth-client-id>"
client_secret = "<google-oauth-client-secret>"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

Do not use a Supabase publishable key for app storage. The app requires a server-only secret key because sensitive tables are protected with RLS.

Do not rotate `ACCOUNT_KEY_PEPPER` during data collection. Changing it makes prior participants appear new and prevents recovery of existing in-progress sessions.

Set `ALLOW_REPEAT_PARTICIPATION = true` only during testing. Set it to `false` before collecting real study responses to enforce one completion per Google account.

## Completion Privacy Flow

While a participant is in progress:

- `resume_links` contains only the opaque account key and random session id;
- `participant_sessions` contains the recoverable checkpoint for that same session id.

At final submission:

- `psychometric_pre_answers` stores pre-questionnaire answers by `session_id`;
- `psychometric_post_answers` stores post-questionnaire answers by `session_id`;
- `month_results` stores monthly decisions and calculated financial state by `session_id` and `month_number`;
- `session_summaries` stores the final score and financial summary by `session_id`;
- `completed_accounts` stores only the opaque account key for duplicate prevention;
- the temporary `resume_links` row is deleted.

The completed experimental data is connected by session id, not by Google email, name, or profile photo.
