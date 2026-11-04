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
- All 12 routes use `src/live/pages.js` and the live API client. The original mock pages are retained as source history but are not imported by the runtime.
- Sidebar styling, design tokens and navigation are reused. Page content was replaced with live forms and results rather than preserving fictional demo answers and scores.
- Some technical outputs (simulations, ledger, evidence inspection, approvals, skills) are shown as readable JSON rather than bespoke visualisations.
- Refresh data reloads the current page. Uploads, connector creation, sync, handover generation/approval and membership updates refresh relevant data automatically.
- Source selection dates explicitly use UTC. Saving preserves previously selected dates and inclusion state.
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

Backend: **80 passed, 2 dependency deprecation warnings**. Frontend production build: **passed**. Browser suites: **3 passed**. The suites include many assertions; this count is three scenarios, not three individual checks.

| Page / flow | Result | Evidence and boundary |
| --- | --- | --- |
| Registration/login/logout | PASS | Browser registration, live session, logout and login |
| Overview | PASS | Real empty workspace counts, health formula and risk render; no mock population |
| Settings / projects | PASS | New project, project switching, organisation and project members, password change and fresh login |
| Sources | PASS, external providers untested | Upload/extraction, job/record refresh, manual connector, source selection/date persistence and manual sync. No live GitHub/Slack/Drive credentials used |
| Claims / uncertainty ledger | PASS | Extracted claim list, detail/evidence, correction approval request and event history |
| Knowledge graph | PASS | Extracted nodes/edges render and explicit person-to-account binding |
| Impact simulator | PASS | Documented person selection, departure result and bus factor |
| Interview | PASS | Manager starts, employee drafts/confirms, approval resolves conflict, manager completes. Other unanswered questions remain visible as gaps |
| Handover centre / approval | PASS | Generate, request, reject own approval attempt, second manager approves |
| Incoming workspace | PASS | Assigned approved handover readable, skill self-declaration and manager skill approval |
| PDF | PASS | Browser downloads actual PDF; both pages visually inspected, evidence and missing knowledge retained |
| Assistant | PASS | Real question response with accessible evidence citations |
| Rehearsal | PASS | Start session, ask and coverage evaluation, without claiming employee competency |
| Security | PASS, partial controls coverage | Page load, audit, consent grant assertion, mode update, confirmed record deletion. Manual reverification UI is wired but was not clicked in browser (covered by backend regression tests) |
| Mobile | PASS, sampled route | 390x844 incoming workspace, no horizontal overflow, navigation opens/closes. Not an exhaustive device/browser matrix |

Screenshots of every route and key populated flows were captured. Key desktop pages, graph, interview, approved handover, incoming workspace, assistant, simulator, mobile screen and both PDF pages were visually inspected. Early mobile/header overlap and stale organisation/role labels were fixed and retested. Generated test outputs and credentials are not committed.

## Explicit gaps

Task CRUD, sprint scheduling, automatic notifications, OAuth token refresh and model-provider administration have no matching integrated API and are explicitly unavailable rather than simulated. Connector revocation and organisation role editing exist in the backend but have no new UI controls in this integration. Manager project membership can still be managed through the API; the new combined member-management form is admin-only.

This is local integration verification, not production certification. Live external provider operation, Docker execution, production PostgreSQL, TLS deployment, migrations/backfill, multi-worker throttling, concurrent approval/admin invariants and a full accessibility/browser matrix were not established by this run. Existing documented backend limits still apply. No paid LLM is required; the rule-based fallback remains the default.
