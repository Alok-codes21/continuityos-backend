/**
 * ContinuityOS — Main Entry Point
 */

// ── Styles ───────────────────────────────────────────────────
import './styles/global.css';
import './styles/layout.css';
import './styles/components.css';

// ── Bootstrap ────────────────────────────────────────────────
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap-icons/font/bootstrap-icons.css';

// ── App modules ──────────────────────────────────────────────
import { initializeStore } from './data/mock-store.js';
import { renderSidebar, initSidebar } from './components/sidebar.js';
import { renderTopbar, initTopbar } from './components/topbar.js';
import { initRouter } from './router.js';

// ─────────────────────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────────────────────

/** Mount the entire application. */
function mount() {
  const app = document.getElementById('app');
  if (!app) {
    console.error('[ContinuityOS] #app element not found.');
    return;
  }

  // 1. Seed localStorage with demo data
  initializeStore();

  // 2. Render the app shell (sidebar + main wrapper)
  app.innerHTML = `
    <div class="app-layout">
      ${renderSidebar()}
      <div class="main-area" id="main-area">
        <div id="topbar-container"></div>
        <main class="page-content" id="page-content" role="main"></main>
      </div>
    </div>
  `;

  // 3. Render topbar into its container
  const topbarContainer = document.getElementById('topbar-container');
  if (topbarContainer) {
    topbarContainer.innerHTML = renderTopbar(window.location.hash || '#/overview');
  }

  // 4. Attach interactive behaviours
  initSidebar();
  initTopbar();

  // 5. Start the router — renders the first page
  initRouter(document.getElementById('page-content'));

  console.info('[ContinuityOS] Application mounted successfully.');
}

// ─────────────────────────────────────────────────────────────
// BOOT
// ─────────────────────────────────────────────────────────────

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mount);
} else {
  mount();
}
