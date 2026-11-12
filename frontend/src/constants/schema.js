/**
 * Backend contract schema, field mappings, label tokens and normalization for LunaSafe AI.
 * Centralizing all field names, label strings, label colours, and placeholder value lists
 * here ensures that any backend contract changes are isolated to this single file.
 */

export const BACKEND_FIELDS = {
  // Boulder detection fields
  BOULDER_ID: 'id',
  BOULDER_BBOX: 'bbox',
  BOULDER_CONFIDENCE: 'confidence',
  BOULDER_DIAMETER: 'diameter_m',
  BOULDER_SHADOW_LENGTH: 'shadow_length_m',
  BOULDER_HEIGHT: 'height_m',
  BOULDER_HEIGHT_METHOD: 'height_method',
  BOULDER_HEIGHT_UNCERTAINTY: 'height_uncertainty_m',

  // Grid cell fields
  CELL_ROW: 'row',
  CELL_COL: 'col',
  CELL_PROBABILITY: 'probability',
  CELL_INTERVAL_LOW: 'interval_low',
  CELL_INTERVAL_HIGH: 'interval_high',
  CELL_LABEL: 'label',
  CELL_RAW_COUNT: 'raw_count',
  CELL_CORRECTED_COUNT: 'corrected_count',
  CELL_LARGEST_HEIGHT: 'largest_height_m',
  CELL_SLOPE: 'slope_deg',
  CELL_SLOPE_STATUS: 'slope_status',

  // Top level fields
  IMAGE: 'image',
  DETECTIONS: 'detections',
  HAZARD_CELLS: 'hazard_cells',
  WARNINGS: 'warnings',
};

/**
 * Exact agreed label names.
 * Note: Never use the words "safe landing" or "certified" anywhere in the UI.
 */
export const HAZARD_LABELS = {
  SAFE_CANDIDATE: 'Safe candidate',
  CAUTION: 'Caution',
  UNSAFE_CANDIDATE: 'Unsafe candidate',
  NOT_ASSESSED: 'Not assessed',
};

/**
 * Candidate region advisory note mandated across the UI.
 */
export const CANDIDATE_ONLY_NOTE = 'Candidate regions only. This is not a landing safety certification.';

/**
 * Placeholder value list for slope_status (not confirmed yet).
 */
export const SLOPE_STATUS = {
  NOMINAL: 'nominal',
  MODERATE: 'moderate',
  STEEP: 'steep',
  UNAVAILABLE: 'unavailable',
};

/**
 * Placeholder value list for height_method (not confirmed yet).
 */
export const HEIGHT_METHODS = {
  SHADOW: 'shadow_geometry',
  DIAMETER_FALLBACK: 'diameter_fallback',
  UNAVAILABLE: 'unavailable',
};

/**
 * Label visual styling: colours (green, yellow, red, grey), badges and SVG stroke/fill.
 * "Not assessed" cells have a grey fill and dashed outline.
 */
