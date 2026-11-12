import React from 'react';
import { useMission } from '../context/useMission';

const FIELDS = [
  { key: 'lander_footprint_diameter_m', label: 'Footprint diameter (m)', min: 0.1, step: 0.5 },
  { key: 'hazard_height_threshold_m', label: 'Hazardous boulder height (m)', min: 0.05, step: 0.05 },
  { key: 'slope_gate_deg', label: 'Slope gate (°)', min: 0, max: 90, step: 1 },
];

/**
 * Inputs for the analysis thresholds sent in the `config` field of /api/analyze.
 * Empty = backend default. These are placeholders, not validated landing limits.
 */
export default function ThresholdControls({ showRun = false }) {
  const { thresholds, setThreshold, resetThresholds, analysisConfig, runAnalysis, loading, resultSource } =
    useMission();

  const canRerun = showRun && resultSource !== 'precomputed';

  return (
    <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3 text-xs">
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-sm font-semibold text-slate-200">Analysis thresholds</h4>
        <button
          type="button"
          onClick={resetThresholds}
          className="text-[11px] text-cyan-300 hover:text-white underline underline-offset-2"
        >
          Reset to defaults
        </button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        {FIELDS.map((f) => (
          <label key={f.key} className="space-y-1">
            <span className="text-slate-400">{f.label}</span>
            <input
              type="number"
              min={f.min}
              max={f.max}
              step={f.step}
              value={thresholds[f.key] ?? ''}
              placeholder={analysisConfig ? String(analysisConfig[f.key]) : 'default'}
              onChange={(e) => setThreshold(f.key, e.target.value)}
              className="w-full px-2 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-100 font-mono"
            />
          </label>
        ))}
      </div>
      <p className="text-[11px] text-slate-400 leading-snug">
        Placeholder values, not validated limits. Empty fields use the backend defaults.
      </p>
      {showRun && (
        <button
          type="button"
          onClick={runAnalysis}
          disabled={loading || !canRerun}
          className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium disabled:opacity-40"
        >
          {canRerun ? 'Re-run analysis with these thresholds' : 'Re-run unavailable for saved results'}
        </button>
      )}
    </div>
  );
}
