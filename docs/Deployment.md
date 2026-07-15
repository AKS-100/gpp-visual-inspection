# Deployment

## Current scope
This is an internship-prototype MVP designed to run locally via
`streamlit run app/main.py`. It is not configured for multi-user
concurrent production deployment.

## Known constraints
- **SQLite**: single-writer database. Fine for a demo or single-operator
  use; a real multi-station deployment would need PostgreSQL (the
  repository interfaces make this a swap-in, not a rewrite — see
  Architecture.md).
- **No containerization yet**: a `Dockerfile` isn't included. Adding one
  is straightforward: base `python:3.11-slim`, `pip install -r
  requirements.txt`, `EXPOSE 8501`, `CMD ["streamlit", "run", "app/main.py"]`.
- **Secrets**: no `.env`/secrets management yet — there are no external
  API keys to manage today (auth is local, ML inference is local).

## Recommended path to a real deployment
1. Swap `SqliteUserRepository` etc. for PostgreSQL implementations of the
   same interfaces.
2. Add a reverse proxy (nginx) in front of Streamlit for TLS.
3. Move the trained model file to persistent shared storage if running
   multiple app instances.
4. Add the `api_tokens` table (already schema-documented in
   FutureScope.md) if a REST API is introduced alongside the UI.
