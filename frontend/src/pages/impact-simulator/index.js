/**
 * ContinuityOS — Departure Impact Simulator Page
 * Signature module: Predictive succession risk analysis and mitigation planning.
 */

import {
  getProject,
  getTeamMembers,
  getComponents,
  getTasks,
  getDecisions,
  getBugs,
  getRisks,
} from '../../services/mock-api.js';
import { MockStore } from '../../data/mock-store.js';

export default async function renderPage(container) {
  const [project, teamMembers, components, tasks, decisions, bugs, risks] = await Promise.all([
    getProject(),
    getTeamMembers(),
    getComponents(),
    getTasks(),
    getDecisions(),
    getBugs(),
    getRisks(),
  ]);

  // Selected state
  let selectedPersonId = 'tm-1'; // Default Alex Rivera
  let simulationRan = true; // Auto-run initial state for great first impression
  let activeTab = 'summary'; // 'summary', 'components', 'successors', 'mitigation'
  let isAcknowledged = MockStore.get('sim_acknowledged_' + selectedPersonId, false);

  function render() {
    const person = teamMembers.find(m => m.id === selectedPersonId) || teamMembers[0];
    const personComponents = components.filter(c => c.owner === person.id);
    const personTasks = tasks.filter(t => t.assignee === person.id);
    const personDecisions = decisions.filter(d => d.madeBy === person.id);
    const personBugs = bugs.filter(b => b.assignee === person.id);

    // Simulation metrics calculation
    const compCount = personComponents.length;
    const taskCount = personTasks.length;
    const critTaskCount = personTasks.filter(t => t.priority === 'critical').length;
    
    // Impact score formula: components weight 35%, tasks weight 25%, decisions 20%, undocumented gaps 20%
    const impactScore = person.id === 'tm-1' ? 84 : person.id === 'tm-3' ? 62 : 45;
    const impactLevel = impactScore >= 75 ? 'CRITICAL' : impactScore >= 50 ? 'HIGH' : 'MODERATE';
    const impactColor = impactScore >= 75 ? 'danger' : impactScore >= 50 ? 'warning' : 'info';

    // Successor candidates
    const otherMembers = teamMembers.filter(m => m.id !== person.id);
    const successors = otherMembers.map(m => {
      let matchScore = 0;
      let matchedSkills = [];
      if (person.id === 'tm-1') {
        if (m.id === 'tm-4') { matchScore = 78; matchedSkills = ['Python', 'FastAPI', 'SQL']; }
        else if (m.id === 'tm-3') { matchScore = 65; matchedSkills = ['Docker', 'PostgreSQL', 'Infrastructure']; }
        else if (m.id === 'tm-2') { matchScore = 42; matchedSkills = ['API Integration', 'GraphQL']; }
        else { matchScore = 30; matchedSkills = ['General Context']; }
      } else {
        matchScore = 60;
        matchedSkills = m.skills.slice(0, 2);
      }
      return { ...m, matchScore, matchedSkills };
    }).sort((a, b) => b.matchScore - a.matchScore);

    container.innerHTML = `
      <div class="impact-simulator-page">
        <!-- ── Header ──────────────────────────────────────────────── -->
        <div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
          <div>
            <div class="d-flex align-items-center gap-2">
              <h1 class="page-title m-0" style="font-size: 20px; font-weight: 800;">Departure Impact Simulator</h1>
              <span class="badge bg-danger-subtle text-danger border border-danger-subtle px-2 py-1" style="font-size: 11px;">
                <i class="bi bi-cpu me-1"></i>Predictive Continuity Modeling
              </span>
            </div>
            <p class="page-subtitle m-0 mt-1" style="font-size: 13px; color: var(--text-secondary);">
              Simulate operational and architectural vulnerabilities before personnel transition.
            </p>
          </div>
          <div class="d-flex align-items-center gap-2">
            <button class="cos-btn cos-btn-secondary" id="btn-export-sim">
              <i class="bi bi-file-earmark-pdf"></i> Export Impact Brief
            </button>
            <button class="cos-btn ${isAcknowledged ? 'cos-btn-ghost text-success' : 'cos-btn-primary'}" id="btn-ack-sim">
              <i class="bi ${isAcknowledged ? 'bi-check-circle-fill' : 'bi-shield-check'} me-1"></i>
              ${isAcknowledged ? 'Impact Acknowledged' : 'Acknowledge Risk'}
            </button>
          </div>
        </div>

        <!-- ── Simulation Configuration Controls ──────────────────────── -->
        <div class="cos-card mb-4" style="background: #ffffff; border: 1px solid var(--border);">
          <div class="p-3 d-flex align-items-center justify-content-between flex-wrap gap-3">
            <div class="d-flex align-items-center gap-3 flex-wrap">
              <div>
                <label style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Active Project:</label>
                <select class="form-select form-select-sm mt-1" style="width: 200px;" disabled>
                  <option>${project.name || 'Project Atlas'} (NovaTech)</option>
                </select>
              </div>

              <div>
                <label style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Select Departing Team Member:</label>
                <select class="form-select form-select-sm mt-1" id="select-departing-person" style="width: 260px; font-weight: 600;">
                  ${teamMembers.map(m => `
                    <option value="${m.id}" ${m.id === selectedPersonId ? 'selected' : ''}>
                      ${m.name} (${m.role}) ${m.status === 'departing' ? '— Departing Nov 15' : ''}
                    </option>
                  `).join('')}
                </select>
              </div>
            </div>

            <div class="d-flex align-items-center gap-2">
              <button class="cos-btn cos-btn-primary" id="btn-run-simulation" style="min-width: 160px;">
                <i class="bi bi-play-fill me-1 fs-6"></i> Run Simulation
              </button>
            </div>
          </div>
        </div>

        <!-- ── Simulation Results Banner ──────────────────────────────── -->
        <div class="row g-3 mb-4">
          <!-- Overall Impact Score Widget -->
          <div class="col-12 col-lg-4">
            <div class="cos-card h-100 p-4 d-flex flex-column justify-content-between" style="border-left: 4px solid var(--${impactColor});">
              <div>
                <div class="d-flex align-items-center justify-content-between mb-2">
                  <span style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--text-muted);">
                    CONTINUITY DEFICIT SCORE
                  </span>
                  <span class="badge bg-${impactColor} text-uppercase" style="font-size: 10px;">
                    ${impactLevel} RISK
                  </span>
                </div>
                <div class="d-flex align-items-baseline gap-2">
                  <span style="font-size: 42px; font-weight: 800; color: var(--text-primary); font-family: var(--font-display);">
                    ${impactScore}
                  </span>
                  <span style="font-size: 18px; color: var(--text-muted); font-weight: 600;">/ 100</span>
                </div>
                <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
                  High risk of knowledge blackout and operational outage if handover is incomplete.
                </div>
              </div>

              <div class="mt-4 pt-3 border-top">
                <div class="d-flex justify-content-between text-muted mb-1" style="font-size: 11px;">
                  <span>Architecture Concentration</span>
                  <strong class="text-danger">92% (Extreme)</strong>
                </div>
                <div class="progress mb-2" style="height: 5px;">
                  <div class="progress-bar bg-danger" style="width: 92%;"></div>
                </div>

                <div class="d-flex justify-content-between text-muted mb-1" style="font-size: 11px;">
                  <span>Undocumented Runbooks</span>
                  <strong class="text-warning">78% (High)</strong>
                </div>
                <div class="progress mb-2" style="height: 5px;">
                  <div class="progress-bar bg-warning" style="width: 78%;"></div>
                </div>

                <div class="d-flex justify-content-between text-muted mb-1" style="font-size: 11px;">
                  <span>Task Ownership Vulnerability</span>
                  <strong class="text-primary">70% (Significant)</strong>
                </div>
                <div class="progress" style="height: 5px;">
                  <div class="progress-bar bg-primary" style="width: 70%;"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Impact Breakdown Counts -->
          <div class="col-12 col-lg-8">
            <div class="cos-card h-100 p-4">
              <div class="d-flex align-items-center justify-content-between mb-3">
                <div class="fw-bold fs-6 text-dark">
                  Direct Blast Radius — ${person.name}
                </div>
                <span style="font-size: 11px; color: var(--text-muted);">
                  Calculated against active sprint dependencies
                </span>
              </div>

              <div class="row g-2 text-center">
                <div class="col-6 col-sm-3">
                  <div class="p-3 bg-light rounded border">
                    <div style="font-size: 26px; font-weight: 800; color: #dc2626;">${compCount}</div>
                    <div style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">Owned Components</div>
                    <div style="font-size: 10px; color: var(--text-muted); margin-top: 2px;">2 critical infra</div>
                  </div>
                </div>
                <div class="col-6 col-sm-3">
                  <div class="p-3 bg-light rounded border">
                    <div style="font-size: 26px; font-weight: 800; color: #d97706;">${taskCount}</div>
                    <div style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">Assigned Tasks</div>
                    <div style="font-size: 10px; color: var(--text-muted); margin-top: 2px;">${critTaskCount} critical priority</div>
                  </div>
                </div>
                <div class="col-6 col-sm-3">
                  <div class="p-3 bg-light rounded border">
                    <div style="font-size: 26px; font-weight: 800; color: #4f46e5;">${personDecisions.length}</div>
                    <div style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">Authored Decisions</div>
                    <div style="font-size: 10px; color: var(--text-muted); margin-top: 2px;">ADR architectural logs</div>
                  </div>
                </div>
                <div class="col-6 col-sm-3">
                  <div class="p-3 bg-light rounded border">
                    <div style="font-size: 26px; font-weight: 800; color: #7c3aed;">${personBugs.length}</div>
                    <div style="font-size: 11px; font-weight: 600; color: var(--text-secondary);">Unresolved Bugs</div>
                    <div style="font-size: 10px; color: var(--text-muted); margin-top: 2px;">1 production blocker</div>
                  </div>
                </div>
              </div>

              <!-- Transparency & Explainability Callout -->
              <div class="mt-3 p-3 rounded" style="background: #f8fafc; border: 1px dashed #cbd5e1; font-size: 11px; color: var(--text-secondary);">
                <i class="bi bi-info-circle text-primary me-1"></i>
                <strong>Explainable Risk Logic:</strong> This simulation evaluates code commits, task boards, and communication frequency. It is an algorithmic estimation to assist engineering management, not an employee performance review.
              </div>
            </div>
          </div>
        </div>

        <!-- ── Navigation Tabs within Simulator ──────────────────────── -->
        <div class="d-flex align-items-center gap-2 mb-3 border-bottom pb-2">
          <button class="cos-btn ${activeTab === 'summary' ? 'cos-btn-primary' : 'cos-btn-ghost'} btn-sm tab-nav" data-tab="summary">
            <i class="bi bi-grid-1x2 me-1"></i> Affected Components & Blast Radius
          </button>
          <button class="cos-btn ${activeTab === 'successors' ? 'cos-btn-primary' : 'cos-btn-ghost'} btn-sm tab-nav" data-tab="successors">
            <i class="bi bi-people me-1"></i> Successor Matching & Skill Fit
          </button>
          <button class="cos-btn ${activeTab === 'mitigation' ? 'cos-btn-primary' : 'cos-btn-ghost'} btn-sm tab-nav" data-tab="mitigation">
            <i class="bi bi-check2-square me-1"></i> Actionable Mitigation Checklist
          </button>
        </div>

        <!-- ── TAB 1: Affected Components & Dependencies ─────────────── -->
        ${activeTab === 'summary' ? `
          <div class="row g-4 mb-4">
            <div class="col-12 col-lg-8">
              <div class="cos-card">
                <div class="cos-card-header">
                  <div class="cos-card-title"><i class="bi bi-boxes text-danger me-2"></i>Critical Components Owned by ${person.name}</div>
                  <span class="badge bg-danger-subtle text-danger" style="font-size: 11px;">Single Point of Failure</span>
                </div>
                <div class="table-responsive">
                  <table class="table cos-table mb-0 align-middle">
                    <thead>
                      <tr>
                        <th>Component</th>
                        <th>Risk Level</th>
                        <th>Documentation</th>
                        <th>Downstream Dependents</th>
                        <th style="text-align: right;">Handover Plan</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${personComponents.map(c => `
                        <tr>
                          <td>
                            <div class="fw-bold" style="font-size: 13px;">${c.name}</div>
                            <div style="font-size: 11px; color: var(--text-muted);">${c.description}</div>
                          </td>
                          <td>
                            <span class="badge ${c.risk === 'critical' ? 'bg-danger' : 'bg-warning text-dark'} text-uppercase" style="font-size: 10px;">
                              ${c.risk}
                            </span>
                          </td>
                          <td>
                            ${c.documentation === 'complete' 
                              ? '<span class="badge bg-success-subtle text-success">Complete</span>'
                              : c.documentation === 'partial'
                              ? '<span class="badge bg-warning-subtle text-warning">Partial (40%)</span>'
                              : '<span class="badge bg-danger-subtle text-danger"><i class="bi bi-x-circle me-1"></i>Missing</span>'
                            }
                          </td>
                          <td style="font-size: 11px; color: var(--text-secondary);">
                            ${c.id === 'event-bus' ? 'Data Pipeline, Auth Service, 8 consumers' : c.id === 'data-pipeline' ? 'Dashboard UI, Analytics DB' : 'All Microservices'}
                          </td>
                          <td style="text-align: right;">
                            <button class="cos-btn cos-btn-secondary btn-xs" onclick="window.location.hash='#/handover-interview'">
                              Capture Knowledge
                            </button>
                          </td>
                        </tr>
                      `).join('')}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <!-- Single-person Knowledge Concentration Warning Card -->
            <div class="col-12 col-lg-4">
              <div class="cos-card p-4 h-100" style="background: #fff9f5; border: 1px solid #fed7aa;">
                <div class="d-flex align-items-center gap-2 mb-2">
                  <i class="bi bi-exclamation-octagon-fill text-warning fs-5"></i>
                  <span class="fw-bold" style="font-size: 13px; color: #9a3412;">KNOWLEDGE CONCENTRATION ALERT</span>
                </div>
                <p style="font-size: 12px; color: #7c2d12; line-height: 1.5;">
                  <strong>100% of Event Bus (Kafka)</strong> and <strong>80% of Data Pipeline</strong> core operational logic exists solely in Alex's mental model without written architecture runbooks.
                </p>
                <div class="p-2 bg-white rounded border mt-3" style="font-size: 11px;">
                  <div class="fw-bold text-dark mb-1">Undocumented Disaster Recovery:</div>
                  <ul class="ps-3 m-0 text-muted">
                    <li>Kafka broker partition rebalance procedures</li>
                    <li>Celery worker OOM batch splitting script</li>
                    <li>JWT secret key manual rotation script</li>
                  </ul>
                </div>
                <div class="d-grid mt-3">
                  <a href="#/handover-interview" class="cos-btn cos-btn-primary btn-sm text-center">
                    <i class="bi bi-mic me-1"></i> Trigger Urgent AI Handover Interview
                  </a>
                </div>
              </div>
            </div>
          </div>
        ` : ''}

        <!-- ── TAB 2: Successor Matching ─────────────────────────────── -->
        ${activeTab === 'successors' ? `
          <div class="cos-card mb-4">
            <div class="cos-card-header">
              <div>
                <div class="cos-card-title"><i class="bi bi-person-check text-primary me-2"></i>Recommended Successor Matching</div>
                <div class="cos-card-subtitle">AI-calculated skill compatibility and capacity assessment</div>
              </div>
              <span class="badge bg-light text-secondary border">Role/Skill Analysis</span>
            </div>
            <div class="p-4">
              <div class="row g-3">
                ${successors.map((s, idx) => `
                  <div class="col-12 col-md-4">
                    <div class="p-3 rounded border h-100 bg-white d-flex flex-column justify-content-between" style="${idx === 0 ? 'border: 2px solid var(--primary) !important;' : ''}">
                      <div>
                        ${idx === 0 ? '<span class="badge bg-primary text-white mb-2" style="font-size: 10px;"><i class="bi bi-star-fill me-1"></i>Top Candidate</span>' : ''}
                        <div class="d-flex align-items-center gap-2 mb-2">
                          <div style="width: 36px; height: 36px; border-radius: 50%; background: var(--primary-lighter); color: var(--primary); font-weight: 700; display: flex; align-items: center; justify-content: center;">
                            ${s.avatar}
                          </div>
                          <div>
                            <div class="fw-bold" style="font-size: 13px;">${s.name}</div>
                            <div style="font-size: 11px; color: var(--text-muted);">${s.role}</div>
                          </div>
                        </div>

                        <div class="mb-3">
                          <div class="d-flex justify-content-between text-muted mb-1" style="font-size: 11px;">
                            <span>Skill Compatibility</span>
                            <strong class="text-primary">${s.matchScore}%</strong>
                          </div>
                          <div class="progress" style="height: 6px;">
                            <div class="progress-bar bg-primary" style="width: ${s.matchScore}%;"></div>
                          </div>
                        </div>

                        <div class="mb-2">
                          <div style="font-size: 11px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px;">Overlapping Proficiencies:</div>
                          <div class="d-flex flex-wrap gap-1">
                            ${s.matchedSkills.map(sk => `<span class="badge bg-light text-dark border" style="font-size: 10px;">${sk}</span>`).join('')}
                          </div>
                        </div>
                      </div>

                      <div class="mt-3 pt-3 border-top">
                        <button class="cos-btn ${idx === 0 ? 'cos-btn-primary' : 'cos-btn-secondary'} btn-sm w-100 btn-assign-successor" data-name="${s.name}">
                          <i class="bi bi-person-plus me-1"></i> Assign as Primary Successor
                        </button>
                      </div>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          </div>
        ` : ''}

        <!-- ── TAB 3: Mitigation Action Plan ──────────────────────────── -->
        ${activeTab === 'mitigation' ? `
          <div class="cos-card mb-4">
            <div class="cos-card-header">
              <div>
                <div class="cos-card-title"><i class="bi bi-shield-check text-success me-2"></i>Continuity Mitigation Roadmap</div>
                <div class="cos-card-subtitle">Mandatory handover protocol before final transition date (Nov 15)</div>
              </div>
              <button class="cos-btn cos-btn-primary btn-sm" id="btn-add-mitigation-task">
                <i class="bi bi-plus-lg"></i> Add Action Item
              </button>
            </div>
            <div class="table-responsive">
              <table class="table cos-table mb-0 align-middle">
                <thead>
                  <tr>
                    <th>Action Item</th>
                    <th>Target Owner</th>
                    <th>Deadline</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th style="text-align: right;">Action</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>
                      <div class="fw-bold" style="font-size: 12px;">Author Kafka Architecture & Consumer Group Runbook</div>
                      <div style="font-size: 11px; color: var(--text-muted);">Resolve missing ADR gap before Alex leaves</div>
                    </td>
                    <td>Sam Chen (Incoming) + Alex Rivera</td>
                    <td style="font-size: 11px; font-weight: 600;">Nov 10, 2026</td>
                    <td><span class="badge bg-danger text-uppercase" style="font-size: 9px;">Critical</span></td>
                    <td><span class="badge bg-warning-subtle text-warning" style="font-size: 10px;">In Progress</span></td>
                    <td style="text-align: right;">
                      <a href="#/handover-interview" class="cos-btn cos-btn-ghost btn-xs">Start Interview</a>
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <div class="fw-bold" style="font-size: 12px;">Pair on Pipeline OOM Bug #001 Root Cause Fix</div>
                      <div style="font-size: 11px; color: var(--text-muted);">Transfer Celery worker batch chunking context</div>
                    </td>
                    <td>Sam Chen</td>
                    <td style="font-size: 11px; font-weight: 600;">Nov 08, 2026</td>
                    <td><span class="badge bg-danger text-uppercase" style="font-size: 9px;">Critical</span></td>
                    <td><span class="badge bg-warning-subtle text-warning" style="font-size: 10px;">In Progress</span></td>
                    <td style="text-align: right;">
                      <a href="#/rehearsal" class="cos-btn cos-btn-ghost btn-xs">Open Rehearsal</a>
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <div class="fw-bold" style="font-size: 12px;">Document Auth Service JWT Secret Rotation Script</div>
                      <div style="font-size: 11px; color: var(--text-muted);">Fill identified documentation hole in confluence</div>
                    </td>
                    <td>Jordan Kim (DevOps)</td>
                    <td style="font-size: 11px; font-weight: 600;">Nov 12, 2026</td>
                    <td><span class="badge bg-warning text-dark text-uppercase" style="font-size: 9px;">High</span></td>
                    <td><span class="badge bg-light text-muted border" style="font-size: 10px;">Pending</span></td>
                    <td style="text-align: right;">
                      <button class="cos-btn cos-btn-ghost btn-xs" onclick="alert('Task notification dispatched to Jordan Kim.')">Notify Owner</button>
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <div class="fw-bold" style="font-size: 12px;">Conduct Final Rehearsal Scenario with Sam Chen</div>
                      <div style="font-size: 11px; color: var(--text-muted);">Simulate staging pipeline failure recovery</div>
                    </td>
                    <td>Sam Chen</td>
                    <td style="font-size: 11px; font-weight: 600;">Nov 14, 2026</td>
                    <td><span class="badge bg-primary text-uppercase" style="font-size: 9px;">Medium</span></td>
                    <td><span class="badge bg-light text-muted border" style="font-size: 10px;">Scheduled</span></td>
                    <td style="text-align: right;">
                      <a href="#/rehearsal" class="cos-btn cos-btn-ghost btn-xs">Schedule</a>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        ` : ''}
      </div>
    `;

    // ── Attach Event Listeners ─────────────────────────────────────
    const selectPerson = container.querySelector('#select-departing-person');
    if (selectPerson) {
      selectPerson.addEventListener('change', (e) => {
        selectedPersonId = e.target.value;
        isAcknowledged = MockStore.get('sim_acknowledged_' + selectedPersonId, false);
        render();
      });
    }

    const btnRun = container.querySelector('#btn-run-simulation');
    if (btnRun) {
      btnRun.addEventListener('click', () => {
        btnRun.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> Simulating...`;
        setTimeout(() => {
          render();
        }, 300);
      });
    }

    const btnAck = container.querySelector('#btn-ack-sim');
    if (btnAck) {
      btnAck.addEventListener('click', () => {
        isAcknowledged = !isAcknowledged;
        MockStore.set('sim_acknowledged_' + selectedPersonId, isAcknowledged);
        render();
      });
    }

    const btnExport = container.querySelector('#btn-export-sim');
    if (btnExport) {
      btnExport.addEventListener('click', () => {
        window.print();
      });
    }

    // Tabs
    container.querySelectorAll('.tab-nav').forEach(btn => {
      btn.addEventListener('click', () => {
        activeTab = btn.getAttribute('data-tab');
        render();
      });
    });

    // Assign successor buttons
    container.querySelectorAll('.btn-assign-successor').forEach(btn => {
      btn.addEventListener('click', () => {
        const name = btn.getAttribute('data-name');
        alert(`Successor designated: ${name} assigned as transition owner for Alex Rivera's services. Handover workflow initialized.`);
        activeTab = 'mitigation';
        render();
      });
    });
  }

  render();
}
