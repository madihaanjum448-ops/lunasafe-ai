/**
 * Boulder detection display constants for LunaSafe AI.
 * Change the thresholds here and every coloured box and legend updates automatically.
 */

// Confidence band thresholds (inclusive lower bound)
export const CONFIDENCE_HIGH_MIN = 0.75;  // [0.75, 1.00] → high
export const CONFIDENCE_MED_MIN  = 0.50;  // [0.50, 0.75) → medium
//                                         // [0.00, 0.50) → low

// SVG fill/stroke colours per band (normal / hovered / selected states)
export const BAND_STYLES = {
  high: {
    label:          'High',
    labelRange:     '≥ 75%',
    // emerald / green
    fill:           'rgba(34,  197, 94,  0.14)',
    fillHovered:    'rgba(34,  197, 94,  0.28)',
    fillSelected:   'rgba(34,  197, 94,  0.42)',
    stroke:         '#22c55e',
    strokeHovered:  '#86efac',
    strokeSelected: '#4ade80',
    textFill:       '#86efac',
    swatchBg:       'bg-emerald-500/30',
    swatchBorder:   'border-emerald-400',
    textClass:      'text-emerald-300',
  },
  medium: {
    label:          'Medium',
    labelRange:     '50 – 75%',
    // amber / yellow
    fill:           'rgba(234, 179, 8,   0.14)',
    fillHovered:    'rgba(234, 179, 8,   0.28)',
    fillSelected:   'rgba(234, 179, 8,   0.44)',
    stroke:         '#eab308',
    strokeHovered:  '#fef08a',
    strokeSelected: '#facc15',
    textFill:       '#fde047',
    swatchBg:       'bg-amber-500/30',
    swatchBorder:   'border-amber-400',
    textClass:      'text-amber-300',
  },
  low: {
    label:          'Low',
    labelRange:     '< 50%',
    // rose / red
    fill:           'rgba(239, 68,  68,  0.14)',
    fillHovered:    'rgba(239, 68,  68,  0.28)',
    fillSelected:   'rgba(239, 68,  68,  0.44)',
    stroke:         '#ef4444',
    strokeHovered:  '#fca5a5',
    strokeSelected: '#f87171',
    textFill:       '#fca5a5',
    swatchBg:       'bg-red-500/30',
    swatchBorder:   'border-red-400',
    textClass:      'text-red-300',
  },
};

/**
 * Returns the BAND_STYLES key ('high' | 'medium' | 'low') for a given confidence value.
 * @param {number} confidence  0.00 – 1.00
 * @returns {'high'|'medium'|'low'}
 */
export function confidenceBand(confidence) {
  if (confidence >= CONFIDENCE_HIGH_MIN) return 'high';
  if (confidence >= CONFIDENCE_MED_MIN)  return 'medium';
  return 'low';
}
