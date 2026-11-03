/**
 * ContinuityOS — Mock API
 * Returns Promises that resolve after a simulated network delay (~200ms).
 * All data is read from / written to MockStore (localStorage).
 */

import { MockStore } from '../data/mock-store.js';

/** Simulated network latency */
const DELAY_MS = 200;

/** @param {number} [ms] */
function delay(ms = DELAY_MS) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Deep clone to avoid accidental mutation of stored objects.
 * @param {*} value
 * @returns {*}
 */
function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

// ─────────────────────────────────────────────────────────────
// PROJECT
// ─────────────────────────────────────────────────────────────

/** @returns {Promise<object>} */
export async function getProject() {
  await delay();
  return clone(MockStore.get('project'));
}

// ─────────────────────────────────────────────────────────────
// TEAM MEMBERS
// ─────────────────────────────────────────────────────────────

/** @returns {Promise<object[]>} */
export async function getTeamMembers() {
  await delay();
  return clone(MockStore.get('teamMembers', []));
}

/**
 * @param {string} id
 * @returns {Promise<object|null>}
 */
export async function getTeamMember(id) {
  await delay();
  const members = MockStore.get('teamMembers', []);
  return clone(members.find(m => m.id === id) ?? null);
}

// ─────────────────────────────────────────────────────────────
// TASKS
// ─────────────────────────────────────────────────────────────

/**
 * @param {{ status?: string, priority?: string, assignee?: string, component?: string }} [filters]
 * @returns {Promise<object[]>}
 */
export async function getTasks(filters = {}) {
  await delay();
  let tasks = MockStore.get('tasks', []);

  if (filters.status)    tasks = tasks.filter(t => t.status === filters.status);
  if (filters.priority)  tasks = tasks.filter(t => t.priority === filters.priority);
  if (filters.assignee)  tasks = tasks.filter(t => t.assignee === filters.assignee);
  if (filters.component) tasks = tasks.filter(t => t.component === filters.component);
  if (filters.sprint)    tasks = tasks.filter(t => t.sprint === filters.sprint);

  return clone(tasks);
}

/**
 * @param {string} id
 * @returns {Promise<object|null>}
 */
export async function getTask(id) {
  await delay();
  const tasks = MockStore.get('tasks', []);
  return clone(tasks.find(t => t.id === id) ?? null);
}

/**
 * @param {string} id
 * @param {object} updates
 * @returns {Promise<object>}
 */
export async function updateTask(id, updates) {
  await delay();
  const updated = MockStore.update('tasks', tasks =>
    tasks.map(t => (t.id === id ? { ...t, ...updates } : t))
  , []);
  return clone(updated.find(t => t.id === id));
}

// ─────────────────────────────────────────────────────────────
// DECISIONS
// ─────────────────────────────────────────────────────────────

/** @returns {Promise<object[]>} */
export async function getDecisions() {
  await delay();
  return clone(MockStore.get('decisions', []));
}

/**
 * @param {string} id
 * @returns {Promise<object|null>}
 */
export async function getDecision(id) {
  await delay();
  const decisions = MockStore.get('decisions', []);
  return clone(decisions.find(d => d.id === id) ?? null);
}

// ─────────────────────────────────────────────────────────────
// BUGS
// ─────────────────────────────────────────────────────────────

/** @returns {Promise<object[]>} */
export async function getBugs() {
  await delay();
  return clone(MockStore.get('bugs', []));
}

// ─────────────────────────────────────────────────────────────
// DOCUMENTS
// ─────────────────────────────────────────────────────────────

/**
 * @param {{ classification?: string, component?: string, source?: string }} [filters]
 * @returns {Promise<object[]>}
 */
export async function getDocuments(filters = {}) {
  await delay();
  let docs = MockStore.get('documents', []);

  if (filters.classification) docs = docs.filter(d => d.classification === filters.classification);
  if (filters.source)         docs = docs.filter(d => d.source === filters.source);

  return clone(docs);
}

/**
 * @param {string} id
 * @returns {Promise<object|null>}
 */
export async function getDocument(id) {
  await delay();
  const docs = MockStore.get('documents', []);
  return clone(docs.find(d => d.id === id) ?? null);
}

// ─────────────────────────────────────────────────────────────
// KNOWLEDGE RECORDS
// ─────────────────────────────────────────────────────────────

/**
 * @param {{ classification?: string, component?: string, search?: string }} [filters]
 * @returns {Promise<object[]>}
 */
export async function getKnowledgeRecords(filters = {}) {
  await delay();
  let records = MockStore.get('knowledgeRecords', []);

  if (filters.classification) records = records.filter(r => r.classification === filters.classification);
  if (filters.component)      records = records.filter(r => r.component === filters.component);
  if (filters.search) {
    const q = filters.search.toLowerCase();
    records = records.filter(r =>
      r.claim.toLowerCase().includes(q) ||
      (r.tags && r.tags.some(t => t.includes(q)))
    );
  }

  return clone(records);
}

/**
 * @param {string} id
 * @param {object} updates
 * @returns {Promise<object>}
 */
export async function updateKnowledgeRecord(id, updates) {
  await delay();
  const next = MockStore.update('knowledgeRecords', records =>
    records.map(r => (r.id === id ? { ...r, ...updates } : r))
  , []);
  return clone(next.find(r => r.id === id));
}

