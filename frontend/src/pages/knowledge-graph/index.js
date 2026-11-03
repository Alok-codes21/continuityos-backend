/**
 * ContinuityOS — Knowledge Graph & Project Intelligence Page
 * Interactive graph visualization mapping people, components, decisions, bugs, and tasks.
 */

import {
  getTeamMembers,
  getComponents,
  getTasks,
  getDecisions,
  getBugs,
} from '../../services/mock-api.js';

export default async function renderPage(container) {
  const [teamMembers, components, tasks, decisions, bugs] = await Promise.all([
    getTeamMembers(),
    getComponents(),
    getTasks(),
    getDecisions(),
    getBugs(),
  ]);

  // Filter state
  let filterType = 'all'; // 'all', 'person', 'component', 'decision', 'task', 'bug'
  let searchQuery = '';
  let selectedNode = null;
  let zoomLevel = 1;

  // Build Graph Nodes & Edges
  const nodes = [
    // People
    ...teamMembers.map(m => ({
      id: m.id,
      label: m.name,
      sublabel: m.role,
      type: 'person',
      icon: 'bi-person-fill',
      color: m.status === 'departing' ? '#dc2626' : '#7c3aed',
      details: m,
      x: m.id === 'tm-1' ? 400 : m.id === 'tm-2' ? 200 : m.id === 'tm-3' ? 600 : m.id === 'tm-4' ? 400 : 700,
      y: m.id === 'tm-1' ? 220 : m.id === 'tm-2' ? 320 : m.id === 'tm-3' ? 120 : m.id === 'tm-4' ? 440 : 360,
    })),
    // Components
    ...components.map(c => ({
      id: c.id,
      label: c.name,
      sublabel: c.type,
      type: 'component',
      icon: 'bi-box-seam',
      color: c.risk === 'critical' ? '#ef4444' : c.risk === 'high' ? '#f59e0b' : '#0d9488',
      details: c,
      x: c.id === 'data-pipeline' ? 250 : c.id === 'event-bus' ? 520 : c.id === 'auth-service' ? 360 : c.id === 'dashboard-ui' ? 120 : 660,
      y: c.id === 'data-pipeline' ? 160 : c.id === 'event-bus' ? 220 : c.id === 'auth-service' ? 80 : c.id === 'dashboard-ui' ? 240 : 220,
    })),
    // Key Decisions
    ...decisions.slice(0, 3).map(d => ({
      id: d.id,
      label: d.id.toUpperCase(),
      sublabel: d.title,
      type: 'decision',
      icon: 'bi-journal-check',
      color: '#4f46e5',
      details: d,
      x: d.id === 'dec-001' ? 620 : d.id === 'dec-002' ? 250 : 420,
      y: d.id === 'dec-001' ? 340 : d.id === 'dec-002' ? 20 : 20,
    })),
    // Bugs
    ...bugs.map(b => ({
      id: b.id,
      label: b.id.toUpperCase(),
      sublabel: b.title,
      type: 'bug',
      icon: 'bi-bug-fill',
      color: '#e11d48',
      details: b,
      x: b.id === 'bug-001' ? 150 : b.id === 'bug-002' ? 450 : 160,
      y: b.id === 'bug-001' ? 80 : b.id === 'bug-002' ? 340 : 380,
    })),
  ];

  // Edges connecting items
  const edges = [
    { from: 'tm-1', to: 'data-pipeline', label: 'Maintains' },
    { from: 'tm-1', to: 'event-bus', label: 'Sole Owner' },
    { from: 'tm-1', to: 'auth-service', label: 'Maintains' },
    { from: 'tm-1', to: 'dec-001', label: 'Authored' },
    { from: 'tm-1', to: 'dec-003', label: 'Authored' },
    { from: 'tm-1', to: 'bug-001', label: 'Assigned' },
    { from: 'tm-1', to: 'bug-002', label: 'Assigned' },
    { from: 'tm-4', to: 'data-pipeline', label: 'Target Successor', dashed: true },
    { from: 'tm-4', to: 'event-bus', label: 'Target Successor', dashed: true },
    { from: 'data-pipeline', to: 'event-bus', label: 'Streams to' },
    { from: 'auth-service', to: 'event-bus', label: 'Publishes to' },
    { from: 'tm-2', to: 'dashboard-ui', label: 'Maintains' },
    { from: 'dashboard-ui', to: 'auth-service', label: 'Consumes' },
    { from: 'tm-3', to: 'infrastructure', label: 'Maintains' },
    { from: 'dec-001', to: 'event-bus', label: 'Governs' },
  ];

  function render() {
    // Filter nodes
    const filteredNodes = nodes.filter(n => {
      if (filterType !== 'all' && n.type !== filterType) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        return n.label.toLowerCase().includes(q) || n.sublabel.toLowerCase().includes(q);
      }
      return true;
    });

    const activeNodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredEdges = edges.filter(e => activeNodeIds.has(e.from) && activeNodeIds.has(e.to));

    container.innerHTML = `
      <div class="knowledge-graph-page">
        <!-- ── Header ──────────────────────────────────────────────── -->
        <div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
          <div>
            <div class="d-flex align-items-center gap-2">
              <h1 class="page-title m-0" style="font-size: 20px; font-weight: 800;">Project Intelligence & Knowledge Graph</h1>
              <span class="badge bg-secondary-subtle text-secondary border px-2 py-1" style="font-size: 11px;">
                <i class="bi bi-diagram-3 me-1"></i>Cross-Entity Topology
              </span>
            </div>
            <p class="page-subtitle m-0 mt-1" style="font-size: 13px; color: var(--text-secondary);">
              Interactive relationship network connecting people, components, architecture decisions, and active defects.
            </p>
          </div>
          <div class="d-flex align-items-center gap-2">
            <button class="cos-btn cos-btn-secondary" id="btn-reset-view">
              <i class="bi bi-aspect-ratio"></i> Reset View
            </button>
            <button class="cos-btn cos-btn-primary" id="btn-export-graph">
              <i class="bi bi-download"></i> Export Topology
            </button>
          </div>
        </div>

        <!-- ── Filter & Search Toolbar ──────────────────────────────── -->
        <div class="cos-card mb-3 p-2 d-flex align-items-center justify-content-between flex-wrap gap-2 bg-white">
          <div class="d-flex align-items-center gap-2 flex-wrap">
            <span style="font-size: 11px; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">Filter Nodes:</span>
            <button class="cos-btn ${filterType === 'all' ? 'cos-btn-primary' : 'cos-btn-ghost'} btn-sm filter-node-btn" data-type="all">All (${nodes.length})</button>
            <button class="cos-btn ${filterType === 'person' ? 'cos-btn-primary' : 'cos-btn-ghost'} btn-sm filter-node-btn" data-type="person"><i class="bi bi-people me-1"></i> People</button>
            <button class="cos-btn ${filterType === 'component' ? 'cos-btn-primary' : 'cos-btn-ghost'} btn-sm filter-node-btn" data-type="component"><i class="bi bi-boxes me-1"></i> Components</button>
            <button class="cos-btn ${filterType === 'decision' ? 'cos-btn-primary' : 'cos-btn-ghost'} btn-sm filter-node-btn" data-type="decision"><i class="bi bi-journal-text me-1"></i> Decisions</button>
            <button class="cos-btn ${filterType === 'bug' ? 'cos-btn-primary' : 'cos-btn-ghost'} btn-sm filter-node-btn" data-type="bug"><i class="bi bi-bug me-1"></i> Bugs</button>
          </div>

          <div class="d-flex align-items-center gap-2">
            <div class="input-group input-group-sm" style="width: 220px;">
              <span class="input-group-text bg-light border-end-0"><i class="bi bi-search text-muted"></i></span>
              <input type="text" class="form-control border-start-0" id="graph-search" placeholder="Search entity..." value="${searchQuery}">
            </div>
            <div class="btn-group btn-group-sm">
              <button class="btn btn-outline-secondary" id="btn-zoom-in" title="Zoom In"><i class="bi bi-plus-lg"></i></button>
              <button class="btn btn-outline-secondary" id="btn-zoom-out" title="Zoom Out"><i class="bi bi-dash-lg"></i></button>
            </div>
          </div>
        </div>

        <!-- ── Interactive Canvas & Detail Panel ──────────────────────── -->
        <div class="row g-3">
          <!-- Graph Canvas Container -->
          <div class="col-12 ${selectedNode ? 'col-lg-8' : 'col-lg-12'}">
            <div class="cos-card position-relative overflow-hidden" style="background: #ffffff; height: 580px; border: 1px solid var(--border);">
              <!-- Legend Overlay -->
              <div class="position-absolute top-0 start-0 m-3 p-2 rounded bg-white border shadow-sm d-flex flex-column gap-1" style="z-index: 10; font-size: 11px; opacity: 0.95;">
                <div class="fw-bold text-dark mb-1">Entity Legend</div>
                <div class="d-flex align-items-center gap-2"><span style="width: 10px; height: 10px; border-radius: 50%; background: #dc2626;"></span> Departing Lead</div>
                <div class="d-flex align-items-center gap-2"><span style="width: 10px; height: 10px; border-radius: 50%; background: #7c3aed;"></span> Team Member</div>
                <div class="d-flex align-items-center gap-2"><span style="width: 10px; height: 10px; border-radius: 2px; background: #0d9488;"></span> Microservice</div>
                <div class="d-flex align-items-center gap-2"><span style="width: 10px; height: 10px; border-radius: 2px; background: #4f46e5;"></span> Architecture Decision (ADR)</div>
                <div class="d-flex align-items-center gap-2"><span style="width: 10px; height: 10px; border-radius: 2px; background: #e11d48;"></span> Unresolved Bug</div>
              </div>

              <!-- SVG Graph Surface -->
              <svg id="graph-svg" width="100%" height="100%" viewBox="0 0 800 500" style="cursor: grab;">
                <defs>
                  <marker id="arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8" />
                  </marker>
                </defs>

                <!-- Grid Background -->
                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#f1f5f9" stroke-width="1"/>
                </pattern>
                <rect width="100%" height="100%" fill="url(#grid)" />

                <!-- Edges -->
                <g class="edges">
                  ${filteredEdges.map(e => {
                    const fromNode = nodes.find(n => n.id === e.from);
                    const toNode = nodes.find(n => n.id === e.to);
                    if (!fromNode || !toNode) return '';
                    return `
                      <line
                        x1="${fromNode.x}"
                        y1="${fromNode.y}"
                        x2="${toNode.x}"
                        y2="${toNode.y}"
                        stroke="${e.dashed ? '#a855f7' : '#cbd5e1'}"
                        stroke-width="${e.dashed ? '2' : '1.5'}"
                        stroke-dasharray="${e.dashed ? '4,4' : 'none'}"
                        marker-end="url(#arrow)"
                      />
                      <text
                        x="${(fromNode.x + toNode.x) / 2}"
                        y="${(fromNode.y + toNode.y) / 2 - 4}"
                        font-size="9"
                        fill="#64748b"
                        text-anchor="middle"
                        style="background: #ffffff; font-weight: 500;"
                      >
                        ${e.label}
                      </text>
                    `;
                  }).join('')}
                </g>

                <!-- Nodes -->
                <g class="nodes">
                  ${filteredNodes.map(n => {
                    const isSelected = selectedNode && selectedNode.id === n.id;
                    return `
                      <g
                        class="graph-node-group"
                        data-id="${n.id}"
                        style="cursor: pointer;"
                        transform="translate(${n.x}, ${n.y})"
                      >
                        <!-- Node Circle/Box -->
                        <circle
                          r="${isSelected ? '24' : '20'}"
                          fill="${n.color}"
                          stroke="#ffffff"
                          stroke-width="${isSelected ? '4' : '2'}"
                          filter="drop-shadow(0px 2px 4px rgba(0,0,0,0.15))"
                        />
                        <!-- Inner Icon/Text -->
                        <text
                          text-anchor="middle"
                          dy="4"
                          font-size="12"
                          fill="#ffffff"
                          font-family="bootstrap-icons"
                        >
                          ${n.type === 'person' ? '&#xF4DA;' : n.type === 'component' ? '&#xF1C9;' : n.type === 'decision' ? '&#xF452;' : '&#xF200;'}
                        </text>
                        <!-- Label Below -->
                        <text
                          text-anchor="middle"
                          y="34"
                          font-size="11"
                          font-weight="700"
                          fill="#1e293b"
                        >
                          ${n.label}
                        </text>
                        <text
                          text-anchor="middle"
                          y="46"
                          font-size="9"
                          fill="#64748b"
                        >
                          ${n.sublabel ? (n.sublabel.length > 20 ? n.sublabel.substring(0, 18) + '...' : n.sublabel) : ''}
                        </text>
                      </g>
                    `;
                  }).join('')}
                </g>
              </svg>
            </div>
          </div>

          <!-- Node Detail Panel (Sidebar when node clicked) -->
          ${selectedNode ? `
            <div class="col-12 col-lg-4">
              <div class="cos-card h-100 p-4 bg-white" style="border-left: 3px solid ${selectedNode.color};">
                <div class="d-flex align-items-center justify-content-between mb-3">
                  <span class="badge" style="background: ${selectedNode.color}; color: #fff; font-size: 10px; text-transform: uppercase;">
                    ${selectedNode.type}
                  </span>
                  <button class="btn-close btn-sm" id="btn-close-node-detail"></button>
                </div>

                <h3 class="fw-bold fs-5 text-dark mb-1">${selectedNode.label}</h3>
                <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 16px;">${selectedNode.sublabel}</div>

                <div class="p-3 bg-light rounded border mb-3" style="font-size: 12px;">
                  <div class="fw-bold text-dark mb-1">Entity Details</div>
                  ${selectedNode.type === 'person' ? `
                    <div>Email: <strong>${selectedNode.details.email}</strong></div>
                    <div>Status: <span class="badge ${selectedNode.details.status === 'departing' ? 'bg-danger' : 'bg-success'}">${selectedNode.details.status}</span></div>
                    <div>Departure Date: <strong>${selectedNode.details.departureDate || 'N/A'}</strong></div>
                    <div class="mt-2">Skills: ${(selectedNode.details.skills || []).join(', ')}</div>
                  ` : selectedNode.type === 'component' ? `
                    <div>Language: <strong>${selectedNode.details.language || 'Config'}</strong></div>
                    <div>Risk: <span class="badge bg-danger">${selectedNode.details.risk}</span></div>
                    <div>Documentation: <strong>${selectedNode.details.documentation}</strong></div>
                    <div class="mt-2 text-muted">${selectedNode.details.description}</div>
                  ` : `
                    <div class="text-secondary">${selectedNode.details.description || selectedNode.details.rationale}</div>
                  `}
                </div>

                <!-- Connected Entities -->
                <div class="mb-3">
                  <div class="fw-bold mb-2" style="font-size: 12px; color: var(--text-secondary); text-transform: uppercase;">Connected Relationships</div>
                  <div class="list-group list-group-flush border rounded" style="font-size: 11px;">
                    ${edges.filter(e => e.from === selectedNode.id || e.to === selectedNode.id).map(e => {
                      const otherId = e.from === selectedNode.id ? e.to : e.from;
                      const otherNode = nodes.find(n => n.id === otherId);
                      return `
                        <div class="list-group-item p-2 d-flex align-items-center justify-content-between">
                          <span>${e.label}: <strong>${otherNode ? otherNode.label : otherId}</strong></span>
                          <span class="badge bg-light text-muted border">${otherNode ? otherNode.type : ''}</span>
                        </div>
                      `;
                    }).join('')}
                  </div>
                </div>

                <div class="d-grid gap-2">
                  <button class="cos-btn cos-btn-primary btn-sm" onclick="window.location.hash='#/uncertainty-ledger'">
                    <i class="bi bi-journal-text me-1"></i> View Related Ledger Claims
                  </button>
                  ${selectedNode.type === 'person' ? `
                    <button class="cos-btn cos-btn-secondary btn-sm" onclick="window.location.hash='#/impact-simulator'">
                      <i class="bi bi-person-dash me-1"></i> Simulate Departure Impact
                    </button>
                  ` : ''}
                </div>
              </div>
            </div>
          ` : ''}
        </div>
      </div>
    `;

    // ── Attach Event Listeners ─────────────────────────────────────
    container.querySelectorAll('.filter-node-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        filterType = btn.getAttribute('data-type');
        render();
      });
    });

    const searchInput = container.querySelector('#graph-search');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value;
        render();
      });
    }

    container.querySelectorAll('.graph-node-group').forEach(el => {
      el.addEventListener('click', () => {
        const id = el.getAttribute('data-id');
        selectedNode = nodes.find(n => n.id === id) || null;
        render();
      });
    });

    const btnCloseNode = container.querySelector('#btn-close-node-detail');
    if (btnCloseNode) {
      btnCloseNode.addEventListener('click', () => {
        selectedNode = null;
        render();
      });
    }

    const btnReset = container.querySelector('#btn-reset-view');
    if (btnReset) {
      btnReset.addEventListener('click', () => {
        filterType = 'all';
        searchQuery = '';
        selectedNode = null;
        render();
      });
    }

    const btnExport = container.querySelector('#btn-export-graph');
    if (btnExport) {
      btnExport.addEventListener('click', () => {
        alert('Exporting graph topology as SVG/JSON schema representation.');
      });
    }
  }

  render();
}
