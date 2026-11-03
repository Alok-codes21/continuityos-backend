/**
 * ContinuityOS — Mock Store
 * Observable localStorage-backed store with pub/sub.
 */

import {
  PROJECT,
  TEAM_MEMBERS,
  TASKS,
  DECISIONS,
  BUGS,
  DOCUMENTS,
  KNOWLEDGE_RECORDS,
  COMPONENTS,
  DEPENDENCIES,
  RISKS,
  HANDOVERS,
  SOURCES,
  METRICS,
} from './demo-data.js';

const INIT_FLAG = 'cos_initialized';
const KEY_PREFIX = 'cos_';

/** Simple observable store backed by localStorage. */
export class MockStore {
  static #subscribers = new Map();

  /**
   * Read a value from the store.
   * @param {string} key
   * @param {*} defaultValue
   * @returns {*}
   */
  static get(key, defaultValue = null) {
    try {
      const raw = localStorage.getItem(KEY_PREFIX + key);
      if (raw === null) return defaultValue;
      return JSON.parse(raw);
    } catch {
      return defaultValue;
    }
  }

  /**
   * Write a value to the store and notify subscribers.
   * @param {string} key
   * @param {*} value
   */
  static set(key, value) {
    try {
      localStorage.setItem(KEY_PREFIX + key, JSON.stringify(value));
      MockStore.#notify(key, value);
    } catch (err) {
      console.warn('[MockStore] set failed:', err);
    }
  }

  /**
   * Apply an updater function to the current value and save the result.
   * @param {string} key
   * @param {function(*): *} updaterFn
   * @param {*} defaultValue - used if no current value
   */
  static update(key, updaterFn, defaultValue = null) {
    const current = MockStore.get(key, defaultValue);
    const next = updaterFn(current);
    MockStore.set(key, next);
    return next;
  }

  /**
   * Subscribe to changes on a key. Returns an unsubscribe function.
   * @param {string} key
   * @param {function(*): void} callback
   * @returns {function(): void} unsubscribe
   */
  static subscribe(key, callback) {
    if (!MockStore.#subscribers.has(key)) {
      MockStore.#subscribers.set(key, new Set());
    }
    MockStore.#subscribers.get(key).add(callback);
    return () => {
      const set = MockStore.#subscribers.get(key);
      if (set) set.delete(callback);
    };
  }

  /**
   * Notify all subscribers for a key.
   * @param {string} key
   * @param {*} value
   */
  static #notify(key, value) {
    const subscribers = MockStore.#subscribers.get(key);
    if (subscribers) {
      subscribers.forEach(cb => {
        try { cb(value); } catch (e) { console.warn('[MockStore] subscriber error:', e); }
      });
    }
  }

  /**
   * Clear all COS keys from localStorage.
   */
  static clear() {
    Object.keys(localStorage)
      .filter(k => k.startsWith(KEY_PREFIX))
      .forEach(k => localStorage.removeItem(k));
    localStorage.removeItem(INIT_FLAG);
    MockStore.#subscribers.clear();
  }

  /**
   * Dump all store keys for debugging.
   */
  static debug() {
    const state = {};
    Object.keys(localStorage)
      .filter(k => k.startsWith(KEY_PREFIX))
      .forEach(k => {
        try { state[k] = JSON.parse(localStorage.getItem(k)); }
        catch { state[k] = localStorage.getItem(k); }
      });
    return state;
  }
}

/**
 * Seeds localStorage with demo data on first run.
 * Subsequent calls are no-ops (checks cos_initialized flag).
 */
export function initializeStore() {
  if (localStorage.getItem(INIT_FLAG) === 'true') {
    return; // already seeded
  }

  MockStore.set('project', PROJECT);
  MockStore.set('teamMembers', TEAM_MEMBERS);
  MockStore.set('tasks', TASKS);
  MockStore.set('decisions', DECISIONS);
  MockStore.set('bugs', BUGS);
  MockStore.set('documents', DOCUMENTS);
  MockStore.set('knowledgeRecords', KNOWLEDGE_RECORDS);
  MockStore.set('components', COMPONENTS);
  MockStore.set('dependencies', DEPENDENCIES);
  MockStore.set('risks', RISKS);
  MockStore.set('handovers', HANDOVERS);
  MockStore.set('sources', SOURCES);
  MockStore.set('metrics', METRICS);

  // UI preferences
  MockStore.set('sidebarCollapsed', false);
  MockStore.set('currentUser', TEAM_MEMBERS[0]); // Alex Rivera (departing)
  MockStore.set('notifications', [
    { id: 'notif-1', type: 'warning', message: 'Alex Rivera departs in 11 days — 3 undocumented components', read: false, timestamp: '2026-11-03T09:00:00Z' },
    { id: 'notif-2', type: 'error', message: 'Data pipeline OOM crashes detected in production', read: false, timestamp: '2026-11-03T08:30:00Z' },
    { id: 'notif-3', type: 'info', message: 'Sprint 23 planning complete — 18 tasks assigned', read: true, timestamp: '2026-10-28T10:00:00Z' },
  ]);

  localStorage.setItem(INIT_FLAG, 'true');
  console.info('[ContinuityOS] Store initialised with demo data.');
}

/**
 * Reset the store to demo data (e.g., for demos/testing).
 */
export function resetStore() {
  MockStore.clear();
  initializeStore();
}
