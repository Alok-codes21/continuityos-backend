/**
 * ContinuityOS — Incoming Member Workspace
 * Tailored onboarding hub for incoming engineers showing only approved, verified knowledge.
 */

import {
  getProject,
  getTeamMembers,
  getComponents,
  getTasks,
  getDecisions,
} from '../../services/mock-api.js';

export default async function renderPage(container) {
  const [project, teamMembers, components, tasks, decisions] = await Promise.all([
    getProject(),
    getTeamMembers(),
    getComponents(),
    getTasks(),
    getDecisions(),
  ]);

  const incomingUser = teamMembers.find(m => m.id === 'tm-4') || {
    name: 'Sam Chen',
    role: 'Junior Backend Engineer',
    avatar: 'SC',
  };

  // First day checklist state
  let checklist = [
    { id: 'chk-1', text: 'Clone repository & configure local docker-compose environment', done: true },
    { id: 'chk-2', text: 'Review Kafka ADR-007 partitioning strategy', done: true },
    { id: 'chk-3', text: 'Complete Staging Pipeline OOM crash recovery rehearsal', done: false },
    { id: 'chk-4', text: 'Shadow Alex Rivera on pgBouncer connection pool tuning', done: false },
    { id: 'chk-5', text: 'Verify AWS staging EKS cluster read credentials', done: false },
  ];

  function render() {
    const doneCount = checklist.filter(c => c.done).length;
    const progress = Math.round((doneCount / checklist.length) * 100);

    container.innerHTML = `
      <div class="incoming-workspace-page">
        <!-- ── Welcome Hero Banner ───────────────────────────────────── -->
        <div class="cos-card mb-4 p-4 text-white position-relative overflow-hidden" style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); border: none;">
          <div class="d-flex align-items-center justify-content-between flex-wrap gap-3">
            <div>
              <div class="d-flex align-items-center gap-2 mb-2">
                <span class="badge bg-white text-primary fw-bold" style="font-size: 11px;">INCOMING ENGINEER ONBOARDING</span>
                <span style="font-size: 12px; opacity: 0.85;">Project Atlas · NovaTech</span>
              </div>
              <h1 class="fw-bold fs-4 m-0">Welcome to Project Atlas, ${incomingUser.name}!</h1>
              <p class="mt-2 mb-0" style="font-size: 13px; opacity: 0.9; max-width: 600px;">
                You have been assigned as the incoming transition owner for the <strong>Data Pipeline Service</strong> and <strong>Event Bus (Kafka)</strong>. Below is your certified handover briefing.
              </p>
            </div>
            <div class="d-flex flex-column gap-2">
              <a href="#/rehearsal" class="cos-btn" style="background: #ffffff; color: var(--primary); font-weight: 700; border: none; white-space: nowrap;">
                <i class="bi bi-mortarboard-fill text-primary me-1"></i> Launch Readiness Rehearsal
              </a>
              <button class="cos-btn" style="background: rgba(255,255,255,0.15); color: #fff; border: 1px solid rgba(255,255,255,0.25);" onclick="window.location.hash='#/assistant'">
                <i class="bi bi-chat-dots me-1"></i> Query Knowledge Assistant
              </button>
            </div>
          </div>
        </div>

        <!-- ── First-Day Checklist & Core Contacts ────────────────────── -->
        <div class="row g-4 mb-4">
          <!-- First-Day Checklist -->
          <div class="col-12 col-lg-7">
            <div class="cos-card h-100 p-4 bg-white">
              <div class="d-flex align-items-center justify-content-between mb-3">
                <div class="fw-bold fs-6 text-dark"><i class="bi bi-check2-all text-success me-2"></i>First-Week Continuity Checklist</div>
                <span class="badge bg-success-subtle text-success" style="font-size: 11px;">${doneCount}/${checklist.length} Complete (${progress}%)</span>
              </div>
              <div class="progress mb-3" style="height: 6px;">
                <div class="progress-bar bg-success" style="width: ${progress}%;"></div>
              </div>

              <div class="list-group list-group-flush border rounded mb-3">
                ${checklist.map(item => `
                  <label class="list-group-item d-flex align-items-center gap-2 p-3 ${item.done ? 'bg-light' : ''}" style="cursor: pointer;">
                    <input class="form-check-input chk-box me-1" type="checkbox" data-id="${item.id}" ${item.done ? 'checked' : ''}>
                    <span style="font-size: 13px; ${item.done ? 'text-decoration: line-through; color: var(--text-muted);' : 'color: var(--text-primary); font-weight: 500;'}">
                      ${item.text}
                    </span>
                  </label>
                `).join('')}
              </div>

              <div class="d-flex justify-content-between align-items-center" style="font-size: 11px; color: var(--text-muted);">
                <span><i class="bi bi-info-circle me-1"></i>Completing rehearsal unlocks certification credit.</span>
                <a href="#/rehearsal" class="fw-bold text-primary text-decoration-none">Open Scenario Practice →</a>
              </div>
            </div>
          </div>

          <!-- Team Contacts & Escalations -->
          <div class="col-12 col-lg-5">
            <div class="cos-card h-100 p-4 bg-white">
              <div class="fw-bold fs-6 text-dark mb-3"><i class="bi bi-people-fill text-primary me-2"></i>Key Project Contacts</div>

              <div class="d-flex flex-column gap-3">
                <div class="p-2 rounded border bg-light d-flex align-items-center justify-content-between">
                  <div class="d-flex align-items-center gap-2">
                    <div style="width: 34px; height: 34px; border-radius: 50%; background: #fee2e2; color: #dc2626; display: flex; align-items: center; justify-content: center; font-weight: 700;">
                      AR
                    </div>
                    <div>
                      <div class="fw-bold" style="font-size: 12px;">Alex Rivera</div>
                      <div style="font-size: 11px; color: var(--text-muted);">Senior Backend (Departing Lead)</div>
                    </div>
                  </div>
                  <a href="#/handover-interview" class="cos-btn cos-btn-ghost btn-xs text-primary">Interview Log</a>
                </div>

                <div class="p-2 rounded border bg-light d-flex align-items-center justify-content-between">
                  <div class="d-flex align-items-center gap-2">
                    <div style="width: 34px; height: 34px; border-radius: 50%; background: #e0e7ff; color: #4f46e5; display: flex; align-items: center; justify-content: center; font-weight: 700;">
                      JK
                    </div>
                    <div>
                      <div class="fw-bold" style="font-size: 12px;">Jordan Kim</div>
                      <div style="font-size: 11px; color: var(--text-muted);">DevOps & Kubernetes Contact</div>
                    </div>
                  </div>
                  <span class="badge bg-light text-muted border">#devops</span>
                </div>

                <div class="p-2 rounded border bg-light d-flex align-items-center justify-content-between">
                  <div class="d-flex align-items-center gap-2">
                    <div style="width: 34px; height: 34px; border-radius: 50%; background: #ccfbf1; color: #0d9488; display: flex; align-items: center; justify-content: center; font-weight: 700;">
                      MP
                    </div>
                    <div>
                      <div class="fw-bold" style="font-size: 12px;">Maya Patel</div>
                      <div style="font-size: 11px; color: var(--text-muted);">Product Manager</div>
                    </div>
                  </div>
                  <span class="badge bg-light text-muted border">#proj-atlas</span>
                </div>
              </div>

              <div class="p-3 rounded border bg-white mt-3" style="font-size: 12px;">
                <div class="fw-bold text-dark mb-1"><i class="bi bi-question-circle text-warning me-1"></i>Recommended Questions for 1:1:</div>
                <ul class="ps-3 m-0 text-muted" style="font-size: 11px;">
                  <li>"What are the unwritten retry policies in the Celery worker queue?"</li>
                  <li>"How do you monitor Kafka broker lag during night spikes?"</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <!-- ── Approved Handover Architecture Dossier ─────────────────── -->
        <div class="cos-card mb-4">
          <div class="cos-card-header">
            <div>
              <div class="cos-card-title"><i class="bi bi-shield-check text-success me-2"></i>Approved Institutional Knowledge for your Services</div>
              <div class="cos-card-subtitle">Verified facts extracted from Project Atlas architectural records</div>
            </div>
            <span class="badge bg-success-subtle text-success">Certified Handover</span>
          </div>
          <div class="table-responsive">
            <table class="table cos-table mb-0 align-middle">
              <thead>
                <tr>
                  <th style="width: 25%;">Service</th>
                  <th style="width: 45%;">Approved Architecture Claim</th>
                  <th style="width: 15%;">Evidence Citation</th>
                  <th style="width: 15%; text-align: right;">Action</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>
                    <div class="fw-bold" style="font-size: 12px;">Data Pipeline Service</div>
                    <span class="badge bg-danger-subtle text-danger" style="font-size: 9px;">CRITICAL SERVICE</span>
                  </td>
                  <td style="font-size: 12px;">
                    Processes 50k events/minute during peak hours. Uses pgBouncer connection pool of 80 to prevent RDS saturation.
                  </td>
                  <td>
                    <span class="badge bg-light text-primary border" style="font-size: 10px;">Architecture Spec v2.3</span>
                  </td>
                  <td style="text-align: right;">
                    <button class="cos-btn cos-btn-ghost btn-xs text-primary" onclick="window.location.hash='#/uncertainty-ledger'">Inspect Claim</button>
                  </td>
                </tr>
                <tr>
                  <td>
                    <div class="fw-bold" style="font-size: 12px;">Event Bus (Kafka)</div>
                    <span class="badge bg-warning-subtle text-warning" style="font-size: 9px;">INFRASTRUCTURE</span>
                  </td>
                  <td style="font-size: 12px;">
                    12 topics with 4 partitions each. Raw-events topic has 7-day retention; entity-state uses log compaction.
                  </td>
                  <td>
                    <span class="badge bg-light text-primary border" style="font-size: 10px;">ADR-007</span>
                  </td>
                  <td style="text-align: right;">
                    <button class="cos-btn cos-btn-ghost btn-xs text-primary" onclick="window.location.hash='#/uncertainty-ledger'">Inspect Claim</button>
                  </td>
                </tr>
                <tr>
                  <td>
                    <div class="fw-bold" style="font-size: 12px;">Auth Service</div>
                    <span class="badge bg-light text-secondary border" style="font-size: 9px;">SERVICE</span>
                  </td>
                  <td style="font-size: 12px;">
                    OAuth2 + JWT with multi-tenant RBAC hierarchical roles (org:admin, org:member, resource:owner).
                  </td>
                  <td>
                    <span class="badge bg-light text-primary border" style="font-size: 10px;">DEC-002</span>
                  </td>
                  <td style="text-align: right;">
                    <button class="cos-btn cos-btn-ghost btn-xs text-primary" onclick="window.location.hash='#/uncertainty-ledger'">Inspect Claim</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;

    // ── Attach Event Listeners ─────────────────────────────────────
    container.querySelectorAll('.chk-box').forEach(cb => {
      cb.addEventListener('change', () => {
        const id = cb.getAttribute('data-id');
        const item = checklist.find(c => c.id === id);
        if (item) item.done = cb.checked;
        render();
      });
    });
  }

  render();
}
