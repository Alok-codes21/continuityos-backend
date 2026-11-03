/**
 * ContinuityOS — Handover Centre Page
 * Complete lifecycle management of knowledge transition briefs and approvals.
 */

import {
  getHandovers,
  getTeamMembers,
  updateHandover,
} from '../../services/mock-api.js';

export default async function renderPage(container) {
  let [handovers, teamMembers] = await Promise.all([
    getHandovers(),
    getTeamMembers(),
  ]);

  let activeTab = 'active'; // 'active', 'draft', 'review', 'approved'
  let selectedHandoverId = handovers[0]?.id || 'ho-001';
  let showCommentModal = false;

  function render() {
    const selectedHo = handovers.find(h => h.id === selectedHandoverId) || handovers[0];
    const departing = teamMembers.find(m => m.id === selectedHo.from) || { name: 'Alex Rivera', role: 'Senior Backend' };
    const incoming = teamMembers.find(m => m.id === selectedHo.to) || { name: 'Sam Chen', role: 'Junior Backend' };

    // Filter list by tab
    let displayList = handovers;
    if (activeTab === 'active') displayList = handovers.filter(h => h.status === 'in-progress' || h.status === 'awaiting-review');
    else if (activeTab === 'draft') displayList = handovers.filter(h => h.status === 'draft');
    else if (activeTab === 'review') displayList = handovers.filter(h => h.status === 'awaiting-review');
    else if (activeTab === 'approved') displayList = handovers.filter(h => h.status === 'approved');

    container.innerHTML = `
      <div class="handover-centre-page">
        <!-- ── Top Header ────────────────────────────────────────────── -->
        <div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
          <div>
            <div class="d-flex align-items-center gap-2">
              <h1 class="page-title m-0" style="font-size: 20px; font-weight: 800;">Handover Governance Centre</h1>
              <span class="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1" style="font-size: 11px;">
                <i class="bi bi-briefcase me-1"></i>Official Knowledge Transfer Records
              </span>
            </div>
            <p class="page-subtitle m-0 mt-1" style="font-size: 13px; color: var(--text-secondary);">
              Formal handover dossiers, stakeholder approval sign-offs, and versioned transition manifests.
            </p>
          </div>
          <div class="d-flex align-items-center gap-2">
            <button class="cos-btn cos-btn-secondary" id="btn-export-dossier">
              <i class="bi bi-printer"></i> Print / Export PDF
            </button>
            ${selectedHo.status === 'approved' ? `
              <button class="cos-btn cos-btn-primary" id="btn-share-approved">
                <i class="bi bi-share me-1"></i> Share Approved Dossier
              </button>
            ` : `
              <button class="cos-btn cos-btn-primary" id="btn-approve-handover">
                <i class="bi bi-check-circle me-1"></i> Approve Handover
              </button>
            `}
          </div>
        </div>

        <!-- ── Lifecycle Tabs ────────────────────────────────────────── -->
        <div class="d-flex align-items-center gap-2 mb-3 border-bottom pb-2">
          <button class="cos-btn ${activeTab === 'active' ? 'cos-btn-primary' : 'cos-btn-ghost'} btn-sm tab-btn" data-tab="active">
            Active Transitions (${handovers.filter(h => h.status === 'in-progress' || h.status === 'awaiting-review').length})
          </button>
          <button class="cos-btn ${activeTab === 'review' ? 'cos-btn-primary' : 'cos-btn-ghost'} btn-sm tab-btn" data-tab="review">
            Awaiting Review (${handovers.filter(h => h.status === 'awaiting-review').length})
          </button>
          <button class="cos-btn ${activeTab === 'approved' ? 'cos-btn-primary' : 'cos-btn-ghost'} btn-sm tab-btn" data-tab="approved">
            Approved & Finalized (${handovers.filter(h => h.status === 'approved').length})
          </button>
        </div>

        <!-- ── Handover Overview Grid ────────────────────────────────── -->
        <div class="row g-4 mb-4">
          <!-- Left: Dossier List -->
          <div class="col-12 col-lg-4">
            <div class="cos-card">
              <div class="cos-card-header">
                <div class="cos-card-title"><i class="bi bi-folder2-open text-primary me-2"></i>Transition Dossiers</div>
              </div>
              <div class="list-group list-group-flush" id="dossier-list">
                ${displayList.map(h => `
                  <button class="list-group-item list-group-item-action p-3 dossier-select-btn ${h.id === selectedHandoverId ? 'active' : ''}" data-id="${h.id}">
                    <div class="d-flex align-items-center justify-content-between mb-1">
                      <span class="badge ${h.status === 'approved' ? 'bg-success' : 'bg-warning text-dark'} text-uppercase" style="font-size: 9px;">
                        ${h.status}
                      </span>
                      <span style="font-size: 11px; opacity: 0.8;">${h.completionPercent || 45}% complete</span>
                    </div>
                    <div class="fw-bold" style="font-size: 12px;">${h.title}</div>
                    <div style="font-size: 11px; opacity: 0.8; margin-top: 2px;">Component: ${h.component}</div>
                  </button>
                `).join('')}
              </div>
            </div>
          </div>

          <!-- Right: Full Handover Document Viewer -->
          <div class="col-12 col-lg-8">
            <div class="cos-card p-4 bg-white">
              <!-- Top Metadata Strip -->
              <div class="d-flex align-items-center justify-content-between border-bottom pb-3 mb-4 flex-wrap gap-2">
                <div>
                  <div class="d-flex align-items-center gap-2">
                    <span class="badge bg-light text-dark border" style="font-size: 11px;">DOSSIER REF: ${selectedHo.id.toUpperCase()}</span>
                    <span class="badge ${selectedHo.status === 'approved' ? 'bg-success' : 'bg-warning text-dark'}" style="font-size: 11px;">
                      ${selectedHo.status === 'approved' ? 'APPROVED BY MANAGEMENT' : 'TRANSITION IN-FLIGHT'}
                    </span>
                  </div>
                  <h2 class="fw-bold fs-5 text-dark mt-2 mb-0">${selectedHo.title}</h2>
                </div>
                <div class="text-end">
                  <div style="font-size: 11px; color: var(--text-muted);">TARGET EFFECTIVE DATE</div>
                  <div class="fw-bold text-danger fs-6">${selectedHo.dueDate || 'Nov 15, 2026'}</div>
                </div>
              </div>

              <!-- Personnel Bridge Banner -->
              <div class="row g-3 mb-4">
                <div class="col-md-6">
                  <div class="p-3 rounded border bg-light">
                    <div style="font-size: 10px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">DEPARTING SPECIALIST</div>
                    <div class="fw-bold fs-6 text-dark mt-1">${departing.name}</div>
                    <div style="font-size: 11px; color: var(--text-secondary);">${departing.role}</div>
                  </div>
                </div>
                <div class="col-md-6">
                  <div class="p-3 rounded border bg-light">
                    <div style="font-size: 10px; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">INCOMING SUCCESSOR</div>
                    <div class="fw-bold fs-6 text-dark mt-1">${incoming.name}</div>
                    <div style="font-size: 11px; color: var(--text-secondary);">${incoming.role}</div>
                  </div>
                </div>
              </div>

              <!-- Proposed Handover Sections -->
              <div class="mb-4">
                <div class="fw-bold fs-6 text-dark mb-3">Structured Handover Manifest</div>

                <!-- Section: Architecture & Decisions -->
                <div class="p-3 rounded border mb-3 bg-light">
                  <div class="d-flex align-items-center gap-2 mb-2">
                    <i class="bi bi-diagram-3-fill text-primary"></i>
                    <span class="fw-bold" style="font-size: 13px;">1. Architecture & Core Decisions</span>
                  </div>
                  <p style="font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;">
                    Kafka selected over RabbitMQ (ADR-007) for 50k events/min partitioned throughput. pgBouncer connection pool configured with 80 maximum connections in transaction mode.
                  </p>
                  <div class="d-flex gap-2">
                    <span class="badge bg-light text-primary border" style="font-size: 10px;">ADR-007</span>
                    <span class="badge bg-light text-primary border" style="font-size: 10px;">DEC-003</span>
                  </div>
                </div>

                <!-- Section: Operational Runbooks & Known Gaps -->
                <div class="p-3 rounded border mb-3 bg-light">
                  <div class="d-flex align-items-center gap-2 mb-2">
                    <i class="bi bi-hdd-network-fill text-warning"></i>
                    <span class="fw-bold" style="font-size: 13px;">2. Operational Runbooks & Identified Gaps</span>
                  </div>
                  <ul class="ps-3 m-0 text-secondary" style="font-size: 12px;">
                    <li><strong>Pipeline OOM Recovery (Bug #001):</strong> Celery worker requires batch splitting via admin endpoint. Permanent chunking fix scheduled for Sprint 24.</li>
                    <li><strong class="text-danger">Unresolved Documentation Gap:</strong> Auth Service JWT secret key rotation scripts not yet checked into repository.</li>
                  </ul>
                </div>

                <!-- Section: Key Contacts & Escalations -->
                <div class="p-3 rounded border mb-3 bg-light">
                  <div class="d-flex align-items-center gap-2 mb-2">
                    <i class="bi bi-person-lines-fill text-success"></i>
                    <span class="fw-bold" style="font-size: 13px;">3. Primary Escalation Contacts</span>
                  </div>
                  <div style="font-size: 12px; color: var(--text-secondary);">
                    Infrastructure & Kubernetes: <strong>Jordan Kim</strong> (#devops-alerts)<br>
                    Product & Client SLAs: <strong>Maya Patel</strong> (#proj-atlas-pm)
                  </div>
                </div>
              </div>

              <!-- Stakeholder Signoff Status -->
              <div class="p-3 rounded border bg-light mb-4">
                <div class="fw-bold mb-2" style="font-size: 12px; color: var(--text-secondary); text-transform: uppercase;">Review & Sign-Off Status</div>
                <div class="d-flex align-items-center justify-content-between flex-wrap gap-2">
                  <div class="d-flex align-items-center gap-2">
                    <span class="badge bg-success-subtle text-success"><i class="bi bi-check-circle me-1"></i>Engineering Lead Review</span>
                    <span class="text-muted" style="font-size: 11px;">Signed off by Maya Patel</span>
                  </div>
                  <div class="d-flex align-items-center gap-2">
                    ${selectedHo.status === 'approved' 
                      ? '<span class="badge bg-success-subtle text-success"><i class="bi bi-check-circle me-1"></i>Final Handover Approved</span>'
                      : '<span class="badge bg-warning-subtle text-warning"><i class="bi bi-hourglass-split me-1"></i>Pending Final Approval</span>'
                    }
                  </div>
                </div>
              </div>

              <!-- Actions Strip -->
              <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 pt-3 border-top">
                <button class="cos-btn cos-btn-secondary" id="btn-add-review-comment">
                  <i class="bi bi-chat-left-text me-1"></i> Add Review Comment
                </button>
                <div class="d-flex align-items-center gap-2">
                  <button class="cos-btn cos-btn-ghost text-danger" id="btn-request-changes">
                    Request Changes
                  </button>
                  ${selectedHo.status !== 'approved' ? `
                    <button class="cos-btn cos-btn-primary" id="btn-approve-action">
                      <i class="bi bi-check-lg me-1"></i> Approve Handover Dossier
                    </button>
                  ` : `
                    <span class="badge bg-success text-white px-3 py-2" style="font-size: 12px;">
                      <i class="bi bi-shield-check me-1"></i> Dossier Certified
                    </span>
                  `}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    // ── Attach Event Listeners ─────────────────────────────────────
    container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        activeTab = btn.getAttribute('data-tab');
        render();
      });
    });

    container.querySelectorAll('.dossier-select-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        selectedHandoverId = btn.getAttribute('data-id');
        render();
      });
    });

    const btnApprove = container.querySelector('#btn-approve-action') || container.querySelector('#btn-approve-handover');
    if (btnApprove) {
      btnApprove.addEventListener('click', async () => {
        await updateHandover(selectedHo.id, { status: 'approved', completionPercent: 100 });
        handovers = await getHandovers();
        alert('Handover dossier successfully approved! Successor now has certified transition clearance.');
        render();
      });
    }

    const btnExport = container.querySelector('#btn-export-dossier');
    if (btnExport) {
      btnExport.addEventListener('click', () => {
        window.print();
      });
    }

    const btnShare = container.querySelector('#btn-share-approved');
    if (btnShare) {
      btnShare.addEventListener('click', () => {
        alert('Official approved handover packet shared securely with incoming member (Sam Chen).');
      });
    }

    const btnComment = container.querySelector('#btn-add-review-comment');
    if (btnComment) {
      btnComment.addEventListener('click', () => {
        const comment = prompt('Enter review feedback or approval stipulation:');
        if (comment) {
          alert('Review comment recorded in audit ledger.');
        }
      });
    }

    const btnReqChanges = container.querySelector('#btn-request-changes');
    if (btnReqChanges) {
      btnReqChanges.addEventListener('click', () => {
        const notes = prompt('Specify sections requiring additional documentation:');
        if (notes) {
          alert('Change request dispatched to departing engineer.');
        }
      });
    }
  }

  render();
}
