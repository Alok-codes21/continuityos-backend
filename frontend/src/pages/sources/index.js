/**
 * ContinuityOS — Sources & Multi-Source Ingestion Page
 * Connectors, selective scoping permissions, local file validation, and audit trail.
 */

import {
  getSources,
  getDocuments,
  connectSource,
  disconnectSource,
} from '../../services/mock-api.js';
import { MockStore } from '../../data/mock-store.js';

export default async function renderPage(container) {
  let [sources, documents] = await Promise.all([
    getSources(),
    getDocuments(),
  ]);

  let activeTab = 'connectors'; // 'connectors', 'upload', 'history'
  let selectedSourceForModal = null;
  let showRevokeModal = false;
  let showPermissionModal = false;
  let localUploadedFiles = MockStore.get('sources_local_uploads', [
    { name: 'architecture_spec_v2.3.pdf', size: '2.4 MB', type: 'application/pdf', status: 'staged', uploadedAt: '10 mins ago' },
    { name: 'kafka_broker_env_notes.txt', size: '14 KB', type: 'text/plain', status: 'staged', uploadedAt: '25 mins ago' }
  ]);

  function render() {
    container.innerHTML = `
      <div class="sources-page">
        <!-- ── Header ──────────────────────────────────────────────── -->
        <div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
          <div>
            <div class="d-flex align-items-center gap-2">
              <h1 class="page-title m-0" style="font-size: 20px; font-weight: 800;">Multi-Source Ingestion & Permissions</h1>
              <span class="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1" style="font-size: 11px;">
                <i class="bi bi-shield-check me-1"></i>Granular Source Scoping
              </span>
            </div>
            <p class="page-subtitle m-0 mt-1" style="font-size: 13px; color: var(--text-secondary);">
              Connect enterprise repositories, project management boards, and documentation streams with zero-retention privacy controls.
            </p>
          </div>
          <div class="d-flex align-items-center gap-2">
            <button class="cos-btn ${activeTab === 'connectors' ? 'cos-btn-primary' : 'cos-btn-secondary'} btn-sm tab-btn" data-tab="connectors">
              <i class="bi bi-diagram-3 me-1"></i> Enterprise Connectors (${sources.length})
            </button>
            <button class="cos-btn ${activeTab === 'upload' ? 'cos-btn-primary' : 'cos-btn-secondary'} btn-sm tab-btn" data-tab="upload">
              <i class="bi bi-cloud-arrow-up me-1"></i> Document Upload
            </button>
            <button class="cos-btn ${activeTab === 'history' ? 'cos-btn-primary' : 'cos-btn-secondary'} btn-sm tab-btn" data-tab="history">
              <i class="bi bi-clock-history me-1"></i> Ingestion History
            </button>
          </div>
        </div>

        <!-- ── Explicit Demo Environment Notice ──────────────────────── -->
        <div class="alert alert-light border p-3 mb-4 d-flex align-items-center justify-content-between flex-wrap gap-2" style="font-size: 12px; background: #fafaf9;">
          <div class="d-flex align-items-center gap-2">
            <i class="bi bi-info-circle-fill text-primary fs-5"></i>
            <div>
              <strong>ContinuityOS Demo Environment:</strong> Integration actions use local synthetic state simulation. No live OAuth tokens or external company repositories are connected without backend credential configuration.
            </div>
          </div>
          <span class="badge bg-secondary-subtle text-secondary">Local Simulated Connector</span>
        </div>

        <!-- ── TAB 1: Enterprise Connectors ───────────────────────────── -->
        ${activeTab === 'connectors' ? `
          <div class="row g-3 mb-4">
            ${sources.map(s => `
              <div class="col-12 col-md-6 col-xl-4">
                <div class="cos-card h-100 p-4 bg-white d-flex flex-column justify-content-between">
                  <div>
                    <div class="d-flex align-items-start justify-content-between mb-3">
                      <div class="d-flex align-items-center gap-3">
                        <div class="source-icon-container" style="width: 42px; height: 42px; border-radius: 8px; background: var(--main-bg); border: 1px solid var(--border); display: flex; align-items: center; justify-content: center; font-size: 20px; color: var(--primary);">
                          <i class="bi ${s.icon || 'bi-database'}"></i>
                        </div>
                        <div>
                          <div class="fw-bold fs-6 text-dark">${s.name}</div>
                          <div style="font-size: 11px; color: var(--text-muted);">${s.type || 'Enterprise Tool'}</div>
                        </div>
                      </div>
                      <div>
                        ${s.status === 'connected' 
                          ? '<span class="badge bg-success-subtle text-success border border-success-subtle"><i class="bi bi-check-circle-fill me-1"></i>Connected</span>'
                          : s.status === 'pending'
                          ? '<span class="badge bg-warning-subtle text-warning border"><i class="bi bi-hourglass-split me-1"></i>Syncing</span>'
                          : '<span class="badge bg-light text-muted border">Disconnected</span>'
                        }
                      </div>
                    </div>

                    <div class="p-2 bg-light rounded border mb-3" style="font-size: 11px;">
                      <div class="d-flex justify-content-between mb-1">
                        <span class="text-muted">Indexed Artifacts:</span>
                        <strong class="text-dark">${s.documentsIndexed || 0} records</strong>
                      </div>
                      <div class="d-flex justify-content-between">
                        <span class="text-muted">Last Audit Sync:</span>
                        <span class="text-dark">${s.lastSync ? new Date(s.lastSync).toLocaleTimeString() : 'Never'}</span>
                      </div>
                    </div>

                    <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 12px;">
                      <i class="bi bi-shield-check text-success me-1"></i>
                      ${s.status === 'connected' ? 'Granular channel/repo access authorized' : 'Access authorization required'}
                    </div>
                  </div>

                  <div class="pt-3 border-top d-flex align-items-center justify-content-between gap-2">
                    ${s.status === 'connected' ? `
                      <button class="cos-btn cos-btn-ghost btn-sm text-secondary btn-configure-perms" data-id="${s.id}">
                        <i class="bi bi-sliders me-1"></i> Permissions
                      </button>
                      <button class="cos-btn cos-btn-danger btn-sm btn-revoke-source" data-id="${s.id}">
                        Revoke Access
                      </button>
                    ` : `
                      <button class="cos-btn cos-btn-primary btn-sm w-100 btn-connect-source" data-id="${s.id}">
                        <i class="bi bi-link-45deg me-1"></i> Authorize Integration
                      </button>
                    `}
                  </div>
                </div>
              </div>
            `).join('')}

            <!-- Add New Custom Connector Card -->
            <div class="col-12 col-md-6 col-xl-4">
              <div class="cos-card h-100 p-4 border-dashed d-flex flex-column align-items-center justify-content-center text-center bg-light" style="border: 2px dashed var(--border) !important;">
                <i class="bi bi-plus-circle text-primary fs-2 mb-2"></i>
                <div class="fw-bold text-dark fs-6">Custom Webhook / REST Source</div>
                <p class="text-muted mt-1 mb-3" style="font-size: 12px;">
                  Connect internal Notion, Linear, or custom documentation endpoints via signed webhooks.
                </p>
                <button class="cos-btn cos-btn-secondary btn-sm" onclick="alert('Custom webhook configuration wizard available in Admin settings.')">
                  Configure Endpoint
                </button>
              </div>
            </div>
          </div>
        ` : ''}

        <!-- ── TAB 2: Document Upload ────────────────────────────────── -->
        ${activeTab === 'upload' ? `
          <div class="row g-4 mb-4">
            <div class="col-12 col-lg-7">
              <div class="cos-card p-4 bg-white">
                <div class="fw-bold fs-6 text-dark mb-1">Local Document Ingestion</div>
                <p class="text-muted mb-3" style="font-size: 12px;">
                  Upload architecture guides, meeting transcripts, or code runbooks (PDF, DOCX, TXT, CSV, MD).
                </p>

                <!-- Drag & Drop Zone -->
                <div class="p-5 text-center rounded border-dashed mb-3" id="drop-zone" style="border: 2px dashed var(--primary); background: #faf5ff; cursor: pointer;">
                  <i class="bi bi-cloud-arrow-up text-primary fs-1 mb-2"></i>
                  <div class="fw-bold text-dark fs-6">Drag & drop files here, or click to browse</div>
                  <div class="text-muted mt-1" style="font-size: 11px;">Supported formats: PDF, DOCX, TXT, CSV, Markdown (Max 25 MB)</div>
                  <input type="file" id="file-input" class="d-none" multiple accept=".pdf,.docx,.txt,.csv,.md">
                </div>

                <div class="alert alert-info p-2 mb-0" style="font-size: 11px;">
                  <i class="bi bi-shield-lock me-1"></i>
                  <strong>Zero-Retention Rule:</strong> Uploaded documents are parsed locally for synthetic schema validation. Files are not sent to third-party endpoints.
                </div>
              </div>
            </div>

            <div class="col-12 col-lg-5">
              <div class="cos-card p-4 bg-white h-100">
                <div class="d-flex align-items-center justify-content-between mb-3">
                  <div class="fw-bold fs-6 text-dark">Staged Files for Processing</div>
                  <span class="badge bg-light text-dark border">${localUploadedFiles.length} files</span>
                </div>

                <div class="list-group list-group-flush border rounded mb-3">
                  ${localUploadedFiles.map(f => `
                    <div class="list-group-item p-3 d-flex align-items-center justify-content-between">
                      <div class="d-flex align-items-center gap-2">
                        <i class="bi bi-file-earmark-code text-primary fs-5"></i>
                        <div>
                          <div class="fw-bold" style="font-size: 12px;">${f.name}</div>
                          <div style="font-size: 10px; color: var(--text-muted);">${f.size} · ${f.uploadedAt}</div>
                        </div>
                      </div>
                      <span class="badge bg-warning-subtle text-warning" style="font-size: 10px;">Staged</span>
                    </div>
                  `).join('')}
                </div>

                <button class="cos-btn cos-btn-primary w-100" id="btn-process-staged">
                  <i class="bi bi-cpu me-1"></i> Extract Knowledge Entities (${localUploadedFiles.length})
                </button>
              </div>
            </div>
          </div>
        ` : ''}

        <!-- ── TAB 3: Ingestion History ──────────────────────────────── -->
        ${activeTab === 'history' ? `
          <div class="cos-card mb-4">
            <div class="cos-card-header">
              <div>
                <div class="cos-card-title"><i class="bi bi-clock-history text-secondary me-2"></i>Ingestion Audit Log & Sync Activity</div>
                <div class="cos-card-subtitle">Real-time status of document chunking and vector index jobs</div>
              </div>
              <button class="cos-btn cos-btn-secondary btn-sm" id="btn-refresh-history">
                <i class="bi bi-arrow-clockwise"></i> Refresh Status
              </button>
            </div>
            <div class="table-responsive">
              <table class="table cos-table mb-0 align-middle">
                <thead>
                  <tr>
                    <th>Document / Source</th>
                    <th>Source Type</th>
                    <th>Chunk Count</th>
                    <th>Status</th>
                    <th>Extracted At</th>
                    <th style="text-align: right;">Action</th>
                  </tr>
                </thead>
                <tbody>
                  ${documents.map(d => `
                    <tr>
                      <td>
                        <div class="fw-bold" style="font-size: 12px;">${d.title}</div>
                        <div style="font-size: 10px; color: var(--text-muted);">Size: ${d.size} · ID: <code>${d.id}</code></div>
                      </td>
                      <td>
                        <span class="badge bg-light text-secondary border text-uppercase" style="font-size: 10px;">${d.source}</span>
                      </td>
                      <td style="font-size: 12px;">
                        ${Math.floor(Math.random() * 20) + 4} chunks
                      </td>
                      <td>
                        ${d.status === 'verified'
                          ? '<span class="badge bg-success-subtle text-success"><i class="bi bi-check-circle me-1"></i>Indexed</span>'
                          : d.status === 'conflicting'
                          ? '<span class="badge bg-danger-subtle text-danger"><i class="bi bi-exclamation-triangle me-1"></i>Conflict</span>'
                          : '<span class="badge bg-warning-subtle text-warning">Inferred Chunks</span>'
                        }
                      </td>
                      <td style="font-size: 11px; color: var(--text-muted);">
                        ${d.uploadedAt || 'Oct 28, 2026'}
                      </td>
                      <td style="text-align: right;">
                        <button class="cos-btn cos-btn-ghost btn-xs text-primary" onclick="window.location.hash='#/uncertainty-ledger'">
                          View in Ledger
                        </button>
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        ` : ''}

        <!-- ── Revoke Confirmation Modal ────────────────────────────── -->
        ${showRevokeModal && selectedSourceForModal ? `
          <div class="cos-modal-overlay">
            <div class="cos-modal" style="max-width: 500px;">
              <div class="cos-modal-header d-flex justify-content-between align-items-center">
                <div class="cos-modal-title text-danger"><i class="bi bi-exclamation-triangle me-2"></i>Revoke Access & Purge Tokens</div>
                <button class="btn-close" id="btn-close-revoke-modal"></button>
              </div>
              <div class="cos-modal-body p-4">
                <p style="font-size: 13px;">
                  Are you sure you want to revoke ContinuityOS access to <strong>${selectedSourceForModal.name}</strong>?
                </p>
                <div class="alert alert-danger p-2" style="font-size: 11px;">
                  All active OAuth credentials will be terminated and incremental ingestion syncs will pause immediately.
                </div>
              </div>
              <div class="cos-modal-footer d-flex justify-content-between">
                <button class="cos-btn cos-btn-ghost" id="btn-cancel-revoke">Cancel</button>
                <button class="cos-btn cos-btn-danger" id="btn-confirm-revoke">Confirm Revocation</button>
              </div>
            </div>
          </div>
        ` : ''}

        <!-- ── Granular Permission Selection Modal ──────────────────── -->
        ${showPermissionModal && selectedSourceForModal ? `
          <div class="cos-modal-overlay">
            <div class="cos-modal" style="max-width: 600px;">
              <div class="cos-modal-header d-flex justify-content-between align-items-center">
                <div class="cos-modal-title"><i class="bi bi-sliders me-2"></i>Configure Selective Access: ${selectedSourceForModal.name}</div>
                <button class="btn-close" id="btn-close-perm-modal"></button>
              </div>
              <div class="cos-modal-body p-4">
                <p class="text-muted" style="font-size: 12px;">
                  Select exactly which repositories, channels, or document paths ContinuityOS is allowed to read.
                </p>

                <div class="list-group mb-3" style="font-size: 12px;">
                  <label class="list-group-item d-flex align-items-center gap-2">
                    <input class="form-check-input me-1" type="checkbox" checked>
                    <div>
                      <div class="fw-bold">novatech/data-pipeline</div>
                      <div class="text-muted" style="font-size: 10px;">Primary ETL workers and ingestion scripts</div>
                    </div>
                  </label>
                  <label class="list-group-item d-flex align-items-center gap-2">
                    <input class="form-check-input me-1" type="checkbox" checked>
                    <div>
                      <div class="fw-bold">novatech/infra-kafka</div>
                      <div class="text-muted" style="font-size: 10px;">Terraform and Kafka broker topology</div>
                    </div>
                  </label>
                  <label class="list-group-item d-flex align-items-center gap-2">
                    <input class="form-check-input me-1" type="checkbox">
                    <div>
                      <div class="fw-bold">novatech/finance-billing (Restricted)</div>
                      <div class="text-muted" style="font-size: 10px;">Sensitive client billing contracts — excluded by default</div>
                    </div>
                  </label>
                </div>
              </div>
              <div class="cos-modal-footer d-flex justify-content-between">
                <button class="cos-btn cos-btn-ghost" id="btn-cancel-perm">Cancel</button>
                <button class="cos-btn cos-btn-primary" id="btn-save-perm">Save Scoping Rules</button>
              </div>
            </div>
          </div>
        ` : ''}
      </div>
    `;

    // ── Attach Event Listeners ─────────────────────────────────────
    container.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        activeTab = btn.getAttribute('data-tab');
        render();
      });
    });

    // Connect source
    container.querySelectorAll('.btn-connect-source').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> Authorizing...`;
        await connectSource(id);
        sources = await getSources();
        render();
      });
    });

    // Revoke source modal trigger
    container.querySelectorAll('.btn-revoke-source').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        selectedSourceForModal = sources.find(s => s.id === id);
        showRevokeModal = true;
        render();
      });
    });

    // Permissions modal trigger
    container.querySelectorAll('.btn-configure-perms').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.getAttribute('data-id');
        selectedSourceForModal = sources.find(s => s.id === id);
        showPermissionModal = true;
        render();
      });
    });

    // Revoke handlers
    const btnCloseRevoke = container.querySelector('#btn-close-revoke-modal');
    const btnCancelRevoke = container.querySelector('#btn-cancel-revoke');
    const btnConfirmRevoke = container.querySelector('#btn-confirm-revoke');
    if (btnCloseRevoke) btnCloseRevoke.addEventListener('click', () => { showRevokeModal = false; render(); });
    if (btnCancelRevoke) btnCancelRevoke.addEventListener('click', () => { showRevokeModal = false; render(); });
    if (btnConfirmRevoke && selectedSourceForModal) {
      btnConfirmRevoke.addEventListener('click', async () => {
        await disconnectSource(selectedSourceForModal.id);
        showRevokeModal = false;
        sources = await getSources();
        render();
      });
    }

    // Permission handlers
    const btnClosePerm = container.querySelector('#btn-close-perm-modal');
    const btnCancelPerm = container.querySelector('#btn-cancel-perm');
    const btnSavePerm = container.querySelector('#btn-save-perm');
    if (btnClosePerm) btnClosePerm.addEventListener('click', () => { showPermissionModal = false; render(); });
    if (btnCancelPerm) btnCancelPerm.addEventListener('click', () => { showPermissionModal = false; render(); });
    if (btnSavePerm) {
      btnSavePerm.addEventListener('click', () => {
        showPermissionModal = false;
        alert('Selective permissions updated and applied to ingestion crawler.');
        render();
      });
    }

    // Drop zone
    const dropZone = container.querySelector('#drop-zone');
    const fileInput = container.querySelector('#file-input');
    if (dropZone && fileInput) {
      dropZone.addEventListener('click', () => fileInput.click());
      fileInput.addEventListener('change', (e) => {
        const files = Array.from(e.target.files);
        files.forEach(f => {
          localUploadedFiles.push({
            name: f.name,
            size: `${(f.size / (1024 * 1024)).toFixed(1)} MB`,
            type: f.type || 'text/plain',
            status: 'staged',
            uploadedAt: 'Just now',
          });
        });
        MockStore.set('sources_local_uploads', localUploadedFiles);
        render();
      });
    }

    const btnProcessStaged = container.querySelector('#btn-process-staged');
    if (btnProcessStaged) {
      btnProcessStaged.addEventListener('click', () => {
        alert('Staged documents processed into local knowledge chunks. Claims ready for review in Uncertainty Ledger!');
        window.location.hash = '#/uncertainty-ledger';
      });
    }
  }

  render();
}
