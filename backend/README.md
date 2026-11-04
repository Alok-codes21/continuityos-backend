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

## Selected GitHub documentation

Create a GitHub integration with `scopes.permissions` including `documents`
(and `repo` as well if commit/PR/issue ingestion is wanted). On source creation
or the source selection PUT endpoint, set `file_paths`, for example
`["README.md", "docs/*.md"]`. No documentation files are fetched by default.
Selected supported files are README or docs/ text files with .md, .rst or .txt
extensions. Paths are case-sensitive glob patterns relative to the repository.
The source GET response reports the saved selection. Existing integrations need
an explicitly approved documents scope; legacy repo scope is not expanded.

Each sync pins the default branch commit before fetching file contents. Limits:
40 selected files, 200 KB per file and 2 MB total per sync. Symlinks, submodules,
binary/non-UTF-8 files and unsupported types are excluded. Partial fetches report
warnings; truncated fetches do not advance the sync cursor. Files use the normal
redaction, permission, extraction, deduplication, version and citation pipeline.
These are current file snapshots, not per-file change history or deletion tracking.

## Selected code-file snapshots

GitHub integration permission `code_files` is separate from `documents` and
legacy `repo`. Choose source-relative `file_paths` such as `["src/*.py"]` using
the same source/selection endpoints. File paths, extension allowlists and the
same file/byte limits apply; no repository files are executed or imported.
Supported extensions: .py, .js, .jsx, .ts, .tsx, .go, .java, .rb, .rs, .cs, .c,
.h and .cpp. Common vendor/build directories, symlinks and submodules are skipped.

Python uses the standard-library AST to extract declared classes/functions and
static imports. Other supported languages use limited declaration/import text
patterns, not full language parsers. File paths create module components; imports
create inferred dependencies and declared symbols link to the module. Explicit
owner/maintainer comments become inferred `possible_owner` hints, never qualified
ownership. Existing CODEOWNERS remains the documented ownership source.

Limits: no execution, runtime call graph, dynamic import resolution, cross-file
symbol resolution or guaranteed architecture understanding. Old snapshots and
claims are retained; removed symbols/files are not automatically retired. Code
snapshots have no reliable author attribution; opt-in consent mode blocks these
records rather than silently assuming consent. Existing document records retain
the current document opt-in exemption. The API can reject content types or paths
before fetch/ingestion but does not reproduce every provider ACL inside the app.

Incoming users may now submit their own skill/profile records and view their
own pending records; a different manager must approve them. This does not grant
incoming users access to source administration or other contributors' drafts.

## Detailed audit: ingestion and account limits

Session revocation uses sub-second issue/cutoff timestamps. Users can change
passwords with `POST /api/auth/change-password`; this revokes existing sessions.
Temporary-password replacement is available but not yet enforced at first login.
Membership is admin-provisioned, not an email invitation/acceptance workflow.
Failed-login throttling remains process-local; multi-worker deployments need a
shared throttle. Last-admin concurrent demotion protection is not yet guaranteed.

Slack history/thread and Drive folder caps save provider continuation cursors;
repeat sync to continue. A failed fetch does not commit a new cursor. The cursor
is continuation state, not a background sync schedule. Capped GitHub snapshots
and skipped selected binary/oversized files report incomplete coverage. When
code/docs snapshots are selected, CODEOWNERS uses the same pinned commit SHA.
File selection dates refer to the repository snapshot commit, not each file's
last modification. Included selections use OR semantics; excluded rows are not
negative rules overriding other included rows. Bounded dates exclude undated
records, and timezone-qualified bounds are normalized to UTC.

Consent currently uses exact provider author identifiers, not a verified global
person mapping. Configure each source identity separately. An author's display
name change or alias is not automatically resolved for consent. Uploaded document
records retain the documented opt-in exception; code snapshots do not.

Request bodies are bounded to 12 MB before multipart parsing; uploaded files
remain capped at 10 MB. PDFs are limited to 300 pages and two million extracted
characters and are closed after extraction. Set upload form `record_type` to
`meeting` or `document` to override heuristic classification (`auto` is default).
Existing PostgreSQL deployments must widen sources.last_cursor to TEXT before
using long continuation state; create_all does not migrate existing columns.


