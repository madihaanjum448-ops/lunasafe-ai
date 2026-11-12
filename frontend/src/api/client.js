/**
 * Central API client for the LunaSafe AI backend (FastAPI).
 * Base URL comes from VITE_API_URL (default http://localhost:8000).
 * Every function returns parsed JSON or throws an ApiError with a readable message.
 */

const BASE_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message, { status = 0, detail = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

const STATUS_MESSAGES = {
  400: 'The backend rejected the request (bad request).',
  413: 'The image is too large for the backend.',
  415: 'The backend does not support this file type.',
  422: 'The backend could not process the data (validation error).',
  500: 'The backend hit an internal error.',
};

function formatDetail(detail) {
  if (!detail) return '';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (d && d.msg ? `${(d.loc || []).slice(1).join('.')}: ${d.msg}` : JSON.stringify(d)))
      .slice(0, 3)
      .join('; ');
  }
  return JSON.stringify(detail);
}

const DEFAULT_TIMEOUT_MS = 30000;
const UPLOAD_TIMEOUT_MS = 120000;

async function request(path, options = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, { ...options, signal: controller.signal });
  } catch (err) {
    clearTimeout(timer);
    if (err && err.name === 'AbortError') {
      throw new ApiError(
        `The backend at ${BASE_URL} did not respond within ${Math.round(timeoutMs / 1000)} seconds.`,
        { status: 0 }
      );
    }
    throw new ApiError(
      `Cannot reach the backend at ${BASE_URL}. Check that it is running and that it allows this page's address (CORS).`,
      { status: 0 }
    );
  }
  clearTimeout(timer);

  if (!res.ok) {
    let detail = null;
    try {
      const body = await res.json();
      detail = body && body.detail !== undefined ? body.detail : body;
    } catch {
      detail = null;
    }
    const base = STATUS_MESSAGES[res.status] || `Backend error (HTTP ${res.status}).`;
    const extra = formatDetail(detail);
    throw new ApiError(extra ? `${base} ${extra}` : base, { status: res.status, detail });
  }

  try {
    return await res.json();
  } catch {
    throw new ApiError('The backend returned an unreadable response.', { status: res.status });
  }
}

/** GET /api/health */
export function getHealth() {
  return request('/api/health');
}

/** GET /api/config: default analysis thresholds (placeholders, not validated limits). */
export function getConfig() {
  return request('/api/config');
}

/**
 * POST /api/upload (multipart). Metadata is optional; the backend never invents missing values.
 * @param {File} file
 * @param {{pixelScaleM?: number|null, sunElevationDeg?: number|null, projection?: string|null}} [meta]
 */
export function uploadImage(file, meta = {}) {
  const form = new FormData();
  form.append('file', file);
  if (meta.pixelScaleM != null) form.append('pixel_scale_m', String(meta.pixelScaleM));
  if (meta.sunElevationDeg != null) form.append('sun_elevation_deg', String(meta.sunElevationDeg));
  if (meta.projection) form.append('projection', meta.projection);
  return request('/api/upload', { method: 'POST', body: form }, UPLOAD_TIMEOUT_MS);
}

/**
 * POST /api/analyze (JSON): { image, detections, shadow_lengths_px?, config?, slope_by_cell?, recall?, is_mock }
 */
export function analyze(payload) {
  return request('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export default { getHealth, getConfig, uploadImage, analyze };