export const HAZARD_LABEL_COLORS = {
  [HAZARD_LABELS.SAFE_CANDIDATE]: {
    key: 'safe_candidate',
    colorName: 'green',
    fill: 'rgba(34, 197, 94, 0.32)',
    fillHovered: 'rgba(34, 197, 94, 0.45)',
    fillSelected: 'rgba(34, 197, 94, 0.55)',
    stroke: '#22c55e',
    strokeHovered: '#86efac',
    strokeSelected: '#ffffff',
    strokeDasharray: undefined,
    textFill: '#dcfce7',
    badgeClass: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40',
    swatchBg: 'bg-emerald-500/40',
    swatchBorder: 'border-emerald-400',
    textClass: 'text-emerald-400',
  },
  [HAZARD_LABELS.CAUTION]: {
    key: 'caution',
    colorName: 'yellow',
    fill: 'rgba(234, 179, 8, 0.35)',
    fillHovered: 'rgba(234, 179, 8, 0.48)',
    fillSelected: 'rgba(234, 179, 8, 0.60)',
    stroke: '#eab308',
    strokeHovered: '#fef08a',
    strokeSelected: '#ffffff',
    strokeDasharray: undefined,
    textFill: '#fef9c3',
    badgeClass: 'bg-amber-500/20 text-amber-300 border border-amber-500/40',
    swatchBg: 'bg-amber-500/40',
    swatchBorder: 'border-amber-400',
    textClass: 'text-amber-400',
  },
  [HAZARD_LABELS.UNSAFE_CANDIDATE]: {
    key: 'unsafe_candidate',
    colorName: 'red',
    fill: 'rgba(239, 68, 68, 0.38)',
    fillHovered: 'rgba(239, 68, 68, 0.52)',
    fillSelected: 'rgba(239, 68, 68, 0.65)',
    stroke: '#ef4444',
    strokeHovered: '#fca5a5',
    strokeSelected: '#ffffff',
    strokeDasharray: undefined,
    textFill: '#fee2e2',
    badgeClass: 'bg-red-500/20 text-red-300 border border-red-500/40',
    swatchBg: 'bg-red-500/40',
    swatchBorder: 'border-red-400',
    textClass: 'text-red-400',
  },
  [HAZARD_LABELS.NOT_ASSESSED]: {
    key: 'not_assessed',
    colorName: 'grey',
    fill: 'rgba(100, 116, 139, 0.22)',
    fillHovered: 'rgba(100, 116, 139, 0.36)',
    fillSelected: 'rgba(148, 163, 184, 0.45)',
    stroke: '#94a3b8',
    strokeHovered: '#cbd5e1',
    strokeSelected: '#ffffff',
    strokeDasharray: '6 4', // Dashed outline for Not assessed
    textFill: '#cbd5e1',
    badgeClass: 'bg-slate-700/40 text-slate-300 border border-slate-600',
    swatchBg: 'bg-slate-700/50',
    swatchBorder: 'border-slate-500 border-dashed',
    textClass: 'text-slate-400',
  },
};

/**
 * Returns color tokens for a given label string.
 * Defaults to "Not assessed" style if label is unknown or missing.
 *
 * @param {string} label
 * @returns {Object}
 */
export function getLabelColorConfig(label) {
  if (!label) return HAZARD_LABEL_COLORS[HAZARD_LABELS.NOT_ASSESSED];

  // Direct match
  if (HAZARD_LABEL_COLORS[label]) {
    return HAZARD_LABEL_COLORS[label];
  }

  // Case-insensitive fallback
  const lower = label.toLowerCase();
  if (lower.includes('safe')) return HAZARD_LABEL_COLORS[HAZARD_LABELS.SAFE_CANDIDATE];
  if (lower.includes('caution')) return HAZARD_LABEL_COLORS[HAZARD_LABELS.CAUTION];
  if (lower.includes('unsafe')) return HAZARD_LABEL_COLORS[HAZARD_LABELS.UNSAFE_CANDIDATE];
  return HAZARD_LABEL_COLORS[HAZARD_LABELS.NOT_ASSESSED];
}

/**
 * Backend hazard class (enum value) -> display label.
 */
export const CLASS_TO_LABEL = {
  safe: HAZARD_LABELS.SAFE_CANDIDATE,
  caution: HAZARD_LABELS.CAUTION,
  unsafe: HAZARD_LABELS.UNSAFE_CANDIDATE,
};

/**
 * Human-readable height method text. Fallback is always flagged low confidence.
 */
export function describeHeightMethod(method) {
  if (method === HEIGHT_METHODS.SHADOW || method === 'shadow') return 'Shadow geometry';
  if (method === HEIGHT_METHODS.DIAMETER_FALLBACK) return 'Diameter-based fallback (low confidence)';
  return 'Unavailable';
}

function normalizeMethod(m) {
  if (!m) return null;
  return m === 'shadow' ? HEIGHT_METHODS.SHADOW : m;
}

/**
 * Normalizes one detection. `measurement` is the matching entry of measurements[]
 * (joined by detection_id); it carries diameter, height, method and confidence.
 */