### Detailed audit lifecycle changes

Dedupe is per source identity and latest-version fingerprint, not project-wide text.
Title, author, URL, type and connector metadata changes are version-significant.
Reverting A -> B -> A creates a third version. Old hashes are supported as legacy
rows but the first post-upgrade sync may create one extra version.
Deletion removes unsupported claims even when previously verified and removes
record-bound tasks/decisions. It also invalidates all project handover, rehearsal
and stored risk snapshots because they may embed deleted text. This is deliberately
conservative: regenerate and approve a handover after deletion. Previously exported
PDFs and backups are outside this API's deletion control.

Derived content fields now use encrypted text/JSON, including claim statements,
evidence excerpts, graph labels, and materialized handover/rehearsal content. This
is not whole-database encryption: routing keys, identities, timestamps and the
append-only audit ledger remain readable. Production needs encrypted disks/backups
and restricted database access too. Wrong-key reads fail rather than returning blank.
Existing PostgreSQL installations MUST migrate changed JSON columns to TEXT using
`ALTER TABLE ... ALTER COLUMN ... TYPE TEXT USING ...::text` before deploying this
version. Existing plaintext rows remain readable, but are not encrypted until
rewritten. Take a verified backup and run a separate controlled encryption backfill
before claiming all historical data is encrypted. Do not deploy this schema change
blindly to an existing database. New databases use the new types automatically.

Consent still records a manager's assertion for an exact provider author identifier;
it is not independently authenticated employee consent. Do not use opt-in mode as
proof of personal legal consent until a verified provider-identity/self-service
consent flow exists. Only manual-upload documents are exempt from the opt-in author
check. Disconnecting removes the local credential, not the provider's token grant;
revoke it at the provider separately. Imported data requires a separate deletion.
Unanswered questions are rechecked against the original role; missing evidence
keeps the gap open, and supported evidence closes it. Generic contradiction
detection remains limited to explicit configuration values.


Source person labels no longer auto-bind employee accounts, even on an exact
name match. A manager must first PUT `/api/projects/{id}/graph/people/{key}/account`
with a project member's `user_id` after checking the identity. Interviews require
this binding. Two people bound to different accounts cannot be merged. Do not use
an extracted first name as authority to let someone confirm an employee answer.
Interview progress counts approved answers, not submitted drafts; confirmation is
idempotent and pending approvals block completion. Corrections are re-extracted
as one unambiguous claim of the same category; unsupported free-form edits return
422 rather than leaving graph fields inconsistent. Scope-change approvals currently
cover inclusion/exclusion only, not date/type/file-selection edits. Graph edges
retain a primary claim reference; complete supporting evidence is available on
claims, but a relationship-evidence join table is still a future improvement.

### Handover audience and runtime safeguards

Handover snapshots are generated for incoming visibility, never manager visibility.
Manager-only simulation risk/dependents are not copied into incoming documents.
Live claim visibility is rechecked when incoming members read/export, and the
normal project context rejects removed members. Handover approval binds a content
digest and version; pending requests are idempotent. Source updates can make old
snapshots stale: regenerate after material changes. Existing pre-upgrade handovers
must be deleted/regenerated; the new filtering cannot sanitize their stored text.
Q&A ignores historical source versions, stale/conflicting claims and generic
approved corrections whose old source quote does not support the edited statement.
Without a model, answers use retrieved text; lexical validation is still not general
semantic proof. Entailment accepts only an exact YES/NO. Rehearsal is sampled
workspace knowledge coverage, not employee competency; unresolved conflicts fail.
Re-verification requires a reason and is labelled a manual manager check.

Set APP_ENV=production explicitly. It rejects the development JWT secret, missing
field-encryption key, implicit/SQLite database and invalid time/page ranges. TLS_CERT
and TLS_KEY must both be present or both absent. /api/health is liveness; /api/ready
checks database connectivity and the projects table, NOT a complete schema migration
or encryption-backfill verification. There is still no migration runner or production
schema-version gate, no real PostgreSQL/container/HTTPS smoke test in this audit,
and upload concurrency must be bounded by the hosting proxy. These are deployment
blockers, not evidence that the backend is production-ready.
