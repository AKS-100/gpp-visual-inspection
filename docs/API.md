# API

No REST API exists in this MVP — the application is a single Streamlit
process calling the service layer directly in-process.

## Why this doc exists anyway
The database schema (`api_tokens` table) and layered architecture
(services depending only on repository interfaces) are already
API-ready: a future REST layer would call the same `core/services/*`
classes this Streamlit app calls, with no service-layer changes.

## Future scope
See `docs/FutureScope.md` — REST API integration is explicitly listed as
deferred, not started.
