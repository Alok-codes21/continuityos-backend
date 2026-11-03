# ContinuityOS backend (MVP)

FastAPI + SQLAlchemy (SQLite by default, Postgres via DATABASE_URL). No paid APIs. Extraction is rule-based; a free LLM (Gemini/Groq) is optional.

Run: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload` then open `/docs`.
Test: `cd backend && python -m pytest -q`.

Implemented: auth + RBAC, orgs/projects, GitHub and file-upload connectors (others show as unavailable), ingestion with dedupe, secret redaction and prompt-injection flagging, claim ledger (hash chain) with 7 states, knowledge graph, departure impact simulator, interviews, approvals, handover document + PDF, cited Q&A and rehearsal.
Connectors: GitHub, Slack (selected public channels), Google Drive/Docs (selected folder), file upload. Teams, Zoom, Notion show as unavailable.
Also: per-author consent (withdraw removes data), stored document text encrypted at rest, incremental GitHub sync, scenario-based rehearsal readiness, adaptive interview follow-ups.
Not yet: Postgres migrations, background sync.
Demo data: `SEED_ADMIN_PASSWORD=... python -m app.seed` (all content labelled synthetic).

## Language

Application-authored responses, errors, interview questions, handover labels,
comments, documentation, tests and demo data use English. Optional LLM answer
and follow-up prompts explicitly request plain English. Future commit messages
should also use English.

Source quotes, uploaded content, user names, questions and answers preserve the
original text. The backend does not translate these fields, and it does not
reject non-English user input. A source excerpt can therefore contain another
language. Generated output from an external model is not a guaranteed language
filter.
