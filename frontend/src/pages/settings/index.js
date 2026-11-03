/**
 * ContinuityOS — Settings Page
 * Project configuration, workspace parameters, and demo store reset.
 */

import { getProject } from '../../services/mock-api.js';
import { initializeStore } from '../../data/mock-store.js';

export default async function renderPage(container) {
  const project = await getProject();

  function render() {
    container.innerHTML = `
      <div class="settings-page">
        <!-- ── Top Header ────────────────────────────────────────────── -->
        <div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
          <div>
            <div class="d-flex align-items-center gap-2">
              <h1 class="page-title m-0" style="font-size: 20px; font-weight: 800;">Workspace Settings</h1>
              <span class="badge bg-light text-dark border px-2 py-1" style="font-size: 11px;">
                <i class="bi bi-gear me-1"></i>Project Atlas Environment
              </span>
            </div>
            <p class="page-subtitle m-0 mt-1" style="font-size: 13px; color: var(--text-secondary);">
              Manage enterprise organisation details, RAG model configurations, and demo data state.
            </p>
          </div>
        </div>

        <div class="row g-4 mb-4">
          <!-- Left: General & Organization Settings -->
          <div class="col-12 col-lg-7">
            <div class="cos-card p-4 bg-white mb-4">
              <div class="fw-bold fs-6 text-dark mb-3"><i class="bi bi-building me-2 text-primary"></i>Organisation Profile</div>
              <div class="mb-3">
                <label class="form-label" style="font-size: 12px; font-weight: 600;">Organisation Name</label>
                <input type="text" class="form-control" value="${project.organisation || 'NovaTech Engineering'}" readonly>
              </div>
              <div class="mb-3">
                <label class="form-label" style="font-size: 12px; font-weight: 600;">Active Continuity Project</label>
                <input type="text" class="form-control" value="${project.name || 'Project Atlas'}" readonly>
              </div>
              <div class="row g-2">
                <div class="col-6">
                  <label class="form-label" style="font-size: 12px; font-weight: 600;">Current Sprint</label>
                  <input type="text" class="form-control" value="${project.sprint || 'Sprint 23'}" readonly>
                </div>
                <div class="col-6">
                  <label class="form-label" style="font-size: 12px; font-weight: 600;">Cycle Dates</label>
                  <input type="text" class="form-control" value="${project.sprintDates || 'Oct 28 – Nov 11, 2026'}" readonly>
                </div>
              </div>
            </div>

            <!-- Backend Integration Parameters -->
            <div class="cos-card p-4 bg-white">
              <div class="fw-bold fs-6 text-dark mb-1"><i class="bi bi-cpu me-2 text-primary"></i>Backend API & RAG Connection</div>
              <p class="text-muted mb-3" style="font-size: 12px;">
                Configuration contract for connecting to the Flask / RAG backend service.
              </p>
              <div class="mb-3">
                <label class="form-label" style="font-size: 12px; font-weight: 600;">API Base Endpoint</label>
                <input type="text" class="form-control" value="http://localhost:5000/api/v1" placeholder="/api">
                <div class="form-text" style="font-size: 11px;">Current mode: Client-side Mock Store with localStorage persistence.</div>
              </div>
              <div class="mb-3">
                <label class="form-label" style="font-size: 12px; font-weight: 600;">Vector Embedding Model Target</label>
                <input type="text" class="form-control" value="text-embedding-3-small (Simulated)" readonly>
              </div>
            </div>
          </div>

          <!-- Right: Demo Reset & Danger Zone -->
          <div class="col-12 col-lg-5">
            <div class="cos-card p-4 bg-white mb-4 border-warning" style="border-top: 3px solid #f59e0b !important;">
              <div class="fw-bold fs-6 text-dark mb-2"><i class="bi bi-arrow-counterclockwise text-warning me-2"></i>Reset Synthetic Demo State</div>
              <p style="font-size: 12px; color: var(--text-secondary); line-height: 1.5;">
                ContinuityOS stores modifications (approvals, new claims, simulated checklist steps) in your browser's localStorage. If you wish to restart the demo scenario from pristine initial state:
              </p>
              <button class="cos-btn cos-btn-secondary w-100 mt-2" id="btn-reset-demo-data">
                <i class="bi bi-arrow-repeat me-1"></i> Reset to Factory Demo Data
              </button>
            </div>

            <!-- About ContinuityOS -->
            <div class="cos-card p-4 bg-white" style="font-size: 12px;">
              <div class="fw-bold fs-6 text-dark mb-2"><i class="bi bi-info-circle text-primary me-2"></i>About ContinuityOS</div>
              <p class="text-secondary mb-2">
                <strong>ContinuityOS v0.1 DEMO</strong> — AI-Powered Knowledge Continuity, Organisational Intelligence & Secure Handover Platform.
              </p>
              <ul class="ps-3 text-muted mb-0">
                <li>Permission-aware knowledge graph</li>
                <li>6-state uncertainty ledger</li>
                <li>Predictive departure blast radius modeling</li>
                <li>Guided AI transition debriefing</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    `;

    const btnReset = container.querySelector('#btn-reset-demo-data');
    if (btnReset) {
      btnReset.addEventListener('click', () => {
        if (confirm('Are you sure you want to reset all demo data? This will restore initial synthetic records.')) {
          localStorage.clear();
          initializeStore();
          alert('Demo data reset successfully! Reloading...');
          window.location.hash = '#/overview';
          window.location.reload();
        }
      });
    }
  }

  render();
}
