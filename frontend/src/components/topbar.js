/**
 * ContinuityOS — Topbar Component
 */

import { MockStore } from '../data/mock-store.js';
import { openMobileSidebar } from './sidebar.js';
import { navigate } from '../router.js';

// ─────────────────────────────────────────────────────────────
// BREADCRUMB MAP
// ─────────────────────────────────────────────────────────────

const ROUTE_META = {
  '#/overview':            { title: 'Overview',            crumbs: [] },
  '#/knowledge-graph':     { title: 'Knowledge Graph',     crumbs: ['Workspace'] },
  '#/sources':             { title: 'Sources',             crumbs: ['Workspace'] },
  '#/uncertainty-ledger':  { title: 'Uncertainty Ledger',  crumbs: ['Workspace'] },
  '#/impact-simulator':    { title: 'Impact Simulator',    crumbs: ['Transitions'] },
  '#/handover-interview':  { title: 'Handover Interview',  crumbs: ['Transitions'] },
  '#/handover-centre':     { title: 'Handover Centre',     crumbs: ['Transitions'] },
  '#/incoming-workspace':  { title: 'Incoming Workspace',  crumbs: ['Transitions'] },
  '#/rehearsal':           { title: 'Rehearsal',           crumbs: ['Transitions'] },
  '#/assistant':           { title: 'AI Assistant',        crumbs: ['Admin'] },
  '#/security':            { title: 'Security & Risks',    crumbs: ['Admin'] },
  '#/settings':            { title: 'Settings',            crumbs: ['Admin'] },
};

// ─────────────────────────────────────────────────────────────
// RENDER
// ─────────────────────────────────────────────────────────────

/**
 * Render the breadcrumb trail HTML.
 * @param {string[]} crumbs
 * @param {string} title
 * @returns {string}
 */
function renderBreadcrumbs(crumbs, title) {
  const parts = [
    `<span class="text-muted-color">Project Atlas</span>`,
    ...crumbs.map(c => `<i class="bi bi-chevron-right separator" style="font-size:9px;"></i><span>${c}</span>`),
    `<i class="bi bi-chevron-right separator" style="font-size:9px;"></i>`,
    `<span class="current">${title}</span>`,
  ];
  return parts.join('');
}

/**
 * Render the topbar HTML for the current route.
 * @param {string} [hash]
 * @returns {string}
 */
export function renderTopbar(hash) {
  const currentHash = hash || window.location.hash || '#/overview';
  const meta = ROUTE_META[currentHash] || { title: 'Page', crumbs: [] };

  const currentUser = MockStore.get('currentUser', { name: 'Alex Rivera', avatar: 'AR' });
  const notifications = MockStore.get('notifications', []);
  const unreadCount = notifications.filter(n => !n.read).length;
  const isCollapsed = MockStore.get('sidebarCollapsed', false);

  const project = MockStore.get('project', { sprint: 'Sprint 23', sprintDates: 'Oct 28 – Nov 11, 2026' });

  return `
    <header class="topbar${isCollapsed ? ' sidebar-collapsed' : ''}" id="topbar" role="banner">
      <!-- Left: hamburger (mobile) + breadcrumb -->
      <div class="topbar-left">
        <!-- Mobile hamburger -->
        <button
          class="topbar-hamburger"
          id="topbar-hamburger"
          aria-label="Open navigation"
          title="Open navigation"
        >
          <i class="bi bi-list"></i>
        </button>

        <!-- Breadcrumbs -->
        <nav class="breadcrumb-bar" aria-label="Breadcrumb">
          ${renderBreadcrumbs(meta.crumbs, meta.title)}
        </nav>
      </div>

      <!-- Right: search, sprint, actions, user -->
      <div class="topbar-right">
        <!-- Search -->
        <div class="topbar-search">
          <i class="bi bi-search topbar-search-icon" aria-hidden="true"></i>
          <input
            type="search"
            class="topbar-search-input"
            id="topbar-search"
            placeholder="Search knowledge…"
            aria-label="Search"
            autocomplete="off"
          >
          <span class="topbar-search-shortcut" aria-hidden="true">⌘K</span>
        </div>

        <!-- Sprint pill -->
        <div class="sprint-pill" title="${project.sprintDates}">
          <i class="bi bi-lightning-charge"></i>
          ${project.sprint}
        </div>

        <!-- Notifications -->
        <button
          class="topbar-action-btn"
          id="topbar-notif-btn"
          title="Notifications"
          aria-label="Notifications (${unreadCount} unread)"
        >
          <i class="bi bi-bell"></i>
          ${unreadCount > 0 ? `<span class="topbar-notif-badge" aria-hidden="true">${unreadCount}</span>` : ''}
        </button>

        <!-- Help -->
        <button
          class="topbar-action-btn"
          title="Help &amp; Docs"
          aria-label="Help"
        >
          <i class="bi bi-question-circle"></i>
        </button>

        <!-- User menu -->
        <div class="topbar-user-wrapper" style="position: relative;">
          <button
            class="topbar-user-btn"
            id="topbar-user-btn"
            aria-haspopup="true"
            aria-expanded="false"
            aria-label="User menu"
          >
            <div class="topbar-user-avatar" aria-hidden="true">${currentUser.avatar || 'U'}</div>
            <span class="topbar-user-name">${currentUser.name?.split(' ')[0] || 'User'}</span>
            <i class="bi bi-chevron-down" style="font-size: 10px; color: var(--text-muted);" aria-hidden="true"></i>
          </button>
        </div>
      </div>
    </header>
  `;
}