/**
 * Mark a knowledge record as verified.
 * @param {string} id
 * @returns {Promise<object>}
 */
export async function approveKnowledgeRecord(id) {
  return updateKnowledgeRecord(id, {
    classification: 'verified',
    confidence: 95,
    lastVerified: new Date().toISOString().split('T')[0],
  });
}

/**
 * Mark a knowledge record as conflicting with a reason.
 * @param {string} id
 * @param {string} reason
 * @returns {Promise<object>}
 */
export async function rejectKnowledgeRecord(id, reason) {
  return updateKnowledgeRecord(id, {
    classification: 'conflicting',
    conflictNote: reason,
    confidence: 20,
  });
}

/**
 * Add a new knowledge record.
 * @param {object} record
 * @returns {Promise<object>}
 */
export async function createKnowledgeRecord(record) {
  await delay();
  const id = `kr-${Date.now()}`;
  const newRecord = {
    id,
    confidence: 50,
    classification: 'inferred',
    lastVerified: null,
    verifiedBy: null,
    evidenceLinks: [],
    tags: [],
    createdAt: new Date().toISOString(),
    ...record,
    id,
  };
  MockStore.update('knowledgeRecords', records => [...records, newRecord], []);
  return clone(newRecord);
}

// ─────────────────────────────────────────────────────────────
// COMPONENTS
// ─────────────────────────────────────────────────────────────

/**
 * @param {{ risk?: string, type?: string }} [filters]
 * @returns {Promise<object[]>}
 */
export async function getComponents(filters = {}) {
  await delay();
  let comps = MockStore.get('components', []);

  if (filters.risk) comps = comps.filter(c => c.risk === filters.risk);
  if (filters.type) comps = comps.filter(c => c.type === filters.type);

  return clone(comps);
}

// ─────────────────────────────────────────────────────────────
// METRICS
// ─────────────────────────────────────────────────────────────

/** @returns {Promise<object>} */
export async function getMetrics() {
  await delay();
  return clone(MockStore.get('metrics', {}));
}

// ─────────────────────────────────────────────────────────────
// RISKS
// ─────────────────────────────────────────────────────────────

/**
 * @param {{ severity?: string }} [filters]
 * @returns {Promise<object[]>}
 */
export async function getRisks(filters = {}) {
  await delay();
  let risks = MockStore.get('risks', []);

  if (filters.severity) risks = risks.filter(r => r.severity === filters.severity);

  return clone(risks);
}

// ─────────────────────────────────────────────────────────────
// HANDOVERS
// ─────────────────────────────────────────────────────────────

/** @returns {Promise<object[]>} */
export async function getHandovers() {
  await delay();
  return clone(MockStore.get('handovers', []));
}

/**
 * @param {string} id
 * @param {object} updates
 * @returns {Promise<object>}
 */
export async function updateHandover(id, updates) {
  await delay();
  const next = MockStore.update('handovers', hs =>
    hs.map(h => (h.id === id ? { ...h, ...updates, updatedAt: new Date().toISOString() } : h))
  , []);
  return clone(next.find(h => h.id === id));
}

// ─────────────────────────────────────────────────────────────
// SOURCES
// ─────────────────────────────────────────────────────────────

/** @returns {Promise<object[]>} */
export async function getSources() {
  await delay();
  return clone(MockStore.get('sources', []));
}

/**
 * Connect a source (sets status to 'connected').
 * @param {string} id
 * @returns {Promise<object>}
 */
export async function connectSource(id) {
  await delay(600); // simulate OAuth flow
  const next = MockStore.update('sources', srcs =>
    srcs.map(s => (s.id === id
      ? { ...s, status: 'connected', lastSync: new Date().toISOString(), documentsIndexed: 0 }
      : s))
  , []);
  return clone(next.find(s => s.id === id));
}

/**
 * Disconnect a source.
 * @param {string} id
 * @returns {Promise<object>}
 */
export async function disconnectSource(id) {
  await delay();
  const next = MockStore.update('sources', srcs =>
    srcs.map(s => (s.id === id
      ? { ...s, status: 'disconnected', lastSync: null }
      : s))
  , []);
  return clone(next.find(s => s.id === id));
}

// ─────────────────────────────────────────────────────────────
// DEPENDENCIES
// ─────────────────────────────────────────────────────────────

/** @returns {Promise<object[]>} */
export async function getDependencies() {
  await delay();
  return clone(MockStore.get('dependencies', []));
}

// ─────────────────────────────────────────────────────────────
// CURRENT USER / AUTH
// ─────────────────────────────────────────────────────────────

/** @returns {Promise<object>} */
export async function getCurrentUser() {
  await delay(50);
  return clone(MockStore.get('currentUser', {}));
}

// ─────────────────────────────────────────────────────────────
// NOTIFICATIONS
// ─────────────────────────────────────────────────────────────

/** @returns {Promise<object[]>} */
export async function getNotifications() {
  await delay(50);
  return clone(MockStore.get('notifications', []));
}

/**
 * @param {string} id
 * @returns {Promise<void>}
 */
export async function markNotificationRead(id) {
  await delay(50);
  MockStore.update('notifications', ns =>
    ns.map(n => (n.id === id ? { ...n, read: true } : n))
  , []);
}
