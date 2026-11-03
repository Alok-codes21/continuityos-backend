/**
 * ContinuityOS — Sidebar Component
 */

import { MockStore } from '../data/mock-store.js';
import { navigate } from '../router.js';

// ─────────────────────────────────────────────────────────────
// NAV CONFIGURATION
// ─────────────────────────────────────────────────────────────

const NAV_SECTIONS = [
  {
    label: 'Workspace',
    items: [
      { label: 'Overview',            route: '#/overview',           icon: 'bi-grid-1x2' },
      { label: 'Knowledge Graph',     route: '#/knowledge-graph',    icon: 'bi-diagram-3' },
      { label: 'Sources',             route: '#/sources',            icon: 'bi-database' },
      { label: 'Uncertainty Ledger',  route: '#/uncertainty-ledger', icon: 'bi-journal-check' },
    ],
  },
  {
    label: 'Transitions',
    items: [
      { label: 'Impact Simulator',    route: '#/impact-simulator',   icon: 'bi-person-dash' },
      { label: 'Handover Interview',  route: '#/handover-interview', icon: 'bi-chat-square-dots' },
      { label: 'Handover Centre',     route: '#/handover-centre',    icon: 'bi-briefcase' },
      { label: 'Incoming Workspace',  route: '#/incoming-workspace', icon: 'bi-person-plus' },
      { label: 'Rehearsal',           route: '#/rehearsal',          icon: 'bi-mortarboard' },
    ],
  },
  {
    label: 'Admin',
    items: [
      { label: 'AI Assistant',        route: '#/assistant',          icon: 'bi-stars' },
      { label: 'Security & Risks',    route: '#/security',           icon: 'bi-shield-exclamation' },
      { label: 'Settings',            route: '#/settings',           icon: 'bi-gear' },
    ],
  },
];

// ─────────────────────────────────────────────────────────────
// RENDER
// ─────────────────────────────────────────────────────────────

/**
 * Render a single nav item.
 * @param {{ label: string, route: string, icon: string }} item
 * @param {string} currentHash
 * @returns {string}
 */
function renderNavItem(item, currentHash) {
  const isActive = currentHash === item.route;
  return `
    <a
      class="sidebar-nav-item${isActive ? ' active' : ''}"
      href="${item.route}"
      data-route="${item.route}"
      title="${item.label}"
    >
      <i class="bi ${item.icon} nav-icon"></i>
      <span class="nav-label">${item.label}</span>
    </a>
  `;
}

/**
 * Render a nav section.
 * @param {{ label: string, items: object[] }} section
 * @param {string} currentHash
 * @returns {string}
 */
function renderSection(section, currentHash) {
  const items = section.items.map(item => renderNavItem(item, currentHash)).join('');
  return `
    <div class="sidebar-section-label">${section.label}</div>
    ${items}
  `;
}

/**
 * Build and return the sidebar HTML string.
 * @returns {string}
 */
export function renderSidebar() {
  const currentHash = window.location.hash || '#/overview';
  const currentUser = MockStore.get('currentUser', {
    name: 'Alex Rivera',
    role: 'Senior Backend Engineer',
    avatar: 'AR',
  });

  const sections = NAV_SECTIONS.map(s => renderSection(s, currentHash)).join('<hr class="sidebar-divider">');

  return `
    <aside class="sidebar" id="sidebar" aria-label="Main navigation">
      <!-- Logo -->
      <div class="sidebar-logo" title="ContinuityOS">
        <div class="sidebar-logo-icon">
          <i class="bi bi-infinity"></i>
        </div>
        <div class="sidebar-logo-text">
          <div class="sidebar-logo-name">ContinuityOS</div>
          <div class="sidebar-logo-version">v0.1 DEMO</div>
        </div>
      </div>

      <!-- Collapse toggle -->
      <button
        class="sidebar-collapse-btn"
        id="sidebar-collapse-btn"
        title="Toggle sidebar"
        aria-label="Toggle sidebar"
      >
        <i class="bi bi-chevron-left" id="sidebar-collapse-icon"></i>
      </button>

      <!-- Nav sections -->
      <nav class="sidebar-nav" role="navigation">
        ${sections}
      </nav>

      <!-- Footer: org + user -->
      <div class="sidebar-footer">
        <div class="sidebar-org">NovaTech Engineering</div>
        <div class="sidebar-user" id="sidebar-user-btn" title="${currentUser.name}">
          <div class="sidebar-user-avatar">${currentUser.avatar || 'U'}</div>
          <div class="sidebar-user-info">
            <div class="sidebar-user-name">${currentUser.name}</div>
            <div class="sidebar-user-role">${currentUser.role}</div>
          </div>
        </div>
      </div>
    </aside>

    <!-- Mobile overlay -->
    <div class="sidebar-overlay" id="sidebar-overlay"></div>
  `;
}

