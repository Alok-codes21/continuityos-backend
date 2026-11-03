/**
 * ContinuityOS — Knowledge Uncertainty Ledger Page
 * Priority module: Truth and confidence ledger across all 6 knowledge states.
 */

import {
  getKnowledgeRecords,
  getComponents,
  getDocuments,
  approveKnowledgeRecord,
  rejectKnowledgeRecord,
  updateKnowledgeRecord,
  createKnowledgeRecord,
} from '../../services/mock-api.js';

export default async function renderPage(container) {
  // Read query params if any
  const urlParams = new URLSearchParams(window.location.hash.split('?')[1] || '');
  let activeClassification = urlParams.get('classification') || 'all';
  let searchQuery = '';
  let selectedComponent = 'all';
  let selectedRecord = null;
  let showConflictModal = false;
  let conflictingRecord = null;

  // Load initial data
  const [allRecords, components, documents] = await Promise.all([
    getKnowledgeRecords(),
    getComponents(),
    getDocuments(),
  ]);

  // Render the page shell
  function render() {
    // Classification counters
    const counts = {
      all: allRecords.length,
      verified: allRecords.filter(r => r.classification === 'verified').length,
      'evidence-backed': allRecords.filter(r => r.classification === 'evidence-backed').length,
      inferred: allRecords.filter(r => r.classification === 'inferred').length,
      conflicting: allRecords.filter(r => r.classification === 'conflicting').length,
      missing: allRecords.filter(r => r.classification === 'missing').length,
      outdated: allRecords.filter(r => r.classification === 'outdated').length,
    };

    // Filter records
    let filtered = allRecords.filter(r => {
      if (activeClassification !== 'all' && r.classification !== activeClassification) return false;
      if (selectedComponent !== 'all' && r.component !== selectedComponent) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchesClaim = (r.claim || '').toLowerCase().includes(q);
        const matchesSource = (r.sourceLabel || '').toLowerCase().includes(q);
        const matchesTags = (r.tags || []).some(t => t.toLowerCase().includes(q));
        if (!matchesClaim && !matchesSource && !matchesTags) return false;
      }
      return true;
    });

    container.innerHTML = `
      <div class="uncertainty-ledger-page">
        <!-- ── Header ──────────────────────────────────────────────── -->
        <div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
          <div>
            <div class="d-flex align-items-center gap-2">
              <h1 class="page-title m-0" style="font-size: 20px; font-weight: 800;">Knowledge Uncertainty Ledger</h1>
              <span class="badge bg-light text-dark border px-2 py-1" style="font-size: 11px;">
                <i class="bi bi-shield-lock me-1 text-primary"></i>Permission-Aware Auditing
              </span>
            </div>
            <p class="page-subtitle m-0 mt-1" style="font-size: 13px; color: var(--text-secondary);">
              ContinuityOS distinguishes human-verified facts from AI inferences, source conflicts, and undocumented gaps.
            </p>
          </div>
          <div class="d-flex align-items-center gap-2">
            <button class="cos-btn cos-btn-secondary" id="btn-export-ledger">
              <i class="bi bi-download"></i> Export Ledger CSV
            </button>
            <button class="cos-btn cos-btn-primary" id="btn-add-claim">
              <i class="bi bi-plus-lg"></i> Propose Knowledge Claim
            </button>
          </div>
        </div>

        <!-- ── Classification Tabs / Summary Bar ─────────────────────── -->
        <div class="cos-card mb-4">
          <div class="p-2 d-flex align-items-center gap-1 overflow-auto flex-nowrap" id="classification-tabs" style="border-bottom: 1px solid var(--border-light);">
            <button class="filter-tab-btn ${activeClassification === 'all' ? 'active' : ''}" data-val="all">
              All Knowledge Records <span class="tab-badge">${counts.all}</span>
            </button>
            <button class="filter-tab-btn ${activeClassification === 'verified' ? 'active' : ''}" data-val="verified">
              <i class="bi bi-check-circle-fill text-teal me-1"></i> Verified <span class="tab-badge bg-teal-subtle text-teal">${counts.verified}</span>
            </button>
            <button class="filter-tab-btn ${activeClassification === 'evidence-backed' ? 'active' : ''}" data-val="evidence-backed">
              <i class="bi bi-link-45deg text-secondary me-1"></i> Evidence-Backed <span class="tab-badge bg-primary-subtle text-primary">${counts['evidence-backed']}</span>
            </button>
            <button class="filter-tab-btn ${activeClassification === 'inferred' ? 'active' : ''}" data-val="inferred">
              <i class="bi bi-lightning-charge text-warning me-1"></i> Inferred (Review Needed) <span class="tab-badge bg-warning-subtle text-warning">${counts.inferred}</span>
            </button>
            <button class="filter-tab-btn ${activeClassification === 'conflicting' ? 'active' : ''}" data-val="conflicting">
              <i class="bi bi-exclamation-triangle text-danger me-1"></i> Conflicting Sources <span class="tab-badge bg-danger-subtle text-danger">${counts.conflicting}</span>
            </button>
            <button class="filter-tab-btn ${activeClassification === 'missing' ? 'active' : ''}" data-val="missing">
              <i class="bi bi-question-diamond text-purple me-1"></i> Missing / Gaps <span class="tab-badge bg-purple-subtle text-purple">${counts.missing}</span>
            </button>
            <button class="filter-tab-btn ${activeClassification === 'outdated' ? 'active' : ''}" data-val="outdated">
              <i class="bi bi-clock-history text-muted me-1"></i> Outdated <span class="tab-badge bg-secondary-subtle text-secondary">${counts.outdated}</span>
            </button>
          </div>

          <!-- Filter / Search Controls -->
          <div class="p-3 d-flex align-items-center justify-content-between flex-wrap gap-2 bg-light">
            <div class="d-flex align-items-center gap-2 flex-grow-1" style="max-width: 480px;">
              <div class="input-group input-group-sm">
                <span class="input-group-text bg-white border-end-0"><i class="bi bi-search text-muted"></i></span>
                <input type="text" class="form-control border-start-0 ps-0" id="ledger-search-input" placeholder="Search claims, evidence citations, tags…" value="${searchQuery}">
              </div>
            </div>
            <div class="d-flex align-items-center gap-2">
              <label style="font-size: 11px; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;">Component:</label>
              <select class="form-select form-select-sm" id="ledger-component-filter" style="width: 180px;">
                <option value="all">All Components</option>
                ${components.map(c => `<option value="${c.id}" ${selectedComponent === c.id ? 'selected' : ''}>${c.name}</option>`).join('')}
              </select>
            </div>
          </div>
        </div>

        <!-- ── Main Table Card ──────────────────────────────────────── -->
        <div class="cos-card mb-4">
          <div class="table-responsive">
            <table class="table cos-table mb-0 align-middle">
              <thead>
                <tr>
                  <th style="width: 32%;">Knowledge Claim & Scope</th>
                  <th style="width: 16%;">Classification</th>
                  <th style="width: 14%;">Confidence</th>
                  <th style="width: 18%;">Evidence / Source</th>
                  <th style="width: 12%;">Last Verified</th>
                  <th style="width: 8%; text-align: right;">Action</th>
                </tr>
              </thead>
              <tbody>
                ${filtered.length === 0 ? `
                  <tr>
                    <td colspan="6" class="text-center py-5">
                      <div class="empty-state">
                        <i class="bi bi-journal-x fs-1 text-muted mb-2"></i>
                        <div class="fw-bold">No records match your filter criteria</div>
                        <p class="text-muted" style="font-size: 12px;">Try adjusting your classification tab or clearing the search query.</p>
                      </div>
                    </td>
                  </tr>
                ` : filtered.map(r => `
                  <tr class="ledger-row ${selectedRecord && selectedRecord.id === r.id ? 'table-active' : ''}" data-id="${r.id}" style="cursor: pointer;">
                    <td>
                      <div class="fw-bold text-dark" style="font-size: 12px; line-height: 1.4;">
                        ${highlightQuery(r.claim, searchQuery)}
                      </div>
                      <div class="d-flex align-items-center gap-2 mt-1">
                        <span class="badge bg-light text-secondary border" style="font-size: 10px;">
                          <i class="bi bi-box me-1"></i>${r.component || 'general'}
                        </span>
                        ${(r.tags || []).slice(0, 2).map(t => `<span class="badge bg-light text-muted border" style="font-size: 9px;">#${t}</span>`).join('')}
                      </div>
                    </td>
                    <td>
                      ${renderClassificationBadge(r.classification)}
                    </td>
                    <td>
                      <div class="d-flex align-items-center gap-2">
                        <div class="progress flex-grow-1" style="height: 6px; background: #e5e7eb; min-width: 60px;">
                          <div class="progress-bar ${getConfidenceColor(r.confidence)}" role="progressbar" style="width: ${r.confidence}%;" aria-valuenow="${r.confidence}" aria-valuemin="0" aria-valuemax="100"></div>
                        </div>
                        <span style="font-size: 11px; font-weight: 700; width: 32px; text-align: right;">${r.confidence}%</span>
                      </div>
                    </td>
                    <td>
                      <div class="d-flex align-items-center gap-1" style="font-size: 11px;">
                        <i class="bi bi-file-earmark-text text-primary"></i>
                        <span class="text-truncate" style="max-width: 150px;" title="${r.sourceLabel || r.source || 'Direct observation'}">
                          ${r.sourceLabel || r.source || 'Direct observation'}
                        </span>
                      </div>
                      ${r.classification === 'conflicting' ? `
                        <button class="cos-btn cos-btn-danger btn-xs mt-1 btn-compare-conflict" data-id="${r.id}" style="font-size: 10px; padding: 2px 6px;">
                          <i class="bi bi-arrow-left-right me-1"></i>Compare Conflict
                        </button>
                      ` : ''}
                    </td>
                    <td>
                      <div style="font-size: 11px; color: var(--text-secondary);">
                        ${r.lastVerified ? r.lastVerified : '<span class="text-muted">Unverified</span>'}
                      </div>
                      <div style="font-size: 10px; color: var(--text-muted);">
                        ${r.verifiedBy ? `by ${r.verifiedBy}` : 'Awaiting review'}
                      </div>
                    </td>
                    <td style="text-align: right;">
                      <button class="cos-btn cos-btn-ghost btn-sm btn-inspect-row" data-id="${r.id}" title="Inspect Claim Details">
                        <i class="bi bi-chevron-right"></i>
                      </button>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
          <div class="cos-card-footer d-flex align-items-center justify-content-between">
            <span style="font-size: 11px; color: var(--text-muted);">
              Showing <strong>${filtered.length}</strong> of <strong>${allRecords.length}</strong> institutional knowledge claims
            </span>
            <span style="font-size: 11px; color: var(--text-secondary);">
              <i class="bi bi-info-circle me-1"></i>Claims marked "Inferred" or "Conflicting" cannot be exported to external handovers until authorized.
            </span>
          </div>
        </div>

        <!-- ── Detail Drawer Modal Overlay ───────────────────────────── -->
        ${selectedRecord ? `
          <div class="cos-drawer-backdrop" id="drawer-backdrop"></div>
          <div class="cos-drawer" id="record-drawer">
            <div class="cos-drawer-header d-flex align-items-center justify-content-between p-3 border-bottom bg-light">
              <div>
                <span style="font-size: 10px; text-transform: uppercase; font-weight: 700; color: var(--text-muted); letter-spacing: 0.05em;">KNOWLEDGE CLAIM DETAILS</span>
                <div class="fw-bold fs-6 text-dark">${selectedRecord.id.toUpperCase()}</div>
              </div>
              <button class="btn-close" id="btn-close-drawer" aria-label="Close"></button>
            </div>
            <div class="cos-drawer-body p-4" style="overflow-y: auto; max-height: calc(100vh - 140px);">
              <!-- Classification and Confidence -->
              <div class="d-flex align-items-center justify-content-between mb-3 pb-3 border-bottom">
                <div>
                  <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">CURRENT STATUS</div>
                  ${renderClassificationBadge(selectedRecord.classification)}
                </div>
                <div class="text-end">
                  <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">CONFIDENCE SCORE</div>
                  <span class="badge ${getConfidenceBadgeClass(selectedRecord.confidence)} fs-6">
                    ${selectedRecord.confidence}%
                  </span>
                </div>
              </div>

              <!-- Full Claim Text -->
              <div class="mb-4">
                <label style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Institutional Claim</label>
                <div class="p-3 rounded border bg-light mt-1" style="font-size: 13px; line-height: 1.5; color: var(--text-primary); font-weight: 500;">
                  ${selectedRecord.claim}
                </div>
              </div>

              <!-- Special Conflict Notice if conflicting -->
              ${selectedRecord.classification === 'conflicting' ? `
                <div class="alert alert-danger p-3 mb-4" style="font-size: 12px;">
                  <div class="fw-bold mb-1"><i class="bi bi-exclamation-triangle-fill me-1"></i>Contradiction Flagged</div>
                  ${selectedRecord.conflictNote || 'Two or more enterprise records report conflicting statements for this claim. Resolution required before handover.'}
                  <div class="mt-2">
                    <button class="cos-btn cos-btn-danger btn-sm" id="drawer-btn-open-conflict">
                      <i class="bi bi-layout-split me-1"></i>Open Split-Screen Comparison
                    </button>
                  </div>
                </div>
              ` : ''}

              <!-- Inference Notice if inferred -->
              ${selectedRecord.classification === 'inferred' ? `
                <div class="alert alert-warning p-3 mb-4" style="font-size: 12px;">
                  <div class="fw-bold mb-1"><i class="bi bi-lightning-charge me-1"></i>AI Inference Notice</div>
                  ${selectedRecord.inferenceNote || 'This record was derived algorithmically from conversational transcripts and git commits. It has NOT yet been approved by an authorized engineering lead.'}
                </div>
              ` : ''}

              <!-- Evidence Citations -->
              <div class="mb-4">
                <label style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Grounded Evidence Citations</label>
                <div class="list-group list-group-flush border rounded mt-1">
                  <div class="list-group-item p-3">
                    <div class="d-flex align-items-center justify-content-between mb-1">
                      <div class="d-flex align-items-center gap-2">
                        <i class="bi bi-file-earmark-check text-primary"></i>
                        <span class="fw-bold" style="font-size: 12px;">${selectedRecord.sourceLabel || 'Primary Document Reference'}</span>
                      </div>
                      <span class="badge bg-light text-secondary border" style="font-size: 9px;">VERIFIED DOC</span>
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted);">
                      Identifier: <code>${selectedRecord.source || 'doc-001'}</code> · Chunk #3
                    </div>
                  </div>
                </div>
              </div>

              <!-- Metadata fields -->
              <div class="row g-2 mb-4" style="font-size: 12px;">
                <div class="col-6">
                  <span class="text-muted d-block">Component:</span>
                  <strong>${selectedRecord.component || 'platform'}</strong>
                </div>
                <div class="col-6">
                  <span class="text-muted d-block">Last Verified Date:</span>
                  <strong>${selectedRecord.lastVerified || 'Never'}</strong>
                </div>
                <div class="col-6 mt-2">
                  <span class="text-muted d-block">Verified By:</span>
                  <strong>${selectedRecord.verifiedBy || 'None'}</strong>
                </div>
                <div class="col-6 mt-2">
                  <span class="text-muted d-block">Tags:</span>
                  <span>${(selectedRecord.tags || []).join(', ') || 'none'}</span>
                </div>
              </div>

              <!-- Actions Area -->
              <div class="p-3 rounded border bg-light">
                <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 8px;">
                  Human Review & Audit Actions
                </div>
                <div class="d-grid gap-2">
                  <button class="cos-btn cos-btn-primary" id="btn-approve-claim">
                    <i class="bi bi-check2-circle me-1"></i> Approve & Verify Claim
                  </button>
                  <button class="cos-btn cos-btn-danger" id="btn-dispute-claim">
                    <i class="bi bi-flag me-1"></i> Flag as Conflicting / Disputed
                  </button>
                  <button class="cos-btn cos-btn-secondary" id="btn-edit-claim">
                    <i class="bi bi-pencil me-1"></i> Edit Claim Text
                  </button>
                </div>
              </div>
            </div>
          </div>
        ` : ''}

        <!-- ── Conflict Comparison Modal ────────────────────────────── -->
        ${showConflictModal && conflictingRecord ? `
          <div class="cos-modal-overlay">
            <div class="cos-modal" style="max-width: 800px; width: 95%;">
              <div class="cos-modal-header d-flex justify-content-between align-items-center">
                <div class="d-flex align-items-center gap-2">
                  <span class="badge bg-danger-subtle text-danger"><i class="bi bi-exclamation-triangle me-1"></i>CONTRADICTION AUDITOR</span>
                  <div class="cos-modal-title m-0">Cross-Source Conflict Comparison</div>
                </div>
                <button class="btn-close" id="btn-close-conflict-modal"></button>
              </div>
              <div class="cos-modal-body p-4">
                <div class="alert alert-warning mb-3" style="font-size: 12px;">
                  Two contradictory evidence sources have been identified for this item. Review both sources below and select the authoritative record to resolve.
                </div>

                <div class="row g-3 mb-4">
                  <!-- Source A -->
                  <div class="col-md-6">
                    <div class="p-3 border rounded h-100 bg-white" style="border-top: 3px solid #ef4444 !important;">
                      <div class="d-flex align-items-center justify-content-between mb-2">
                        <span class="badge bg-light text-danger border fw-bold" style="font-size: 10px;">SOURCE A (Confluence)</span>
                        <span class="text-muted" style="font-size: 11px;">Nov 10, 2025</span>
                      </div>
                      <div class="fw-bold text-dark mb-1" style="font-size: 13px;">Incident Report — Nov 2025 Outage</div>
                      <p style="font-size: 12px; color: var(--text-secondary); background: #fef2f2; padding: 10px; border-radius: 6px;">
                        "Root cause determined to be <strong>Kafka broker topic partition misconfiguration</strong> during horizontal autoscaling event. Message retention window saturated broker storage."
                      </p>
                      <div class="text-muted" style="font-size: 11px;">Author: Jordan Kim (DevOps)</div>
                      <button class="cos-btn cos-btn-secondary btn-sm w-100 mt-3" id="btn-select-source-a">
                        Select Source A as Authoritative
                      </button>
                    </div>
                  </div>

                  <!-- Source B -->
                  <div class="col-md-6">
                    <div class="p-3 border rounded h-100 bg-white" style="border-top: 3px solid #3b82f6 !important;">
                      <div class="d-flex align-items-center justify-content-between mb-2">
                        <span class="badge bg-light text-primary border fw-bold" style="font-size: 10px;">SOURCE B (Slack Engineering)</span>
                        <span class="text-muted" style="font-size: 11px;">Nov 12, 2025</span>
                      </div>
                      <div class="fw-bold text-dark mb-1" style="font-size: 13px;">#infra-alerts Channel Thread</div>
                      <p style="font-size: 12px; color: var(--text-secondary); background: #eff6ff; padding: 10px; border-radius: 6px;">
                        "Actually, broker logs showed Kafka was fine. The bottleneck was <strong>PostgreSQL read replica replication lag</strong> that caused consumer workers to block on write transactions."
                      </p>
                      <div class="text-muted" style="font-size: 11px;">Author: Alex Rivera (Senior Backend Lead)</div>
                      <button class="cos-btn cos-btn-primary btn-sm w-100 mt-3" id="btn-select-source-b">
                        Select Source B as Authoritative
                      </button>
                    </div>
                  </div>
                </div>

                <div class="p-3 bg-light rounded border">
                  <label class="form-label fw-bold" style="font-size: 12px;">Resolution Commentary (Audit Log):</label>
                  <textarea class="form-control form-control-sm" id="conflict-resolution-notes" rows="2" placeholder="Explain the rationale for resolving this conflict..."></textarea>
                </div>
              </div>
              <div class="cos-modal-footer d-flex justify-content-between">
                <button class="cos-btn cos-btn-ghost" id="btn-dismiss-conflict">Close without Resolving</button>
                <button class="cos-btn cos-btn-primary" id="btn-confirm-resolve">Mark Conflict Resolved</button>
              </div>
            </div>
          </div>
        ` : ''}
      </div>
    `;

    // ── Attach Event Listeners ─────────────────────────────────────

    // Tabs
    container.querySelectorAll('.filter-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        activeClassification = btn.getAttribute('data-val');
        render();
      });
    });

    // Search
    const searchInput = container.querySelector('#ledger-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value;
        render();
      });
    }

    // Component filter
    const compFilter = container.querySelector('#ledger-component-filter');
    if (compFilter) {
      compFilter.addEventListener('change', (e) => {
        selectedComponent = e.target.value;
        render();
      });
    }

    // Row click → open drawer
    container.querySelectorAll('.ledger-row').forEach(row => {
      row.addEventListener('click', (e) => {
        if (e.target.closest('.btn-compare-conflict')) return;
        const id = row.getAttribute('data-id');
        selectedRecord = allRecords.find(r => r.id === id) || null;
        render();
      });
    });

    // Close drawer
    const btnCloseDrawer = container.querySelector('#btn-close-drawer');
    const drawerBackdrop = container.querySelector('#drawer-backdrop');
    if (btnCloseDrawer) btnCloseDrawer.addEventListener('click', () => { selectedRecord = null; render(); });
    if (drawerBackdrop) drawerBackdrop.addEventListener('click', () => { selectedRecord = null; render(); });

    // Drawer actions
    const btnApprove = container.querySelector('#btn-approve-claim');
    if (btnApprove && selectedRecord) {
      btnApprove.addEventListener('click', async () => {
        await approveKnowledgeRecord(selectedRecord.id);
        selectedRecord.classification = 'verified';
        selectedRecord.confidence = 95;
        selectedRecord.lastVerified = new Date().toISOString().split('T')[0];
        selectedRecord.verifiedBy = 'Alex Rivera (User)';
        alert('Claim approved as human-verified institutional knowledge.');
        render();
      });
    }

    const btnDispute = container.querySelector('#btn-dispute-claim');
    if (btnDispute && selectedRecord) {
      btnDispute.addEventListener('click', async () => {
        const reason = prompt('Please specify why this claim is in dispute:', 'Conflicting evidence from git history');
        if (reason) {
          await rejectKnowledgeRecord(selectedRecord.id, reason);
          selectedRecord.classification = 'conflicting';
          selectedRecord.conflictNote = reason;
          render();
        }
      });
    }

    const btnEdit = container.querySelector('#btn-edit-claim');
    if (btnEdit && selectedRecord) {
      btnEdit.addEventListener('click', async () => {
        const newClaim = prompt('Edit institutional claim text:', selectedRecord.claim);
        if (newClaim && newClaim !== selectedRecord.claim) {
          await updateKnowledgeRecord(selectedRecord.id, { claim: newClaim });
          selectedRecord.claim = newClaim;
          render();
        }
      });
    }

    // Conflict comparison buttons
    container.querySelectorAll('.btn-compare-conflict').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const id = btn.getAttribute('data-id');
        conflictingRecord = allRecords.find(r => r.id === id);
        showConflictModal = true;
        render();
      });
    });

    const drawerConflictBtn = container.querySelector('#drawer-btn-open-conflict');
    if (drawerConflictBtn && selectedRecord) {
      drawerConflictBtn.addEventListener('click', () => {
        conflictingRecord = selectedRecord;
        showConflictModal = true;
        render();
      });
    }

    const btnCloseConflict = container.querySelector('#btn-close-conflict-modal');
    const btnDismissConflict = container.querySelector('#btn-dismiss-conflict');
    if (btnCloseConflict) btnCloseConflict.addEventListener('click', () => { showConflictModal = false; render(); });
    if (btnDismissConflict) btnDismissConflict.addEventListener('click', () => { showConflictModal = false; render(); });

    const btnSelectA = container.querySelector('#btn-select-source-a');
    if (btnSelectA && conflictingRecord) {
      btnSelectA.addEventListener('click', async () => {
        await approveKnowledgeRecord(conflictingRecord.id);
        conflictingRecord.classification = 'verified';
        conflictingRecord.claim = 'Root cause of November 2025 outage was Kafka broker partition misconfiguration.';
        showConflictModal = false;
        alert('Resolved conflict: Source A (Incident Report) designated authoritative.');
        render();
      });
    }

    const btnSelectB = container.querySelector('#btn-select-source-b');
    if (btnSelectB && conflictingRecord) {
      btnSelectB.addEventListener('click', async () => {
        await approveKnowledgeRecord(conflictingRecord.id);
        conflictingRecord.classification = 'verified';
        conflictingRecord.claim = 'Root cause of November 2025 outage was PostgreSQL replica replication lag.';
        showConflictModal = false;
        alert('Resolved conflict: Source B (Slack Engineering Lead) designated authoritative.');
        render();
      });
    }

    const btnConfirmResolve = container.querySelector('#btn-confirm-resolve');
    if (btnConfirmResolve && conflictingRecord) {
      btnConfirmResolve.addEventListener('click', async () => {
        const notes = container.querySelector('#conflict-resolution-notes')?.value || 'Audited by engineer';
        await approveKnowledgeRecord(conflictingRecord.id);
        conflictingRecord.classification = 'verified';
        conflictingRecord.conflictNote = null;
        showConflictModal = false;
        alert('Conflict marked as resolved in ledger.');
        render();
      });
    }

    // Add claim button
    const btnAddClaim = container.querySelector('#btn-add-claim');
    if (btnAddClaim) {
      btnAddClaim.addEventListener('click', async () => {
        const text = prompt('Enter knowledge claim statement:');
        if (!text) return;
        const newRecord = await createKnowledgeRecord({
          claim: text,
          component: 'data-pipeline',
          classification: 'inferred',
          confidence: 60,
          sourceLabel: 'Manual Submission',
        });
        allRecords.unshift(newRecord);
        selectedRecord = newRecord;
        render();
      });
    }

    // Export CSV
    const btnExport = container.querySelector('#btn-export-ledger');
    if (btnExport) {
      btnExport.addEventListener('click', () => {
        const csv = [
          ['ID', 'Claim', 'Classification', 'Confidence', 'Component', 'Source', 'LastVerified'].join(','),
          ...filtered.map(r => [
            `"${r.id}"`,
            `"${(r.claim || '').replace(/"/g, '""')}"`,
            `"${r.classification}"`,
            r.confidence,
            `"${r.component || ''}"`,
            `"${r.sourceLabel || ''}"`,
            `"${r.lastVerified || ''}"`
          ].join(','))
        ].join('\n');

        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `continuityos_ledger_${Date.now()}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      });
    }
  }

  // Helpers
  function renderClassificationBadge(cls) {
    switch (cls) {
      case 'verified':
        return `<span class="badge-verified"><i class="bi bi-check-circle-fill me-1"></i>Verified</span>`;
      case 'evidence-backed':
        return `<span class="badge-evidence-backed"><i class="bi bi-link-45deg me-1"></i>Evidence-Backed</span>`;
      case 'inferred':
        return `<span class="badge-inferred"><i class="bi bi-lightning-charge me-1"></i>Inferred</span>`;
      case 'conflicting':
        return `<span class="badge-conflicting"><i class="bi bi-exclamation-triangle me-1"></i>Conflicting</span>`;
      case 'missing':
        return `<span class="badge-missing"><i class="bi bi-question-diamond me-1"></i>Missing</span>`;
      case 'outdated':
        return `<span class="badge-outdated"><i class="bi bi-clock-history me-1"></i>Outdated</span>`;
      default:
        return `<span class="badge bg-light text-dark border">${cls}</span>`;
    }
  }

  function getConfidenceColor(conf) {
    if (conf >= 80) return 'bg-success';
    if (conf >= 50) return 'bg-warning';
    return 'bg-danger';
  }

  function getConfidenceBadgeClass(conf) {
    if (conf >= 80) return 'bg-success';
    if (conf >= 50) return 'bg-warning text-dark';
    return 'bg-danger';
  }

  function highlightQuery(text, q) {
    if (!q || !text) return text;
    const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return text.replace(new RegExp(`(${escaped})`, 'gi'), '<mark style="background: #fef08a; padding: 0 2px;">$1</mark>');
  }

  render();
}
