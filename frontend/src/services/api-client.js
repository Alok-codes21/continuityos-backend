/**
 * ContinuityOS — API Client
 * Thin fetch wrapper with structured error handling.
 * Falls back gracefully — pages should prefer mock-api.js for demo mode.
 */

const API_BASE = import.meta.env.VITE_API_URL || '/api';

export class ApiError extends Error {
  /**
   * @param {number} status
   * @param {string} message
   * @param {*} [body]
   */
  constructor(status, message, body = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

/**
 * Core fetch helper.
 * @param {string} path
 * @param {RequestInit} [options]
 * @returns {Promise<*>}
 */
async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;

  const defaultHeaders = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  };

  const res = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  let body = null;
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    body = await res.json();
  } else {
    body = await res.text();
  }

  if (!res.ok) {
    const message =
      (body && typeof body === 'object' && body.message) ||
      (typeof body === 'string' && body) ||
      `HTTP ${res.status}`;
    throw new ApiError(res.status, message, body);
  }

  return body;
}

/**
 * GET /api{path}
 * @param {string} path
 * @returns {Promise<*>}
 */
export async function apiGet(path) {
  return request(path, { method: 'GET' });
}

/**
 * POST /api{path}
 * @param {string} path
 * @param {object} body
 * @returns {Promise<*>}
 */
export async function apiPost(path, body) {
  return request(path, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * PUT /api{path}
 * @param {string} path
 * @param {object} body
 * @returns {Promise<*>}
 */
export async function apiPut(path, body) {
  return request(path, {
    method: 'PUT',
    body: JSON.stringify(body),
  });
}

/**
 * PATCH /api{path}
 * @param {string} path
 * @param {object} body
 * @returns {Promise<*>}
 */
export async function apiPatch(path, body) {
  return request(path, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}

/**
 * DELETE /api{path}
 * @param {string} path
 * @returns {Promise<*>}
 */
export async function apiDelete(path) {
  return request(path, { method: 'DELETE' });
}
