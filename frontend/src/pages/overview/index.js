/**
 * ContinuityOS — Overview Dashboard Page
 * High-fidelity executive continuity intelligence dashboard.
 */

import {
  getProject,
  getTeamMembers,
  getMetrics,
  getRisks,
  getDecisions,
  getSources,
  getHandovers,
} from '../../services/mock-api.js';
import { navigate } from '../../router.js';

export default async function renderPage(container) {
  // 1. Fetch data
  const [project, teamMembers, metrics, risks, decisions, sources, handovers] = await Promise.all([
    getProject(),
    getTeamMembers(),
    getMetrics(),
    getRisks(),
    getDecisions(),
    getSources(),
    getHandovers(),
  ]);

  const departingMember = teamMembers.find(m => m.status === 'departing') || teamMembers[0];
  const activeHandovers = handovers.filter(h => h.status === 'in-progress' || h.status === 'awaiting-review');

  // Health ring calculation
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const healthOffset = circumference - (metrics.healthScore / 100) * circumference;
  const reconOffset = circumference - (metrics.reconstructionScore / 100) * circumference;

  // 2. Render HTML
  container.innerHTML = `
    <div class="overview-page">
      <!-- ── Demo Banner & Context Strip ───────────────────────────── -->
      <div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
        <div class="d-flex align-items-center gap-2">
          <span class="badge bg-dark text-white px-2 py-1" style="font-size: 11px; font-weight: 600; letter-spacing: 0.03em;">
            <i class="bi bi-shield-check text-warning me-1"></i>DEMO WORKSPACE
          </span>
          <span class="text-secondary" style="font-size: 13px;">
            <strong>${project.organisation || 'NovaTech Engineering'}</strong> · ${project.name || 'Project Atlas'}
          </span>
          <span class="badge bg-light text-dark border px-2 py-1" style="font-size: 11px;">
            <i class="bi bi-calendar-event me-1 text-primary"></i>${project.sprint || 'Sprint 23'} (${project.sprintDates || 'Oct 28 – Nov 11, 2026'})
          </span>
        </div>
        <div class="d-flex align-items-center gap-2">
          <button class="cos-btn cos-btn-secondary" id="btn-export-overview" title="Export Executive Summary">
            <i class="bi bi-download"></i> Export Report
          </button>
          <button class="cos-btn cos-btn-primary" id="btn-connect-source-quick">
            <i class="bi bi-plus-lg"></i> Connect Source
          </button>
        </div>
      </div>

      <!-- ── Executive Welcome Banner ──────────────────────────────── -->
      <div class="overview-banner mb-4">
        <div class="overview-banner-content">
          <div class="d-flex align-items-center gap-2 mb-2">
            <span class="badge" style="background: rgba(255,255,255,0.2); color: #fff; font-size: 11px;">KNOWLEDGE CONTINUITY RADAR</span>
            <span style="color: rgba(255,255,255,0.8); font-size: 12px;">Automated Reconstruction Engine v2.4</span>
          </div>
          <h2 class="overview-banner-title">
            Project Atlas Knowledge Reconstruction: <span style="color: #a78bfa;">${metrics.reconstructionScore}%</span>
          </h2>
          <p class="overview-banner-desc">
            ${metrics.verifiedClaims} claims verified by team leads. ${metrics.conflicting} source contradictions flagged. 
            <strong>${departingMember ? departingMember.name : 'Alex Rivera'}</strong>'s departure in 11 days poses critical concentration risk across 3 core microservices.
          </p>
          <div class="overview-banner-actions mt-3">
            <button class="cos-btn" style="background: #ffffff; color: var(--primary); font-weight: 600; border: none;" id="banner-btn-simulator">
              <i class="bi bi-person-dash text-danger"></i> Simulate Departure Impact
            </button>
            <button class="cos-btn" style="background: rgba(255,255,255,0.15); color: #ffffff; border: 1px solid rgba(255,255,255,0.25);" id="banner-btn-ledger">
              <i class="bi bi-journal-check"></i> Review Uncertainty Ledger (${metrics.inferred + metrics.conflicting} Pending)
            </button>
            <button class="cos-btn" style="background: rgba(255,255,255,0.15); color: #ffffff; border: 1px solid rgba(255,255,255,0.25);" id="banner-btn-interview">
              <i class="bi bi-chat-square-dots"></i> Conduct AI Handover Interview
            </button>
          </div>
        </div>
        <div class="overview-banner-score-card">
          <div class="score-circle-container">
            <svg class="score-ring" width="104" height="104" viewBox="0 0 104 104">
              <circle class="score-ring-bg" cx="52" cy="52" r="${radius}" stroke-width="8" />
              <circle class="score-ring-fill" cx="52" cy="52" r="${radius}" stroke-width="8"
                stroke-dasharray="${circumference}"
                stroke-dashoffset="${healthOffset}"
                style="stroke: #34d399;" />
            </svg>
            <div class="score-value-box">
              <span class="score-num" style="color: #ffffff;">${metrics.healthScore}%</span>
              <span class="score-lbl" style="color: rgba(255,255,255,0.7); font-size: 10px;">HEALTH</span>
            </div>
          </div>
          <div class="text-center mt-2">
            <div style="font-size: 12px; font-weight: 700; color: #fff;">Continuity Index</div>
            <div style="font-size: 11px; color: rgba(255,255,255,0.75);">Moderate Resilience</div>
          </div>
        </div>
      </div>

      <!-- ── 6-State Knowledge Classification Strip ─────────────────── -->
      <div class="mb-4">
        <div class="d-flex align-items-center justify-content-between mb-2">
          <span style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-secondary);">
            Knowledge State Classification (PDF Specification)
          </span>
          <a href="#/uncertainty-ledger" class="text-primary text-decoration-none" style="font-size: 12px; font-weight: 600;">
            View All in Ledger <i class="bi bi-arrow-right"></i>
          </a>
        </div>
        <div class="row g-2">
          <div class="col-6 col-md-4 col-xl-2">
            <div class="stat-card clickable-card" data-filter="verified" style="border-left: 3px solid var(--teal);">
              <div class="d-flex align-items-center justify-content-between">
                <span class="stat-label">Verified</span>
                <span class="badge-verified"><i class="bi bi-check-circle-fill me-1"></i>Human</span>
              </div>
              <div class="d-flex align-items-baseline gap-2 mt-2">
                <span class="stat-value" style="color: var(--teal);">${metrics.verifiedClaims}</span>
                <span style="font-size: 11px; color: var(--text-muted);">claims</span>
              </div>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Audited & confirmed</div>
            </div>
          </div>

          <div class="col-6 col-md-4 col-xl-2">
            <div class="stat-card clickable-card" data-filter="evidence-backed" style="border-left: 3px solid var(--secondary);">
              <div class="d-flex align-items-center justify-content-between">
                <span class="stat-label">Evidence-Backed</span>
                <span class="badge-evidence-backed"><i class="bi bi-link-45deg me-1"></i>Sources</span>
              </div>
              <div class="d-flex align-items-baseline gap-2 mt-2">
                <span class="stat-value" style="color: var(--secondary);">${metrics.evidenceBacked}</span>
                <span style="font-size: 11px; color: var(--text-muted);">records</span>
              </div>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Cited in git/docs</div>
            </div>
          </div>

          <div class="col-6 col-md-4 col-xl-2">
            <div class="stat-card clickable-card" data-filter="inferred" style="border-left: 3px solid var(--warning);">
              <div class="d-flex align-items-center justify-content-between">
                <span class="stat-label">Inferred</span>
                <span class="badge-inferred"><i class="bi bi-lightning-charge me-1"></i>AI</span>
              </div>
              <div class="d-flex align-items-baseline gap-2 mt-2">
                <span class="stat-value" style="color: var(--warning);">${metrics.inferred}</span>
                <span style="font-size: 11px; color: var(--text-muted);">needs review</span>
              </div>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Derived hypothesis</div>
            </div>
          </div>

          <div class="col-6 col-md-4 col-xl-2">
            <div class="stat-card clickable-card" data-filter="conflicting" style="border-left: 3px solid var(--danger);">
              <div class="d-flex align-items-center justify-content-between">
                <span class="stat-label">Conflicting</span>
                <span class="badge-conflicting"><i class="bi bi-exclamation-triangle me-1"></i>Disputed</span>
              </div>
              <div class="d-flex align-items-baseline gap-2 mt-2">
                <span class="stat-value text-danger">${metrics.conflicting}</span>
                <span style="font-size: 11px; color: var(--text-muted);">contradictions</span>
              </div>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Sources disagree</div>
            </div>
          </div>

          <div class="col-6 col-md-4 col-xl-2">
            <div class="stat-card clickable-card" data-filter="missing" style="border-left: 3px solid #9333ea;">
              <div class="d-flex align-items-center justify-content-between">
                <span class="stat-label">Missing</span>
                <span class="badge-missing"><i class="bi bi-question-diamond me-1"></i>Gaps</span>
              </div>
              <div class="d-flex align-items-baseline gap-2 mt-2">
                <span class="stat-value" style="color: #9333ea;">${metrics.missing}</span>
                <span style="font-size: 11px; color: var(--text-muted);">undocumented</span>
              </div>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Runbooks & secrets</div>
            </div>
          </div>

          <div class="col-6 col-md-4 col-xl-2">
            <div class="stat-card clickable-card" data-filter="outdated" style="border-left: 3px solid #64748b;">
              <div class="d-flex align-items-center justify-content-between">
                <span class="stat-label">Outdated</span>
                <span class="badge-outdated"><i class="bi bi-clock-history me-1"></i>Stale</span>
              </div>
              <div class="d-flex align-items-baseline gap-2 mt-2">
                <span class="stat-value" style="color: #64748b;">${metrics.outdated}</span>
                <span style="font-size: 11px; color: var(--text-muted);">>90 days</span>
              </div>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Likely obsolete</div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Main Grid: Intelligence Columns ────────────────────────── -->
      <div class="row g-4 mb-4">
        <!-- Left Column: Critical Continuity Risks & Connected Sources -->
        <div class="col-12 col-lg-7">
          <!-- Continuity Risks Card -->
          <div class="cos-card mb-4">
            <div class="cos-card-header">
              <div>
                <div class="cos-card-title"><i class="bi bi-shield-exclamation text-danger me-2"></i>Active Continuity Risks</div>
                <div class="cos-card-subtitle">Real-time single-point-of-failure analysis across systems</div>
              </div>
              <button class="cos-btn cos-btn-ghost btn-sm" id="btn-view-all-risks">
                View Risk Centre <i class="bi bi-arrow-right"></i>
              </button>
            </div>
            <div class="cos-card-body p-0">
              <div class="list-group list-group-flush">
                ${risks.slice(0, 3).map(r => `
                  <div class="list-group-item p-3 border-bottom">
                    <div class="d-flex align-items-start justify-content-between gap-2">
                      <div class="d-flex gap-2">
                        <span class="badge ${r.severity === 'critical' ? 'bg-danger' : r.severity === 'high' ? 'bg-warning text-dark' : 'bg-info text-dark'} text-uppercase" style="font-size: 10px; height: fit-content;">
                          ${r.severity}
                        </span>
                        <div>
                          <div style="font-weight: 600; font-size: 13px; color: var(--text-primary);">${r.title}</div>
                          <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">${r.description}</div>
                          <div class="d-flex align-items-center gap-3 mt-2" style="font-size: 11px; color: var(--text-muted);">
                            <span><i class="bi bi-box me-1"></i>Component: <strong>${r.affectedComponent || 'Platform'}</strong></span>
                            <span><i class="bi bi-person me-1"></i>Sole Owner: <strong>Alex Rivera</strong></span>
                          </div>
                        </div>
                      </div>
                      <button class="cos-btn cos-btn-secondary btn-sm flex-shrink-0" onclick="window.location.hash='#/impact-simulator'">
                        Mitigate
                      </button>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
            <div class="cos-card-footer d-flex align-items-center justify-content-between">
              <span style="font-size: 12px; color: var(--text-secondary);">
                <i class="bi bi-info-circle me-1"></i>3 single-point-of-failure components require immediate handover.
              </span>
              <a href="#/impact-simulator" class="cos-btn cos-btn-primary btn-sm">
                Run Simulation
              </a>
            </div>
          </div>

          <!-- Connected Sources & Ingestion Activity -->
          <div class="cos-card">
            <div class="cos-card-header">
              <div>
                <div class="cos-card-title"><i class="bi bi-diagram-2 text-primary me-2"></i>Multi-Source Ingestion Pipeline</div>
                <div class="cos-card-subtitle">Aggregated knowledge streams with audit trail</div>
              </div>
              <a href="#/sources" class="cos-btn cos-btn-ghost btn-sm">Manage Sources</a>
            </div>
            <div class="cos-card-body">
              <div class="row g-3">
                ${sources.slice(0, 4).map(s => `
                  <div class="col-12 col-sm-6">
                    <div class="p-3 rounded border bg-light d-flex align-items-center justify-content-between">
                      <div class="d-flex align-items-center gap-2">
                        <div class="source-icon-box" style="width: 32px; height: 32px; border-radius: 6px; background: #fff; border: 1px solid var(--border); display: flex; align-items: center; justify-content: center; font-size: 16px;">
                          <i class="bi ${s.icon || 'bi-database'} text-primary"></i>
                        </div>
                        <div>
                          <div style="font-weight: 600; font-size: 12px;">${s.name}</div>
                          <div style="font-size: 11px; color: var(--text-muted);">${s.documentsIndexed || 0} indexed</div>
                        </div>
                      </div>
                      <div>
                        ${s.status === 'connected' 
                          ? '<span class="badge bg-success-subtle text-success border border-success-subtle" style="font-size: 10px;"><i class="bi bi-check-circle me-1"></i>Live</span>'
                          : s.status === 'pending'
                          ? '<span class="badge bg-warning-subtle text-warning border border-warning-subtle" style="font-size: 10px;">Syncing</span>'
                          : '<span class="badge bg-secondary-subtle text-secondary border" style="font-size: 10px;">Offline</span>'
                        }
                      </div>
                    </div>
                  </div>
                `).join('')}
              </div>

              <!-- Ingestion trend sparkline -->
              <div class="mt-4 pt-3 border-top">
                <div class="d-flex align-items-center justify-content-between mb-2">
                  <span style="font-size: 12px; font-weight: 600; color: var(--text-secondary);">Weekly Reconstruction Progress</span>
                  <span style="font-size: 11px; color: var(--teal); font-weight: 600;">+9% since Sprint 22</span>
                </div>
                <div class="d-flex align-items-end gap-2" style="height: 48px;">
                  <div class="flex-grow-1 bg-primary-lighter rounded-top" style="height: 58%;" title="Day 1: 58%"></div>
                  <div class="flex-grow-1 bg-primary-lighter rounded-top" style="height: 61%;" title="Day 2: 61%"></div>
                  <div class="flex-grow-1 bg-primary-lighter rounded-top" style="height: 63%;" title="Day 3: 63%"></div>
                  <div class="flex-grow-1 bg-primary-lighter rounded-top" style="height: 63%;" title="Day 4: 63%"></div>
                  <div class="flex-grow-1 bg-primary-lighter rounded-top" style="height: 66%;" title="Day 5: 66%"></div>
                  <div class="flex-grow-1 bg-primary rounded-top" style="height: 67%;" title="Day 6: 67%"></div>
                  <div class="flex-grow-1 bg-primary rounded-top" style="height: 67%;" title="Today: 67%"></div>
                </div>
                <div class="d-flex justify-content-between text-muted mt-1" style="font-size: 10px;">
                  <span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span><span>Sun (Current)</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Column: Transition Hub & Latest Decisions -->
        <div class="col-12 col-lg-5">
          <!-- Active Transition Spotlight -->
          <div class="cos-card mb-4" style="border-top: 3px solid var(--primary);">
            <div class="cos-card-header">
              <div>
                <div class="cos-card-title"><i class="bi bi-arrow-repeat text-primary me-2"></i>Active Transition Spotlight</div>
                <div class="cos-card-subtitle">Primary engineering continuity handover</div>
              </div>
              <span class="badge bg-warning text-dark" style="font-size: 10px;">11 Days Remaining</span>
            </div>
            <div class="cos-card-body">
              <div class="d-flex align-items-center justify-content-between p-3 rounded mb-3" style="background: var(--main-bg); border: 1px solid var(--border);">
                <div class="d-flex align-items-center gap-2">
                  <div class="avatar-circle" style="width: 38px; height: 38px; border-radius: 50%; background: #fee2e2; color: #dc2626; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px;">
                    AR
                  </div>
                  <div>
                    <div style="font-weight: 700; font-size: 13px;">Alex Rivera</div>
                    <div style="font-size: 11px; color: var(--text-muted);">Senior Backend Engineer</div>
                  </div>
                </div>
                <i class="bi bi-arrow-right text-primary fs-5"></i>
                <div class="d-flex align-items-center gap-2">
                  <div class="avatar-circle" style="width: 38px; height: 38px; border-radius: 50%; background: #e0e7ff; color: #4f46e5; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px;">
                    SC
                  </div>
                  <div>
                    <div style="font-weight: 700; font-size: 13px;">Sam Chen</div>
                    <div style="font-size: 11px; color: var(--text-muted);">Junior Backend (Incoming)</div>
                  </div>
                </div>
              </div>

              <!-- Handover Checklist Preview -->
              <div class="mb-3">
                <div class="d-flex justify-content-between text-muted mb-1" style="font-size: 11px;">
                  <span>Handover Completion</span>
                  <span class="fw-bold text-dark">45% Complete</span>
                </div>
                <div class="progress" style="height: 6px;">
                  <div class="progress-bar bg-primary" role="progressbar" style="width: 45%;" aria-valuenow="45" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
              </div>

              <div class="d-flex flex-column gap-2 mb-3">
                <div class="d-flex align-items-center justify-content-between text-secondary" style="font-size: 12px;">
                  <span><i class="bi bi-check2-circle text-success me-2"></i>Responsibilities & Tasks Mapped</span>
                  <span class="badge bg-success-subtle text-success" style="font-size: 10px;">Done</span>
                </div>
                <div class="d-flex align-items-center justify-content-between text-secondary" style="font-size: 12px;">
                  <span><i class="bi bi-clock text-warning me-2"></i>Kafka & Data Pipeline Architecture Runbook</span>
                  <span class="badge bg-warning-subtle text-warning" style="font-size: 10px;">In Progress</span>
                </div>
                <div class="d-flex align-items-center justify-content-between text-secondary" style="font-size: 12px;">
                  <span><i class="bi bi-circle text-muted me-2"></i>Bug #001 & #002 Walkthrough Video</span>
                  <span class="badge bg-light text-muted border" style="font-size: 10px;">Pending</span>
                </div>
                <div class="d-flex align-items-center justify-content-between text-secondary" style="font-size: 12px;">
                  <span><i class="bi bi-circle text-muted me-2"></i>JWT Secret Key Rotation Protocol</span>
                  <span class="badge bg-danger-subtle text-danger" style="font-size: 10px;">Unresolved Gap</span>
                </div>
              </div>

              <div class="d-grid gap-2">
                <a href="#/handover-interview" class="cos-btn cos-btn-primary text-center">
                  <i class="bi bi-mic me-1"></i> Continue Handover Interview
                </a>
                <a href="#/rehearsal" class="cos-btn cos-btn-secondary text-center">
                  <i class="bi bi-mortarboard me-1"></i> Launch Incoming Rehearsal
                </a>
              </div>
            </div>
          </div>

          <!-- Latest Architectural Decisions -->
          <div class="cos-card">
            <div class="cos-card-header">
              <div>
                <div class="cos-card-title"><i class="bi bi-journal-text text-secondary me-2"></i>Decision Log (ADR)</div>
                <div class="cos-card-subtitle">Key architectural consensus captured</div>
              </div>
              <a href="#/knowledge-graph" class="cos-btn cos-btn-ghost btn-sm">Graph View</a>
            </div>
            <div class="cos-card-body p-0">
              <div class="list-group list-group-flush">
                ${decisions.slice(0, 3).map(d => `
                  <div class="list-group-item p-3 border-bottom">
                    <div class="d-flex align-items-center justify-content-between mb-1">
                      <span class="badge bg-light text-dark border" style="font-size: 10px; font-weight: 700;">${d.id.toUpperCase()}</span>
                      <span style="font-size: 11px; color: var(--text-muted);">${d.date}</span>
                    </div>
                    <div style="font-size: 12px; font-weight: 600; color: var(--text-primary);">${d.title}</div>
                    <div style="font-size: 11px; color: var(--text-secondary); margin-top: 3px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                      ${d.rationale}
                    </div>
                    <div class="d-flex align-items-center gap-1 mt-2 flex-wrap">
                      ${(d.relatedComponents || []).map(c => `
                        <span class="badge bg-light text-secondary border" style="font-size: 9px;">${c}</span>
                      `).join('')}
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Fast Action Dock ───────────────────────────────────────── -->
      <div class="p-3 bg-white rounded border d-flex align-items-center justify-content-between flex-wrap gap-3">
        <div class="d-flex align-items-center gap-3">
          <div style="width: 32px; height: 32px; border-radius: 50%; background: var(--primary-lighter); display: flex; align-items: center; justify-content: center; color: var(--primary);">
            <i class="bi bi-lightning-charge-fill"></i>
          </div>
          <div>
            <div style="font-weight: 700; font-size: 12px;">Need to query the project's institutional memory?</div>
            <div style="font-size: 11px; color: var(--text-muted);">The ContinuityOS AI Assistant is grounded on citations from Jira, Confluence, and GitHub.</div>
          </div>
        </div>
        <div class="d-flex align-items-center gap-2">
          <a href="#/assistant" class="cos-btn cos-btn-primary btn-sm">
            <i class="bi bi-chat-dots me-1"></i> Ask AI Assistant
          </a>
          <a href="#/knowledge-graph" class="cos-btn cos-btn-secondary btn-sm">
            <i class="bi bi-diagram-3 me-1"></i> Explore Knowledge Graph
          </a>
        </div>
      </div>
    </div>
  `;

  // 3. Attach Event Listeners
  const bannerSim = container.querySelector('#banner-btn-simulator');
  if (bannerSim) bannerSim.addEventListener('click', () => navigate('#/impact-simulator'));

  const bannerLedger = container.querySelector('#banner-btn-ledger');
  if (bannerLedger) bannerLedger.addEventListener('click', () => navigate('#/uncertainty-ledger'));

  const bannerInterview = container.querySelector('#banner-btn-interview');
  if (bannerInterview) bannerInterview.addEventListener('click', () => navigate('#/handover-interview'));

  const btnExport = container.querySelector('#btn-export-overview');
  if (btnExport) {
    btnExport.addEventListener('click', () => {
      window.print();
    });
  }

  const btnConnect = container.querySelector('#btn-connect-source-quick');
  if (btnConnect) {
    btnConnect.addEventListener('click', () => navigate('#/sources'));
  }

  const riskCenterBtn = container.querySelector('#btn-view-all-risks');
  if (riskCenterBtn) {
    riskCenterBtn.addEventListener('click', () => navigate('#/security'));
  }

  // Filter cards click to uncertainty ledger with filter
  container.querySelectorAll('.clickable-card').forEach(card => {
    card.addEventListener('click', () => {
      const filter = card.getAttribute('data-filter');
      window.location.hash = `#/uncertainty-ledger?classification=${filter}`;
    });
  });
}
