/**
 * ContinuityOS — Client-side Router
 * Hash-based SPA router with lazy-loaded page modules.
 */

/** Route map: hash → dynamic import factory */
const routes = {
  '#/overview':            () => import('./pages/overview/index.js'),
  '#/knowledge-graph':     () => import('./pages/knowledge-graph/index.js'),
  '#/sources':             () => import('./pages/sources/index.js'),
  '#/uncertainty-ledger':  () => import('./pages/uncertainty-ledger/index.js'),
  '#/impact-simulator':    () => import('./pages/impact-simulator/index.js'),
  '#/handover-interview':  () => import('./pages/handover-interview/index.js'),
  '#/handover-centre':     () => import('./pages/handover-centre/index.js'),
  '#/incoming-workspace':  () => import('./pages/incoming-workspace/index.js'),
  '#/rehearsal':           () => import('./pages/rehearsal/index.js'),
  '#/assistant':           () => import('./pages/assistant/index.js'),
  '#/security':            () => import('./pages/security/index.js'),
  '#/settings':            () => import('./pages/settings/index.js'),
};

const DEFAULT_ROUTE = '#/overview';

/** Currently mounted page's cleanup function (if any) */
let currentCleanup = null;

/** The element that page content renders into */
let contentEl = null;

/**
 * Navigate to a route programmatically.
 * @param {string} hash e.g. '#/overview'
 */
export function navigate(hash) {
  window.location.hash = hash;
}

/**
 * Get the current clean hash, defaulting to '#/overview'.
 * @returns {string}
 */
function currentHash() {
  const h = window.location.hash;
  return h && h in routes ? h : DEFAULT_ROUTE;
}

/**
 * Show a loading indicator while the page module loads.
 */
function showPageLoader() {
  if (!contentEl) return;
  contentEl.innerHTML = `
    <div class="loading-state">
      <div class="cos-spinner"></div>
      <p style="color: var(--text-muted); font-size: var(--text-sm);">Loading…</p>
    </div>
  `;
}

/**
 * Show a 404 / not-found state.
 * @param {string} hash
 */
function showNotFound(hash) {
  if (!contentEl) return;
  contentEl.innerHTML = `
    <div class="empty-state">
      <div class="empty-state-icon"><i class="bi bi-question-circle"></i></div>
      <div class="empty-state-title">Page not found</div>
      <p class="empty-state-desc">The route <code>${hash}</code> doesn't exist.</p>
      <button class="cos-btn cos-btn-primary" onclick="window.location.hash='#/overview'">
        <i class="bi bi-grid-1x2"></i> Go to Overview
      </button>
    </div>
  `;
}

/**
 * Show an error state if the page module fails to load.
 * @param {Error} err
 */
function showPageError(err) {
  if (!contentEl) return;
  console.error('[Router] Page load error:', err);
  contentEl.innerHTML = `
    <div class="empty-state">
      <div class="empty-state-icon" style="background: var(--danger-light); color: var(--danger);">
        <i class="bi bi-exclamation-triangle"></i>
      </div>
      <div class="empty-state-title">Failed to load page</div>
      <p class="empty-state-desc">${err.message || 'An unexpected error occurred.'}</p>
      <button class="cos-btn cos-btn-secondary" onclick="window.location.reload()">
        <i class="bi bi-arrow-clockwise"></i> Reload
      </button>
    </div>
  `;
}

/**
 * Update sidebar active state to match the current hash.
 * @param {string} hash
 */
function updateSidebarActive(hash) {
  document.querySelectorAll('.sidebar-nav-item').forEach(el => {
    const itemHash = el.dataset.route;
    el.classList.toggle('active', itemHash === hash);
  });
}

/**
 * Resolve and render the page for the given hash.
 * @param {string} hash
 */
async function renderPage(hash) {
  // Clean up previous page
  if (typeof currentCleanup === 'function') {
    try { currentCleanup(); } catch { /* ignore */ }
    currentCleanup = null;
  }

  // Update sidebar highlight
  updateSidebarActive(hash);

  // Scroll content to top
  if (contentEl) contentEl.scrollTop = 0;

  const loader = routes[hash];
  if (!loader) {
    showNotFound(hash);
    return;
  }

  showPageLoader();

  try {
    const module = await loader();

    // Every page module must export a default `renderPage(el)` function.
    if (typeof module.default !== 'function') {
      throw new Error(`Page module for ${hash} does not export a default function.`);
    }

    if (contentEl) contentEl.innerHTML = '';
    const cleanup = await module.default(contentEl);
    if (typeof cleanup === 'function') {
      currentCleanup = cleanup;
    }
  } catch (err) {
    showPageError(err);
  }
}

/**
 * Handle hashchange event.
 */
function onHashChange() {
  const hash = currentHash();
  renderPage(hash);
}

/**
 * Initialise the router. Call once after the DOM shell is rendered.
 * @param {HTMLElement} appContentEl - The element to render pages into.
 */
export function initRouter(appContentEl) {
  contentEl = appContentEl;

  window.addEventListener('hashchange', onHashChange);

  // Navigate to current hash (or default)
  const initial = currentHash();
  if (!window.location.hash || !(window.location.hash in routes)) {
    window.history.replaceState(null, '', DEFAULT_ROUTE);
  }
  renderPage(initial);
}

/**
 * Tear down the router (useful for HMR / testing).
 */
export function destroyRouter() {
  window.removeEventListener('hashchange', onHashChange);
  if (typeof currentCleanup === 'function') {
    try { currentCleanup(); } catch { /* ignore */ }
    currentCleanup = null;
  }
  contentEl = null;
}
