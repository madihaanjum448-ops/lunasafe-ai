import React from 'react';
import { useMission } from '../context/useMission';
import { HAZARD_LABELS, CANDIDATE_ONLY_NOTE } from '../constants/schema';
import ResultBadge from './ResultBadge';

export default function HazardLegend() {
  const {
    hazardCells,
    showHeatmap,
    setShowHeatmap,
    showDetectionsInHazardMap,
    setShowDetectionsInHazardMap,
    hasResult,
    loading,
    apiError,
  } = useMission();

  if (!hasResult) {
    return (
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 backdrop-blur-sm shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 text-slate-300">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
          <span className="font-semibold text-slate-200">Hazard Heatmap Layer:</span>
          <span className="text-amber-300 font-mono">{loading ? 'Working…' : apiError ? `Not processed: ${apiError}` : 'Not processed yet. Run the analysis on the Upload page.'}</span>
        </div>
        <span className="text-slate-400 text-[11px]">0 cells available</span>
      </div>
    );
  }

  const safeCount = hazardCells.filter((c) => c.label === HAZARD_LABELS.SAFE_CANDIDATE).length;
  const cautionCount = hazardCells.filter((c) => c.label === HAZARD_LABELS.CAUTION).length;
  const unsafeCount = hazardCells.filter((c) => c.label === HAZARD_LABELS.UNSAFE_CANDIDATE).length;
  const notAssessedCount = hazardCells.filter((c) => c.label === HAZARD_LABELS.NOT_ASSESSED).length;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 backdrop-blur-sm shadow-xl space-y-4">
      {/* Header with Title and Visible Mock Data Badge */}
      <div className="flex items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <h3 className="font-semibold text-slate-100 text-sm">Hazard Evaluation Legend</h3>
        </div>

        <ResultBadge />
      </div>

      {/* Layer Toggles */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-950/60 p-3 rounded-lg border border-slate-800">
        <label className="flex items-center gap-2.5 cursor-pointer text-xs font-medium text-slate-200">
          <input
            type="checkbox"
            checked={showHeatmap}
            onChange={(e) => setShowHeatmap(e.target.checked)}
            className="w-4 h-4 rounded border-slate-700 bg-slate-800 text-cyan-500 focus:ring-cyan-500/50 accent-cyan-500"
          />
          <span>Show Hazard Heatmap Layer (8×8 Grid)</span>
        </label>

        <label className="flex items-center gap-2.5 cursor-pointer text-xs font-medium text-slate-400 hover:text-slate-200">
          <input
            type="checkbox"
            checked={showDetectionsInHazardMap}
            onChange={(e) => setShowDetectionsInHazardMap(e.target.checked)}
            className="w-4 h-4 rounded border-slate-700 bg-slate-800 text-cyan-500 focus:ring-cyan-500/50 accent-cyan-500"
          />
          <span>Overlay Boulder Boxes</span>
        </label>
      </div>

      {/* Legend Classes Breakdown - 4 Labels */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Safe candidate */}
        <div className="flex items-start gap-3 p-2.5 rounded-lg bg-emerald-950/20 border border-emerald-500/30">
          <div className="w-5 h-5 rounded bg-emerald-500/40 border-2 border-emerald-400 flex-shrink-0 mt-0.5"></div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-emerald-300 uppercase tracking-wide">
                {HAZARD_LABELS.SAFE_CANDIDATE}
              </span>
              <span className="text-[11px] font-mono text-emerald-400 bg-emerald-900/40 px-1.5 py-0.2 rounded font-semibold">
                {safeCount} cells
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">
              Low estimated hazard probability; sparse or small obstacles.
            </p>
          </div>
        </div>

        {/* Caution */}
        <div className="flex items-start gap-3 p-2.5 rounded-lg bg-amber-950/20 border border-amber-500/30">
          <div className="w-5 h-5 rounded bg-amber-500/40 border-2 border-amber-400 flex-shrink-0 mt-0.5"></div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-amber-300 uppercase tracking-wide">
                {HAZARD_LABELS.CAUTION}
              </span>
              <span className="text-[11px] font-mono text-amber-400 bg-amber-900/40 px-1.5 py-0.2 rounded font-semibold">
                {cautionCount} cells
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">
              Moderate hazard probability or missing data (e.g. slope unavailable).
            </p>
          </div>
        </div>

        {/* Unsafe candidate */}
        <div className="flex items-start gap-3 p-2.5 rounded-lg bg-red-950/20 border border-red-500/30">
          <div className="w-5 h-5 rounded bg-red-500/40 border-2 border-red-400 flex-shrink-0 mt-0.5"></div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-red-300 uppercase tracking-wide">
                {HAZARD_LABELS.UNSAFE_CANDIDATE}
              </span>
              <span className="text-[11px] font-mono text-red-400 bg-red-900/40 px-1.5 py-0.2 rounded font-semibold">
                {unsafeCount} cells
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">
              High hazard probability; dense boulder fields or steep grades.
            </p>
          </div>
        </div>

        {/* Not assessed */}
        <div className="flex items-start gap-3 p-2.5 rounded-lg bg-slate-900/60 border border-slate-700">
          <div className="w-5 h-5 rounded bg-slate-700/50 border-2 border-dashed border-slate-400 flex-shrink-0 mt-0.5"></div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wide">
                {HAZARD_LABELS.NOT_ASSESSED}
              </span>
              <span className="text-[11px] font-mono text-slate-400 bg-slate-800 px-1.5 py-0.2 rounded font-semibold">
                {notAssessedCount} cells
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">
              Incomplete sensor coverage or unmeasured sector terrain.
            </p>
          </div>
        </div>
      </div>

      {/* Mandatory Candidate Advisory Note */}
      <div className="pt-2 border-t border-slate-800/80 flex items-center gap-2 text-xs text-amber-300/90 bg-amber-950/20 p-2.5 rounded-lg border border-amber-500/20">
        <svg className="w-4 h-4 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="font-medium">{CANDIDATE_ONLY_NOTE}</span>
      </div>
    </div>
  );
}
