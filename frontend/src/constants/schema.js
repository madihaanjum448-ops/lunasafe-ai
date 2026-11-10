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
  SHADOW: 'shadow',
  DIAMETER_FALLBACK: 'diameter_fallback',
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
 * Normalizes a single raw boulder detection from the backend.
 *
 * @param {Object} raw
 * @returns {Object|null}
 */
export function normalizeBoulder(raw) {
  if (!raw) return null;
  return {
    id: raw[BACKEND_FIELDS.BOULDER_ID],
    bbox: Array.isArray(raw[BACKEND_FIELDS.BOULDER_BBOX]) ? raw[BACKEND_FIELDS.BOULDER_BBOX] : [0, 0, 0, 0],
    confidence: raw[BACKEND_FIELDS.BOULDER_CONFIDENCE] ?? 0,
    diameterM: raw[BACKEND_FIELDS.BOULDER_DIAMETER] ?? null,
    shadowLengthM: raw[BACKEND_FIELDS.BOULDER_SHADOW_LENGTH] ?? null,
    heightM: raw[BACKEND_FIELDS.BOULDER_HEIGHT] ?? null,
    heightMethod: raw[BACKEND_FIELDS.BOULDER_HEIGHT_METHOD] ?? null,
    heightUncertaintyM: raw[BACKEND_FIELDS.BOULDER_HEIGHT_UNCERTAINTY] ?? null,
  };
}

/**
 * Normalizes a single raw hazard grid cell from the backend.
 *
 * @param {Object} raw
 * @returns {Object|null}
 */
export function normalizeCell(raw) {
  if (!raw) return null;
  return {
    row: raw[BACKEND_FIELDS.CELL_ROW],
    col: raw[BACKEND_FIELDS.CELL_COL],
    probability: raw[BACKEND_FIELDS.CELL_PROBABILITY] ?? null,
    intervalLow: raw[BACKEND_FIELDS.CELL_INTERVAL_LOW] ?? null,
    intervalHigh: raw[BACKEND_FIELDS.CELL_INTERVAL_HIGH] ?? null,
    label: raw[BACKEND_FIELDS.CELL_LABEL] || HAZARD_LABELS.NOT_ASSESSED,
    rawCount: raw[BACKEND_FIELDS.CELL_RAW_COUNT] ?? null,
    correctedCount: raw[BACKEND_FIELDS.CELL_CORRECTED_COUNT] ?? null,
    largestHeightM: raw[BACKEND_FIELDS.CELL_LARGEST_HEIGHT] ?? null,
    slopeDeg: raw[BACKEND_FIELDS.CELL_SLOPE] ?? null,
    slopeStatus: raw[BACKEND_FIELDS.CELL_SLOPE_STATUS] ?? null,
  };
}

/**
 * Normalizes the full mission result payload.
 *
 * @param {Object} raw
 * @returns {Object}
 */
export function normalizeResult(raw) {
  if (!raw) {
    return {
      image: null,
      detections: [],
      hazardCells: [],
      warnings: [],
    };
  }

  const rawCells = raw[BACKEND_FIELDS.HAZARD_CELLS] || [];
  const rawDetections = raw[BACKEND_FIELDS.DETECTIONS] || [];

  return {
    image: raw[BACKEND_FIELDS.IMAGE] || null,
    detections: Array.isArray(rawDetections) ? rawDetections.map(normalizeBoulder) : [],
    hazardCells: Array.isArray(rawCells) ? rawCells.map(normalizeCell) : [],
    warnings: Array.isArray(raw[BACKEND_FIELDS.WARNINGS]) ? raw[BACKEND_FIELDS.WARNINGS] : [],
  };
}