// ─────────────────────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────────────────────

/**
 * Attach event listeners to the topbar.
 * Should be called once the topbar HTML is in the DOM.
 */
export function initTopbar() {
  // ── Mobile hamburger ──────────────────────────────────────
  const hamburger = document.getElementById('topbar-hamburger');
  hamburger?.addEventListener('click', openMobileSidebar);

  // ── Search — keyboard shortcut (⌘K / Ctrl+K) ─────────────
  const searchInput = document.getElementById('topbar-search');
  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      searchInput?.focus();
      searchInput?.select();
    }
    if (e.key === 'Escape' && document.activeElement === searchInput) {
      searchInput.blur();
      searchInput.value = '';
    }
  });

  searchInput?.addEventListener('input', e => {
    const q = e.target.value.trim();
    if (q.length > 0) {
      // In a real app, trigger search overlay. For demo, navigate to ledger.
      // debounce omitted for simplicity.
    }
  });

  // ── User menu dropdown ────────────────────────────────────
  const userBtn = document.getElementById('topbar-user-btn');
  userBtn?.addEventListener('click', e => {
    e.stopPropagation();
    toggleUserMenu();
  });

  // ── Notifications ─────────────────────────────────────────
  const notifBtn = document.getElementById('topbar-notif-btn');
  notifBtn?.addEventListener('click', e => {
    e.stopPropagation();
    toggleNotifPanel();
  });

  // ── Close dropdowns on outside click ─────────────────────
  document.addEventListener('click', () => {
    closeAllDropdowns();
  });

  // ── Update topbar on route change ────────────────────────
  window.addEventListener('hashchange', () => {
    const container = document.getElementById('topbar-container');
    if (container) {
      container.innerHTML = renderTopbar(window.location.hash);
      initTopbar();
    }
  });

  // ── Sync topbar collapsed state with sidebar ──────────────
  window.addEventListener('storage', () => {
    const collapsed = MockStore.get('sidebarCollapsed', false);
    document.getElementById('topbar')?.classList.toggle('sidebar-collapsed', collapsed);
  });
}

// ─────────────────────────────────────────────────────────────
// DROPDOWNS
// ─────────────────────────────────────────────────────────────

function closeAllDropdowns() {
  document.querySelectorAll('.cos-dropdown[data-topbar-dropdown]').forEach(el => el.remove());
  document.getElementById('topbar-user-btn')?.setAttribute('aria-expanded', 'false');
}

