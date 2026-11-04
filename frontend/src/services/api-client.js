/** Live FastAPI transport. No mock fallback and no demo records. */
const API_BASE = import.meta.env.VITE_API_URL || '/api';
export class ApiError extends Error {
  constructor(status, message, body) { super(message); this.status = status; this.body = body; }
}
export const session = {
  get token() { return sessionStorage.getItem('continuity_token'); },
  set token(v) { v ? sessionStorage.setItem('continuity_token', v) : sessionStorage.removeItem('continuity_token'); },
  get projectId() { return sessionStorage.getItem('continuity_project') || ''; },
  set projectId(v) { sessionStorage.setItem('continuity_project', v); },
};
export async function request(path, options = {}) {
  const multipart = options.body instanceof FormData;
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers: {
    Accept: 'application/json', ...(multipart ? {} : {'Content-Type':'application/json'}),
    ...(session.token ? {Authorization:`Bearer ${session.token}`} : {}), ...options.headers,
  }});
  if (options.blob && res.ok) return res.blob();
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401) { session.token = null; window.dispatchEvent(new Event('session-expired')); }
    const detail = body.detail || body.message || `Request failed (${res.status})`;
    throw new ApiError(res.status, typeof detail === 'string' ? detail : JSON.stringify(detail), body);
  }
  return body;
}
export const apiGet = p => request(p);
export const apiPost = (p,b={}) => request(p,{method:'POST',body:JSON.stringify(b)});
export const apiPut = (p,b) => request(p,{method:'PUT',body:JSON.stringify(b)});
export const apiPatch = (p,b) => request(p,{method:'PATCH',body:JSON.stringify(b)});
export const apiDelete = p => request(p,{method:'DELETE'});
