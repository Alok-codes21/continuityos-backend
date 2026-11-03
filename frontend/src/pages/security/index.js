/**
 * ContinuityOS — Security & Risks Centre Page
 * Access governance, single-person dependency audits, and sensitive data protection.
 */

import {
  getRisks,
  getTeamMembers,
  getComponents,
} from '../../services/mock-api.js';

export default async function renderPage(container) {
  const [risks, teamMembers, components] = await Promise.all([
    getRisks(),
    getTeamMembers(),
    getComponents(),
  ]);

  let activeTab = 'risks'; // 'risks', 'audit', 'rbac', 'redaction'

  // Audit event log
  const auditLogs = [
    { id: 'aud-1', event: 'Knowledge Claim Approved', user: 'Alex Rivera', role: 'Senior Backend', resource: 'kr-001 (50k events/min)', timestamp: 'Today, 10:15 AM', status: 'verified' },
    { id: 'aud-2', event: 'Granular Scope Updated', user: 'Jordan Kim', role: 'DevOps Lead', resource: 'GitHub (novatech/infra-kafka)', timestamp: 'Today, 09:30 AM', status: 'success' },
    { id: 'aud-3', event: 'Contradiction Flagged', user: 'System (Auditor)', role: 'Engine', resource: 'doc-012 (Incident Report Nov 2025)', timestamp: 'Yesterday, 16:45 PM', status: 'warning' },
    { id: 'aud-4', event: 'Handover Dossier Generated', user: 'Maya Patel', role: 'Product Manager', resource: 'ho-001 (Data Pipeline Handover)', timestamp: 'Oct 31, 2026', status: 'success' },
    { id: 'aud-5', event: 'OAuth Access Revoked', user: 'Alex Rivera', role: 'Senior Backend', resource: 'Google Drive Connector', timestamp: 'Oct 29, 2026', status: 'revoked' },
  ];

  function render() {
    container.innerHTML = `
      <div class="security-page">
        <!-- ── Top Header ────────────────────────────────────────────── -->
        <div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
          <div>
            <div class="d-flex align-items-center gap-2">
              <h1 class="page-title m-0" style="font-size: 20px; font-weight: 800;">Risk & Security Governance Centre</h1>
              <span class="badge bg-danger-subtle text-danger border border-danger-subtle px-2 py-1" style="font-size: 11px;">
                <i class="bi bi-shield-lock-fill me-1"></i>Zero-Trust Audit Log
              </span>
            </div>
            <p class="page-subtitle m-0 mt-1" style="font-size: 13px; color: var(--text-secondary);">
              Continuous organizational resilience monitoring, secret exposure prevention, and access controls.
            </p>
          </div>
          <div class="d-flex align-items-center gap-2">
            <button class="cos-btn ${activeTab === 'risks' ? 'cos-btn-primary' : 'cos-btn-secondary'} btn-sm tab-btn" data-tab="risks">
              <i class="bi bi-shield-exclamation me-1"></i> Continuity Risks (${risks.length})
            </button>
            <button class="cos-btn ${activeTab === 'audit' ? 'cos-btn-primary' : 'cos-btn-secondary'} btn-sm tab-btn" data-tab="audit">
              <i class="bi bi-journal-text me-1"></i> Audit Trail
            </button>
            <button class="cos-btn ${activeTab === 'rbac' ? 'cos-btn-primary' : 'cos-btn-secondary'} btn-sm tab-btn" data-tab="rbac">
              <i class="bi bi-person-badge me-1"></i> Team RBAC
            </button>
            <button class="cos-btn ${activeTab === 'redaction' ? 'cos-btn-primary' : 'cos-btn-secondary'} btn-sm tab-btn" data-tab="redaction">
              <i class="bi bi-eye-slash me-1"></i> Sensitive Redaction
            </button>
          </div>
        </div>

        <!-- ── TAB 1: Continuity Risks ───────────────────────────────── -->
        ${activeTab === 'risks' ? `
          <div class="row g-4 mb-4">
            <div class="col-12">
              <div class="cos-card">
                <div class="cos-card-header">
                  <div>
                    <div class="cos-card-title"><i class="bi bi-exclamation-triangle text-danger me-2"></i>Active Single-Point-of-Failure Dependencies</div>
                    <div class="cos-card-subtitle">Real-time risk radar across microservices and personnel</div>
                  </div>
                  <span class="badge bg-danger text-white">3 High/Critical Vulnerabilities</span>
                </div>
                <div class="table-responsive">
                  <table class="table cos-table mb-0 align-middle">
                    <thead>
                      <tr>
                        <th>Risk Assessment</th>
                        <th>Severity</th>
                        <th>Affected Entity</th>
                        <th>Single Knowledge Holder</th>
                        <th>Mitigation Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${risks.map(r => `
                        <tr>
                          <td>
                            <div class="fw-bold" style="font-size: 13px;">${r.title}</div>
                            <div style="font-size: 11px; color: var(--text-muted);">${r.description}</div>
                          </td>
                          <td>
                            <span class="badge ${r.severity === 'critical' ? 'bg-danger' : r.severity === 'high' ? 'bg-warning text-dark' : 'bg-info text-dark'} text-uppercase" style="font-size: 10px;">
                              ${r.severity}
                            </span>
                          </td>
                          <td>
                            <span class="badge bg-light text-dark border">
                              <i class="bi bi-box me-1"></i>${r.affectedComponent || 'Platform'}
                            </span>
                          </td>
                          <td>
                            <div class="d-flex align-items-center gap-1">
                              <span style="width: 20px; height: 20px; border-radius: 50%; background: #fee2e2; color: #dc2626; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700;">AR</span>
                              <span style="font-size: 12px; font-weight: 600;">Alex Rivera</span>
                            </div>
                          </td>
                          <td>
                            <a href="#/impact-simulator" class="cos-btn cos-btn-secondary btn-xs">
                              Run Simulation Plan
                            </a>
                          </td>
                        </tr>
                      `).join('')}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        ` : ''}

        <!-- ── TAB 2: Immutable Audit Trail ──────────────────────────── -->
        ${activeTab === 'audit' ? `
          <div class="cos-card mb-4">
            <div class="cos-card-header">
              <div>
                <div class="cos-card-title"><i class="bi bi-journal-text text-secondary me-2"></i>Permission & Verification Audit Ledger</div>
                <div class="cos-card-subtitle">Cryptographic record of all claim verifications and access revocations</div>
              </div>
              <button class="cos-btn cos-btn-secondary btn-sm" onclick="alert('Exporting audit log as signed JSON.')">
                <i class="bi bi-download"></i> Export Audit Log
              </button>
            </div>
            <div class="table-responsive">
              <table class="table cos-table mb-0 align-middle">
                <thead>
                  <tr>
                    <th>Event Type</th>
                    <th>Actor & Role</th>
                    <th>Target Resource / Claim</th>
                    <th>Status</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  ${auditLogs.map(a => `
                    <tr>
                      <td class="fw-bold" style="font-size: 12px;">${a.event}</td>
                      <td>
                        <div style="font-size: 12px; font-weight: 600;">${a.user}</div>
                        <div style="font-size: 10px; color: var(--text-muted);">${a.role}</div>
                      </td>
                      <td style="font-size: 12px;"><code>${a.resource}</code></td>
                      <td>
                        <span class="badge ${a.status === 'verified' || a.status === 'success' ? 'bg-success-subtle text-success' : a.status === 'warning' ? 'bg-warning-subtle text-warning' : 'bg-danger-subtle text-danger'}" style="font-size: 10px;">
                          ${a.status.toUpperCase()}
                        </span>
                      </td>
                      <td style="font-size: 11px; color: var(--text-muted);">${a.timestamp}</td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        ` : ''}

        <!-- ── TAB 3: Team RBAC ──────────────────────────────────────── -->
        ${activeTab === 'rbac' ? `
          <div class="cos-card mb-4">
            <div class="cos-card-header">
              <div>
                <div class="cos-card-title"><i class="bi bi-people-fill text-primary me-2"></i>Team Membership & Permission Scopes</div>
                <div class="cos-card-subtitle">Multi-tenant role-based access control per DEC-002</div>
              </div>
              <button class="cos-btn cos-btn-primary btn-sm" onclick="alert('Invite team member dialog.')">
                <i class="bi bi-plus-lg"></i> Invite Member
              </button>
            </div>
            <div class="table-responsive">
              <table class="table cos-table mb-0 align-middle">
                <thead>
                  <tr>
                    <th>Member</th>
                    <th>Project Role</th>
                    <th>Continuity Scope</th>
                    <th>Status</th>
                    <th style="text-align: right;">Permissions</th>
                  </tr>
                </thead>
                <tbody>
                  ${teamMembers.map(m => `
                    <tr>
                      <td>
                        <div class="d-flex align-items-center gap-2">
                          <div style="width: 32px; height: 32px; border-radius: 50%; background: var(--primary-lighter); color: var(--primary); font-weight: 700; display: flex; align-items: center; justify-content: center;">
                            ${m.avatar}
                          </div>
                          <div>
                            <div class="fw-bold" style="font-size: 12px;">${m.name}</div>
                            <div style="font-size: 11px; color: var(--text-muted);">${m.email}</div>
                          </div>
                        </div>
                      </td>
                      <td style="font-size: 12px;">${m.role}</td>
                      <td>
                        <span class="badge bg-light text-secondary border">
                          ${m.status === 'departing' ? 'Full Architecture (Departing)' : m.status === 'incoming' ? 'Incoming Read-Only' : 'Maintainer'}
                        </span>
                      </td>
                      <td>
                        <span class="badge ${m.status === 'departing' ? 'bg-danger-subtle text-danger' : m.status === 'incoming' ? 'bg-primary-subtle text-primary' : 'bg-success-subtle text-success'}">
                          ${m.status}
                        </span>
                      </td>
                      <td style="text-align: right;">
                        <button class="cos-btn cos-btn-ghost btn-xs text-primary" onclick="alert('Manage permissions for ${m.name}')">
                          Configure
                        </button>
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        ` : ''}

        <!-- ── TAB 4: Sensitive Data Redaction ───────────────────────── -->
        ${activeTab === 'redaction' ? `
          <div class="cos-card p-4 bg-white mb-4">
            <div class="fw-bold fs-6 text-dark mb-1"><i class="bi bi-eye-slash-fill text-warning me-2"></i>Automated Secret & PII Redaction Engine</div>
            <p class="text-muted mb-3" style="font-size: 12px;">
              ContinuityOS automatically strips API secrets, JWT private keys, and personal customer data before persisting knowledge chunks into the institutional ledger.
            </p>

            <div class="row g-3">
              <div class="col-md-4">
                <div class="p-3 rounded border bg-light">
                  <div class="fw-bold text-dark" style="font-size: 13px;">Secret Scanners Active</div>
                  <div class="d-flex align-items-baseline gap-2 mt-1">
                    <span class="fs-4 fw-bold text-success">14 Rules</span>
                  </div>
                  <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">AWS keys, GitHub PATs, JWT tokens</div>
                </div>
              </div>
              <div class="col-md-4">
                <div class="p-3 rounded border bg-light">
                  <div class="fw-bold text-dark" style="font-size: 13px;">Redactions Executed</div>
                  <div class="d-flex align-items-baseline gap-2 mt-1">
                    <span class="fs-4 fw-bold text-primary">38 Items</span>
                  </div>
                  <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Zero secrets exposed to LLM context</div>
                </div>
              </div>
              <div class="col-md-4">
                <div class="p-3 rounded border bg-light">
                  <div class="fw-bold text-dark" style="font-size: 13px;">Compliance Status</div>
                  <div class="d-flex align-items-baseline gap-2 mt-1">
                    <span class="badge bg-success text-white mt-1">SOC-2 Compliant</span>
                  </div>
                  <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Encrypted at rest with AES-256</div>
                </div>
              </div>
            </div>
          </div>
        ` : ''}
      </div>
    `;

    container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        activeTab = btn.getAttribute('data-tab');
        render();
      });
    });
  }

  render();
}