// ─────────────────────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────────────────────

/**
 * Attach event listeners, restore collapsed state, set up active tracking.
 */
export function initSidebar() {
  const sidebar = document.getElementById('sidebar');
  const mainArea = document.getElementById('main-area');
  const topbar = document.getElementById('topbar-container');
  const overlay = document.getElementById('sidebar-overlay');
  const collapseBtn = document.getElementById('sidebar-collapse-btn');
  const collapseIcon = document.getElementById('sidebar-collapse-icon');

  if (!sidebar) return;

  // ── Restore collapsed state ───────────────────────────────
  const isCollapsed = MockStore.get('sidebarCollapsed', false);
  if (isCollapsed) {
    applyCollapsed(true, sidebar, mainArea, topbar, collapseIcon);
  }

  // ── Collapse toggle ───────────────────────────────────────
  collapseBtn?.addEventListener('click', () => {
    const collapsed = sidebar.classList.contains('collapsed');
    applyCollapsed(!collapsed, sidebar, mainArea, topbar, collapseIcon);
    MockStore.set('sidebarCollapsed', !collapsed);
  });

  // ── Mobile overlay close ──────────────────────────────────
  overlay?.addEventListener('click', closeMobileSidebar);

  // ── Prevent default on nav links, use router ─────────────
  sidebar.querySelectorAll('.sidebar-nav-item').forEach(el => {
    el.addEventListener('click', e => {
      e.preventDefault();
      const route = el.dataset.route;
      if (route) {
        navigate(route);
        // Mobile: close sidebar after nav
        if (window.innerWidth < 768) closeMobileSidebar();
      }
    });
  });

  // ── Active state on hash change ───────────────────────────
  window.addEventListener('hashchange', () => {
    const hash = window.location.hash || '#/overview';
    sidebar.querySelectorAll('.sidebar-nav-item').forEach(el => {
      el.classList.toggle('active', el.dataset.route === hash);
    });
  });
}

/**
 * Apply or remove collapsed state across sidebar, main area, and topbar.
 */
function applyCollapsed(collapse, sidebar, mainArea, topbar, icon) {
  sidebar.classList.toggle('collapsed', collapse);
  mainArea?.classList.toggle('sidebar-collapsed', collapse);

  // Topbar is inside topbar-container which may not exist yet; query it
  const topbarEl = document.querySelector('.topbar');
  topbarEl?.classList.toggle('sidebar-collapsed', collapse);

  if (icon) {
    icon.className = collapse ? 'bi bi-chevron-right' : 'bi bi-chevron-left';
  }
}

/**
 * Open the sidebar on mobile.
 */
export function openMobileSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  sidebar?.classList.add('mobile-open');
  overlay?.classList.add('active');
  document.body.style.overflow = 'hidden';
}

/**
 * Close the sidebar on mobile.
 */
export function closeMobileSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  sidebar?.classList.remove('mobile-open');
  overlay?.classList.remove('active');
  document.body.style.overflow = '';
}
