# Frontend and FastAPI integration

The `integration-alok` branch combines the Vite frontend from main (`ec12108`) with FastAPI backend-alok (`9ee5efb`). The legacy Flask application, templates and Dockerfile are preserved and are not executed by this integration.

## Run locally

Requires Python 3.10+ and Node 22. Install the existing backend requirements, then:

```sh
cd frontend
npm ci
npm run build
cd ../backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. Register an account and organisation. The backend creates the first project. No demo records are loaded by the frontend. Development defaults use a local SQLite database. Do not use development secrets or SQLite for production.

For frontend development, start FastAPI on port 8000 and run `npm run dev` in `frontend`. Vite proxies `/api` to FastAPI. Override `API_TARGET` for a different development backend, or set `VITE_API_URL` at build time for separately hosted frontends. The built same-origin app needs neither override.

`Dockerfile.integration` builds and serves this combination. It does not replace the legacy Dockerfile. A Docker build was not tested in this environment.

## Data and UI behavior

- Authentication and selected project live in sessionStorage. Sign out clears them. User, organisation and role come from FastAPI.
- All 12 routes use `src/live/pages.js` and the live API client. Unused mock pages, mock API/store/demo data, obsolete router and unused topbar were removed from the Vite source. Legacy Flask files remain unchanged.
- Sidebar styling, design tokens and navigation are reused. Page content was replaced with live forms and results rather than preserving fictional demo answers and scores.
- All API results use escaped, labelled UI: summary cards, evidence blocks, definition lists and scrollable tables. Simulations, rehearsal evaluations, answers, claims and source content have dedicated views. No API JSON is dumped into page panels.
- Refresh data reloads current user/project permissions and the current page. Returning focus to a handover page rechecks access. Uploads, connector creation, sync, handover generation/approval and membership updates refresh relevant data automatically.
- Source selection dates explicitly use UTC. Saving preserves previously selected dates and inclusion state. A source with multiple selection rows has an explicit row picker and updates that exact row. Selection scope is evaluated across all included rows, not only the selected editing row.
- Diagram shows up to 28 graph nodes. The relationship list includes all returned edges. This is a documented-relationship graph, not a runtime call graph.
- Backend access control remains authoritative. Permission errors are shown, not treated as success. An approval requester cannot approve their own handover.
- Source access tokens are sent only to the configured backend and cleared from the input after submission. Do not connect real providers without appropriate authority.

## Automated checks

```sh
cd backend
python -m pytest -q
cd ../frontend
npm run build
npm run test:e2e
```

Browser tests start a dedicated FastAPI server on port 8765, use a new temporary SQLite database, create synthetic local accounts, and use local uploaded fixtures. Chrome defaults to `/usr/bin/google-chrome`; set `CHROME_PATH` if needed. Build the frontend before browser tests. They never call real provider accounts and never send account emails.

## Combined-app verification, 4 November 2026

Backend: **83 passed, 2 dependency deprecation warnings**. Frontend production build: **passed**. Browser suites: **4 passed**. The suites include many assertions; this count is four scenarios, not four individual checks.

| Page / flow | Result | Evidence and boundary |
| --- | --- | --- |
| Registration/login/logout | PASS | Browser registration, live session, logout and login |
| Overview | PASS | Real empty workspace counts, health formula and risk render; no mock population |
| Settings / projects | PASS | New project, project switching, organisation/project members, live eligible-member reads, role changes, password change/login and all-session revocation |
| Sources | PASS, external providers untested | Upload/extraction, job/record refresh, manual connector, source selection/date persistence and manual sync. Connector revoke/discovery, record content, limits, purge and scope requests also clicked. No live GitHub/Slack/Drive credentials used |
| Claims / uncertainty ledger | PASS | Claim list, detail/evidence, correction request, backend search filters, event history/pagination, re-analysis and ledger integrity verification |
| Knowledge graph | PASS | Extracted nodes/edges, explicit person-to-account binding and duplicate-identity merge |
| Impact simulator | PASS | Documented person selection, departure result and bus factor |
| Interview | PASS | Manager starts, employee drafts/confirms, approval resolves conflict, manager completes. Other unanswered questions remain visible as gaps |
| Handover centre / approval | PASS | Generate, request, hide own-approval controls, second manager approves; scope approval/rejection and approval history |
| Incoming workspace | PASS | Assigned approved handover readable, skill self-declaration and manager skill approval |
| PDF | PASS | Browser downloads actual PDF; both pages visually inspected, evidence and missing knowledge retained |
| Assistant | PASS | Real question response with accessible evidence citations |
| Rehearsal | PASS | Start session, ask, coverage evaluation and previous session history, without claiming employee competency |
| Security | PASS, partial controls coverage | Audit, extended audit, service health/readiness, grant/withdraw assertions, opt-in/out updates, record deletion, successful different-manager reverification and same-manager denial |
| Mobile | PASS, sampled route | 390x844 incoming workspace, no horizontal overflow, navigation opens/closes. Not an exhaustive device/browser matrix |

Screenshots of every route and key populated flows were captured. Key desktop pages, graph, interview, approved handover, incoming workspace, assistant, simulator, mobile screen and both PDF pages were visually inspected. Early mobile/header overlap and stale organisation/role labels were fixed and retested. Generated test outputs and credentials are not committed.

## Explicit gaps

Controls without a backend were removed, not left as unavailable stubs. Connector revoke, organisation role changes, manager project membership and the other existing backend workflows now have UI. Empty or role-ineligible actions are hidden. Actual project-member listing and consent mode on project reads were added to FastAPI so binding, skills, handover assignment and mode selection are based on current state rather than guesses.

This is local integration verification, not production certification. Live external provider operation, Docker execution, production PostgreSQL, TLS deployment, migrations/backfill, multi-worker throttling, concurrent approval/admin invariants and a full accessibility/browser matrix were not established by this run. Existing documented backend limits still apply. No paid LLM is required; the rule-based fallback remains the default.

## Missing-feature planning estimates

These are engineering effort estimates, not delivery promises or monetary quotes. Scope assumes one developer familiar with this codebase, including schema/API/UI, permission checks and regression tests. They do not include a production security review, vendor approval delays or paid services. Features below were present only as demo concepts; none is silently implemented by this integration. No new feature work is committed without approval.

| Removed demo concept / absent feature | Minimum useful scope | Estimated effort | Extra operating cost / uncertainty |
| --- | --- | --- | --- |
| Task CRUD and assignment | Persisted tasks, create/edit/complete, project access, audit and UI | 2-4 developer days | No new paid service required; external Jira/Linear sync is separate |
| Sprint settings and scheduling | Sprint model, dates/capacity, task association and UI | 2-4 days after task CRUD | No paid service required; calendar sync adds scope |
| Automatic notifications | Persisted inbox, preferences, durable delivery/retry and in-app UI | 3-5 days | Email/SMS/push vendors may charge; estimate excludes those channels |
| OAuth connect/refresh | Provider consent, encrypted refresh tokens, rotation/revoke and reconnect UI | 3-6 days per provider | Needs app registrations/consent and vendor review; manual token connectors already exist |
| Model-provider administration | Admin-only encrypted configuration, validation, usage limits and audit | 2-4 days | Optional hosted-model usage costs depend on provider; rule-based fallback stays free |
| Profile/avatar edits and organisation branding | Profile/organisation update APIs, validation, optional image storage and UI | 1-3 days | Image storage cost depends on deployment; read-only identity already uses live data |
| Appearance/theme preference | Local persisted theme with contrast/device testing | 0.5-1 day | Frontend-only, no paid service; not a backend sync gap |
| Personal notification/bell counts and activity reminders | Requires real event rules and notification delivery, not invented counters | Included in notification scope above | Not a separate fake counter implementation |

These ranges are additive only after choosing requirements. They are not a claim that every original decorative demo element warrants a product feature.

## API coverage and new click tests

The frontend covers every existing application workflow in the auth, sources, knowledge and people routers: session security; organisation/project creation and membership/roles; catalogue/connect/revoke/discover/select/sync/upload; record reads/deletion/source purge; consent/mode; overview/claims/corrections/reverification/history/integrity; graph/binding/merge; gaps/re-analysis/risk/simulation/history; ask/rehearsal/history; skills; interviews; approvals/history/scope changes; handovers/assignment/PDF. Health/readiness are available in Security. Backend technical OpenAPI endpoints are documentation, not product page actions. Optional list limits and ledger sequence pagination have UI. This does not mean every failure combination is browser-tested.

`npm run test:unit` also passes two rendering/security unit tests, including escaped hostile field/value content. All four browser scenarios run against FastAPI serving the built frontend. The maintenance scenario adds click coverage for merge, approve/reject/history, read limits, filters, health/readiness, audit and manager project membership. Destructive controls require confirmation. Buttons that are invalid by role, own approval or empty eligible choices are hidden. Backend validation remains the final authority.

## Integrated snapshot review and follow-up

ChatGPT reviewed the current unpushed integration source in the existing review conversation on 4 November 2026. Its pre-fix ratings were synchronization 8.5/10, UI 8/10 and scoped MVP security 7.5/10. This is external review input, not security certification or a post-fix score. Verdict: suitable for a restricted synthetic-data demo, not public production use with real employee/provider data.

Confirmed findings fixed and retested:
- Consent-mode changes now warn that opt-in permanently purges ungranted non-document records. Withdrawal warns about its destructive effect. Both reload authoritative project and page state; cancelling changes nothing.
- Source editing targets an explicit selection ID, validates the row belongs to that source/project/integration, and offers a row picker when more than one exists. Regression proves the other row is unchanged and an unrelated row is rejected.
- Reading or downloading a handover clears previously displayed content before the access-checked request. Returning focus to handover pages refreshes current permissions. Downloaded files and already-seen knowledge cannot be recalled.
- Discovery has a defensive empty-selection guard, and the browser regression verifies discovery is absent before a connector exists.
- Renamed the handover section to avoid implying every included claim needs review. Claim state and verification method remain visible.

The alleged high-priority cross-interview confirmation issue was not present: `services/interview.py:confirm` already rejects a response whose `interview_id` differs from the current interview before creating approval. The initial review packet contained routers but omitted that service, so its claim was conditional. A new API regression confirms HTTP 404. Existing idempotent confirmation checks also pass. Client-role hiding is usability only; backend checks remain authoritative.

Remaining risks: sessionStorage bearer tokens need strong XSS defenses and a production session/CSP review; administrator-recorded author consent is not verified employee consent; manual provider tokens have no OAuth refresh lifecycle; role/source changes invalidate server access but cannot undo prior disclosure; real providers, Docker and production deployment remain untested here.

The follow-up review received the code proof and fix/test summary. It retained GO for a controlled synthetic-data demo and NO-GO for real organisational data or production use. It explicitly acknowledged the cross-interview issue was not a confirmed defect and that it had not independently inspected the post-fix branch or run the tests. No revised numerical score was supplied. Browser regressions additionally prove cancelling opt-in preserves the persisted mode and a simulated handover access-denied response clears previous on-screen content; the latter is a client-error-path test, not a substitute for backend authorization tests.
