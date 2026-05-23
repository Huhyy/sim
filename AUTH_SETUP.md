# Google Authentication Setup

The app uses Google authentication only to resume unfinished participation and prevent duplicate submissions. It stores a peppered HMAC account key in Supabase, never the participant's email or Google profile alongside responses.

## 1. Run The Supabase Migration

Run `migration_identity_separation.sql` once in the Supabase SQL Editor before allowing participants to use the authenticated app.

The migration:

- creates `study_responses` for anonymous final responses;
- creates `resume_links` for temporary in-progress recovery;
- creates `completed_accounts` for duplicate prevention only;
- protects the old `participants` answer table as legacy response data;
- enables Row Level Security on sensitive public tables;
- installs the atomic `finalize_study_response` function.

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

[auth]
redirect_uri = "https://<your-app-domain>/~/+/oauth2callback"
cookie_secret = "<long-random-cookie-secret>"
client_id = "<google-oauth-client-id>"
client_secret = "<google-oauth-client-secret>"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

Do not use a Supabase publishable key for app storage. The app requires a server-only secret key because sensitive tables are protected with RLS.

Do not rotate `ACCOUNT_KEY_PEPPER` during data collection. Changing it makes prior participants appear new and prevents recovery of existing in-progress sessions.

## Completion Privacy Flow

While a participant is in progress:

- `resume_links` contains only the opaque account key and random session id;
- `participant_sessions` contains the recoverable checkpoint, including in-progress questionnaire responses.

At final submission, one database transaction:

- saves answers and final score to `study_responses` under an unrelated response id;
- records the opaque key alone in `completed_accounts`;
- deletes the temporary `resume_links` row;
- deletes the answer-bearing `participant_sessions` row.

The completed response has no account key, session id, Google email, or Google user identifier.

Once deployment is complete and no previous app version writes to `participants`, that table can be renamed to `legacy_responses` for clarity or exported and archived.