export function normalizeBoulder(raw, measurement = null) {
  if (!raw) return null;
  const m = measurement || {};
  return {
    id: raw[BACKEND_FIELDS.BOULDER_ID],
    bbox: Array.isArray(raw[BACKEND_FIELDS.BOULDER_BBOX]) ? raw[BACKEND_FIELDS.BOULDER_BBOX] : [0, 0, 0, 0],
    confidence: raw[BACKEND_FIELDS.BOULDER_CONFIDENCE] ?? 0,
    polygon: Array.isArray(raw.polygon) ? raw.polygon : null,
    diameterM: m.diameter_m ?? raw[BACKEND_FIELDS.BOULDER_DIAMETER] ?? raw.size_m ?? null,
    shadowLengthM: raw[BACKEND_FIELDS.BOULDER_SHADOW_LENGTH] ?? null,
    shadowLengthPx: m.shadow_length_px ?? null,
    heightM: m.height_m ?? raw[BACKEND_FIELDS.BOULDER_HEIGHT] ?? null,
    heightMethod: normalizeMethod(m.method ?? raw[BACKEND_FIELDS.BOULDER_HEIGHT_METHOD]),
    heightUncertaintyM: m.height_uncertainty_m ?? raw[BACKEND_FIELDS.BOULDER_HEIGHT_UNCERTAINTY] ?? null,
    measurementConfidence: m.confidence ?? null,
    isHazardous: m.is_hazardous ?? null,
    measurementWarnings: Array.isArray(m.warnings) ? m.warnings : [],
  };
}

/**
 * Normalizes one hazard cell. Prefers the real backend names (p_hazard, class, ...)
 * and falls back to the frontend-compatible aliases the backend also sends.
 */
export function normalizeCell(raw) {
  if (!raw) return null;
  const cls = raw.class ?? raw.class_ ?? null;
  const prob = raw.p_hazard ?? raw[BACKEND_FIELDS.CELL_PROBABILITY] ?? null;
  const label =
    (cls && CLASS_TO_LABEL[cls]) || raw[BACKEND_FIELDS.CELL_LABEL] || HAZARD_LABELS.NOT_ASSESSED;
  return {
    row: raw[BACKEND_FIELDS.CELL_ROW],
    col: raw[BACKEND_FIELDS.CELL_COL],
    probability: prob,
    intervalLow: raw[BACKEND_FIELDS.CELL_INTERVAL_LOW] ?? null,
    intervalHigh: raw[BACKEND_FIELDS.CELL_INTERVAL_HIGH] ?? null,
    label,
    rawCount:
      raw.raw_boulder_count ?? raw[BACKEND_FIELDS.CELL_RAW_COUNT] ?? raw.boulder_count ?? null,
    correctedCount:
      raw.corrected_boulder_count ?? raw[BACKEND_FIELDS.CELL_CORRECTED_COUNT] ?? null,
    hazardousCount: raw.hazardous_boulder_count ?? null,
    // largest_boulder_m is a size (diameter); largest_height_m is a height. Never mix them.
    largestHeightM: raw[BACKEND_FIELDS.CELL_LARGEST_HEIGHT] ?? null,
    largestBoulderM: raw.largest_boulder_m ?? null,
    slopeDeg: raw[BACKEND_FIELDS.CELL_SLOPE] ?? null,
    slopeGate: raw.slope_gate ?? null,
    slopeStatus: raw[BACKEND_FIELDS.CELL_SLOPE_STATUS] ?? raw.slope_gate ?? null,
    recallCorrected: Boolean(raw.recall_corrected),
    explanation: raw.explanation || '',
    reasons: Array.isArray(raw.reasons) ? raw.reasons : [],
    missingInputs: Array.isArray(raw.missing_inputs) ? raw.missing_inputs : [],
  };
}

/**
 * Normalizes the full /api/analyze (or sampleResult.json) payload.
 * measurements[] are joined to detections by detection_id.
 */
export function normalizeResult(raw) {
  if (!raw) {
    return { image: null, detections: [], hazardCells: [], warnings: [], isMock: true };
  }

  const rawCells = raw[BACKEND_FIELDS.HAZARD_CELLS] || [];
  const rawDetections = raw[BACKEND_FIELDS.DETECTIONS] || [];
  const byId = new Map(
    (Array.isArray(raw.measurements) ? raw.measurements : []).map((m) => [m.detection_id, m])
  );

  return {
    image: raw[BACKEND_FIELDS.IMAGE] || null,
    detections: Array.isArray(rawDetections)
      ? rawDetections.map((d) => normalizeBoulder(d, byId.get(d[BACKEND_FIELDS.BOULDER_ID])))
      : [],
    hazardCells: Array.isArray(rawCells) ? rawCells.map(normalizeCell) : [],
    warnings: Array.isArray(raw[BACKEND_FIELDS.WARNINGS]) ? raw[BACKEND_FIELDS.WARNINGS] : [],
    isMock: raw.is_mock === undefined ? true : Boolean(raw.is_mock),
  };
}
