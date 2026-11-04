# ContinuityOS

Evidence-led knowledge continuity: import selected knowledge, review claims and gaps, interview a departing colleague, and give an incoming colleague an approved, cited handover.

## Live demo

https://continuityos-fsbr.onrender.com

The free hosting instance can sleep when idle. Allow roughly 50-60 seconds for the first request to wake it, then retry if needed. This is a demonstration, not a production-ready service. Use synthetic data only. Do not upload personal/company documents, connect real providers, or reuse a real password.

### Demo accounts

Demo passwords are shared by the maintainer, not stored in this repository.

| Role in the demo organisation | Email | What to try |
| --- | --- | --- |
| Demo Manager (admin) | continuity-demo-manager-20261104@example.com | Overview, sources, claims, graph, departure simulation, interviews, handovers, security and settings |
| Demo Reviewer (manager) | continuity-demo-reviewer-20261104@example.com | Review an approval requested by another account; inspect approved handover and evidence |
| Priya Demo (contributor) | continuity-demo-contributor-20261104@example.com | Open the active interview, draft an answer, confirm it, inspect sources and claims |
| Demo Incoming (incoming) | continuity-demo-incoming-20261104@example.com | Read the assigned approved handover, download PDF, ask cited questions, rehearse and submit skills |

After signing in, select **Synthetic Payments Handover Demo** in the top project picker. The other "My first project" is the account's empty registration sandbox, not the populated demo. Roles shown above apply to the shared demo organisation. Use separate browser profiles/private windows when testing several accounts at once.

### Seeded synthetic scenario

The shared organisation is **ContinuityOS Synthetic Demo**. Three explicitly synthetic documents describe payments-service, auth-service and identity-service, fictional owners, decisions, runbooks and open work. The initial dataset has 27 extracted claims, a deliberate timeout conflict (30 versus 60 seconds), a bound Priya Demo identity, one active interview with two open root questions, a departure simulation, a rehearsal evaluation and one approved version-1 handover assigned to Demo Incoming. Incoming skill data was submitted for manager review.

These counts describe initial setup, not a promise that shared state never changes. Other testers can change the data. Demo data and accounts may be reset. Do not change shared passwords, revoke all sessions, purge sources or withdraw consent during a normal walkthrough. Ask the maintainer for a reset if another tester has completed a pending workflow.

### Suggested test walkthrough

1. Sign in as Demo Manager and select the populated demo project. Overview should show real counts; Sources should show three synthetic documents. In Uncertainty Ledger, inspect evidence and the 30/60-second timeout conflict.
2. Open Knowledge Graph and find Priya Demo's payments-service ownership and documented dependencies. In Impact Simulator, select Priya Demo and run a departure simulation. The result is documentation-derived risk, not an outage prediction.
3. Sign in as Priya Demo in a separate window. Select the demo project, open Handover Interview and the active interview. A decision-rationale question and timeout-conflict question are initially open. To exercise the mutation workflow, draft a synthetic answer, then confirm it. Drafts do not count as manager-approved knowledge.
4. As Demo Reviewer, open Handover Centre and review the new pending interview-answer approval. Approval changes shared data. An account cannot approve its own request. The pre-approved handover can also be read without changing anything.
5. As Demo Incoming, select the demo project. In Incoming Workspace, read the assigned approved handover and download its PDF. Open AI Assistant and ask "Who owns payments-service?" or "Who owns auth-service?" Inspect the cited source excerpts.
6. In Rehearsal, start a session, ask a question and evaluate knowledge coverage. The unresolved timeout conflict should remain a gap rather than being treated as known. This measures sampled workspace coverage, not employee competency.
7. Optionally submit a clearly synthetic skill/profile record as Demo Incoming and inspect it with a manager. Do not enter real personal information.

### Verification and boundaries

All four generated demo credentials were verified by signing out and signing back in. Shared project roles, contributor interview access, separate-manager handover approval and incoming handover access were checked on the live deployment. API reads confirmed three records, 27 claims, one interview, one approved handover and one stored simulation at initial setup. A cited ownership answer and rehearsal evaluation were exercised. No real provider credentials were connected.

The integration's last local check passed 83 backend tests, two renderer/security tests, four multi-step browser scenarios and a production frontend build. This is not an exhaustive production security, accessibility, concurrency or real-provider acceptance test.

Health routes: `/api/health` checks liveness; `/api/ready` checks database access and the projects table, and currently reports `schema_migration_verified: false`. A successful readiness response is not a migration/backfill or backup/restore guarantee.

## Development and integration

- [Integration setup, coverage and known gaps](docs/INTEGRATION.md)
- [FastAPI backend setup, source scopes and limitations](backend/README.md)

The live integration uses the Vite `frontend/` and FastAPI `backend/`, built with `Dockerfile.integration`. The legacy Flask application and legacy Dockerfile remain in the repository but are not the live integration entry point. No paid model is required; deterministic extraction and retrieval work without an external model.