function toggleUserMenu() {
  const existing = document.querySelector('.cos-dropdown[data-topbar-dropdown="user"]');
  if (existing) { existing.remove(); return; }

  closeAllDropdowns();

  const currentUser = MockStore.get('currentUser', { name: 'Alex Rivera', role: 'Senior Backend Engineer' });
  const wrapper = document.querySelector('.topbar-user-wrapper');
  if (!wrapper) return;

  const dropdown = document.createElement('div');
  dropdown.className = 'cos-dropdown';
  dropdown.dataset.topbarDropdown = 'user';
  dropdown.innerHTML = `
    <div style="padding: 10px 14px 8px; border-bottom: 1px solid var(--border);">
      <div style="font-weight: 700; font-size: var(--text-sm); color: var(--text-primary);">${currentUser.name}</div>
      <div style="font-size: var(--text-xs); color: var(--text-muted);">${currentUser.role}</div>
    </div>
    <a class="cos-dropdown-item" href="#/settings" data-route="#/settings">
      <i class="bi bi-person-circle"></i> Profile
    </a>
    <a class="cos-dropdown-item" href="#/settings" data-route="#/settings">
      <i class="bi bi-gear"></i> Settings
    </a>
    <hr class="cos-dropdown-divider">
    <div class="cos-dropdown-item" id="switch-role-btn">
      <i class="bi bi-arrow-left-right"></i> Switch Role (Demo)
    </div>
    <hr class="cos-dropdown-divider">
    <div class="cos-dropdown-item danger" id="logout-btn">
      <i class="bi bi-box-arrow-right"></i> Sign out
    </div>
  `;

  wrapper.appendChild(dropdown);
  document.getElementById('topbar-user-btn')?.setAttribute('aria-expanded', 'true');

  // Nav items in dropdown
  dropdown.querySelectorAll('[data-route]').forEach(el => {
    el.addEventListener('click', e => {
      e.preventDefault();
      navigate(el.dataset.route);
      closeAllDropdowns();
    });
  });

  // Switch role — cycle through team members for demo
  document.getElementById('switch-role-btn')?.addEventListener('click', () => {
    const members = MockStore.get('teamMembers', []);
    const current = MockStore.get('currentUser', {});
    const idx = members.findIndex(m => m.id === current.id);
    const next = members[(idx + 1) % members.length];
    MockStore.set('currentUser', next);

    // Re-render topbar
    const container = document.getElementById('topbar-container');
    if (container) {
      container.innerHTML = renderTopbar(window.location.hash);
      initTopbar();
    }
    closeAllDropdowns();
  });

  document.getElementById('logout-btn')?.addEventListener('click', () => {
    alert('Demo mode — sign-out not available.');
    closeAllDropdowns();
  });
}

function toggleNotifPanel() {
  const existing = document.querySelector('.cos-dropdown[data-topbar-dropdown="notif"]');
  if (existing) { existing.remove(); return; }

  closeAllDropdowns();

  const notifications = MockStore.get('notifications', []);
  const notifBtn = document.getElementById('topbar-notif-btn');
  if (!notifBtn) return;

  const typeIconMap = {
    warning: { icon: 'bi-exclamation-triangle-fill', color: 'var(--warning)' },
    error:   { icon: 'bi-x-circle-fill', color: 'var(--danger)' },
    info:    { icon: 'bi-info-circle-fill', color: 'var(--info)' },
    success: { icon: 'bi-check-circle-fill', color: 'var(--success)' },
  };

  const notifItems = notifications.map(n => {
    const meta = typeIconMap[n.type] || typeIconMap.info;
    const time = n.timestamp ? new Date(n.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) : '';
    return `
      <div class="cos-dropdown-item" style="align-items: flex-start; gap: 10px; ${n.read ? 'opacity: 0.65;' : ''}">
        <i class="bi ${meta.icon}" style="color: ${meta.color}; margin-top: 2px; flex-shrink: 0;"></i>
        <div style="flex: 1; min-width: 0;">
          <div style="font-size: var(--text-sm); font-weight: ${n.read ? '400' : '600'}; color: var(--text-primary); line-height: 1.4;">${n.message}</div>
          <div style="font-size: var(--text-xs); color: var(--text-muted); margin-top: 2px;">${time}</div>
        </div>
      </div>
    `;
  }).join('');

  const dropdown = document.createElement('div');
  dropdown.className = 'cos-dropdown';
  dropdown.dataset.topbarDropdown = 'notif';
  dropdown.style.minWidth = '320px';
  dropdown.style.right = '0';
  dropdown.innerHTML = `
    <div style="padding: 10px 14px 8px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
      <div style="font-weight: 700; font-size: var(--text-sm);">Notifications</div>
      <span style="font-size: var(--text-xs); color: var(--primary); cursor: pointer;" id="mark-all-read">Mark all read</span>
    </div>
    ${notifItems || '<div class="cos-dropdown-item" style="color: var(--text-muted);">No notifications</div>'}
  `;

  // Position relative to notif button
  const wrapper = notifBtn.closest('.topbar-right') || notifBtn.parentElement;
  const relContainer = document.createElement('div');
  relContainer.style.position = 'relative';
  relContainer.style.display = 'contents';
  wrapper.style.position = 'relative';
  notifBtn.parentElement.style.position = 'relative';
  notifBtn.insertAdjacentElement('afterend', dropdown);
  dropdown.dataset.topbarDropdown = 'notif';

  document.getElementById('mark-all-read')?.addEventListener('click', () => {
    MockStore.update('notifications', ns => ns.map(n => ({ ...n, read: true })), []);
    const container = document.getElementById('topbar-container');
    if (container) {
      container.innerHTML = renderTopbar(window.location.hash);
      initTopbar();
    }
    closeAllDropdowns();
  });
}
