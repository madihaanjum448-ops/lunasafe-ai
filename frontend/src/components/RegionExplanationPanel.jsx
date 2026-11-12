import React from 'react';
import { useMission } from '../context/useMission';
import {
  HAZARD_LABELS,
  HEIGHT_METHODS,
  describeHeightMethod,
  getLabelColorConfig,
  CANDIDATE_ONLY_NOTE,
} from '../constants/schema';
import ResultBadge from './ResultBadge';

/**
 * Format helper adhering strictly to: "Unavailable values are null. NEVER replace null with a made-up number; show 'Unavailable'."
 */
function displayValue(val, unit = '') {
  if (val === null || val === undefined) {
    return <span className="text-amber-400/90 font-mono italic">Unavailable</span>;
  }
  return (
    <span className="font-mono text-slate-100 font-semibold">
      {val}
      {unit ? <span className="text-slate-400 font-normal text-xs ml-1">{unit}</span> : ''}
    </span>
  );
}

export default function RegionExplanationPanel() {
  const {
    selectedCell,
    setSelectedCell,
    hazardCells,
    detections,
    imageMeta,
    hasResult,
    loading,
    loadingLabel,
    apiError,
    analysisConfig,
    missingMetadata,
  } = useMission();

  if (!hasResult) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 text-center text-slate-400 flex flex-col items-center justify-center min-h-[300px]">
        <div className="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 mb-3">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h4 className="text-slate-200 font-semibold text-sm">Hazard Evaluation Pending</h4>
        <p className="text-xs text-amber-300/90 mt-1 max-w-xs font-mono">
          {loading
            ? loadingLabel || 'Working…'
            : apiError
              ? `Not processed: ${apiError}`
              : 'Not processed yet. Upload an image and run the analysis on the Upload page.'}
        </p>
      </div>
    );
  }

  if (!selectedCell) {
    return (
      <div className="bg-slate-900/60 border border-dashed border-slate-800 rounded-xl p-6 text-center text-slate-400 flex flex-col items-center justify-center min-h-[300px]">
        <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center text-slate-500 mb-3">
          <svg className="w-6 h-6 text-cyan-400/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
          </svg>
        </div>
        <h4 className="text-slate-200 font-semibold text-sm">Select a Region Cell</h4>
        <p className="text-xs text-slate-400 mt-1 max-w-xs leading-relaxed">
          Click any grid cell on the hazard map to inspect candidate region classification, probability, boulder counts, and slope telemetry.
        </p>
      </div>
    );
  }

  // Find adjacent cells for quick navigation
  const currentIndex = hazardCells.findIndex(
    (c) => c.row === selectedCell.row && c.col === selectedCell.col
  );

  const handlePrev = () => {
    if (currentIndex > 0) {
      setSelectedCell(hazardCells[currentIndex - 1]);
    }
  };

  const handleNext = () => {
    if (currentIndex < hazardCells.length - 1) {
      setSelectedCell(hazardCells[currentIndex + 1]);
    }
  };

  // Detections whose centre falls inside the selected cell (approximate, for height method display)
  const gridRows = Math.max(...hazardCells.map((c) => c.row)) + 1;
  const gridCols = Math.max(...hazardCells.map((c) => c.col)) + 1;
  const cellDetections = detections.filter((d) => {
    if (!d || !imageMeta.width || !imageMeta.height) return false;
    const cx = (d.bbox[0] + d.bbox[2]) / 2;
    const cy = (d.bbox[1] + d.bbox[3]) / 2;
    const r = Math.min(gridRows - 1, Math.floor(cy / (imageMeta.height / gridRows)));
    const c = Math.min(gridCols - 1, Math.floor(cx / (imageMeta.width / gridCols)));
    return r === selectedCell.row && c === selectedCell.col;
  });
  const withHeight = cellDetections
    .filter((d) => d.heightM !== null && d.heightM !== undefined)
    .sort((a, b) => b.heightM - a.heightM);
  const tallest = withHeight[0] || null;
  const displayHeight = selectedCell.largestHeightM ?? (tallest ? tallest.heightM : null);
  const fallbackCount = withHeight.filter((d) => d.heightMethod === HEIGHT_METHODS.DIAMETER_FALLBACK).length;

  const missingInputs = Array.from(
    new Set([...(selectedCell.missingInputs || []), ...(missingMetadata || [])])
  );
  const gateText = { pass: 'Pass', fail: 'Fail', not_assessed: 'Not assessed' };

  const config = getLabelColorConfig(selectedCell.label);
  const isNotAssessed = selectedCell.label === HAZARD_LABELS.NOT_ASSESSED || selectedCell.probability === null;

  // Derive region-specific warnings
  const regionWarnings = [];
  if (isNotAssessed) {
    regionWarnings.push('Region coverage incomplete; probability calculation cannot be performed.');
  }
  if (selectedCell.slopeDeg === null || selectedCell.slopeDeg === undefined) {
    regionWarnings.push('Slope data unavailable for this sector; classified as Caution.');
  }
  if (selectedCell.largestHeightM === null && selectedCell.rawCount > 0) {
    regionWarnings.push('Boulder height measurement unavailable for detected obstacles.');
  }
  if (selectedCell.slopeDeg !== null && selectedCell.slopeDeg > 15) {
    regionWarnings.push(`High slope gradient (${selectedCell.slopeDeg}°) exceeds nominal touchdown threshold.`);
  }

  return (
    <aside className="bg-slate-900/95 border border-slate-800 rounded-2xl p-5 backdrop-blur-md shadow-2xl flex flex-col gap-4 text-sm animate-in fade-in slide-in-from-right-4 duration-200">
      {/* Header with Coordinates, Mock Data Badge, and Close */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700">
              Sector [R{selectedCell.row}, C{selectedCell.col}]
            </span>
            <span className="text-slate-400 text-xs">Cell #{currentIndex + 1} of {hazardCells.length}</span>
            <ResultBadge />
          </div>
          <h3 className="text-base font-bold text-white">Region Evaluation Details</h3>
        </div>

        <button
          onClick={() => setSelectedCell(null)}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          title="Close panel"
          aria-label="Close details panel"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Candidate Advisory Note */}
      <div className="p-2.5 rounded-lg bg-amber-950/20 border border-amber-500/30 text-amber-300/90 text-xs flex items-center gap-2">
        <svg className="w-4 h-4 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="font-medium text-[11px] leading-tight">{CANDIDATE_ONLY_NOTE}</span>
      </div>

      {/* 1. Hazard Section */}
      <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-cyan-400" />
            Hazard
          </span>
          <span className={`px-2.5 py-1 rounded-md font-mono text-xs font-bold uppercase tracking-wider ${config.badgeClass}`}>
            {selectedCell.label}
          </span>
        </div>

        <div className="pt-1.5 border-t border-slate-800/80 text-xs">
          <span className="text-[11px] text-slate-400 block mb-1">Hazard Probability:</span>
          {!isNotAssessed && selectedCell.probability !== null ? (
            <div className="font-mono text-white text-lg font-bold">
              {(selectedCell.probability * 100).toFixed(0)}%
              {selectedCell.intervalLow !== null && selectedCell.intervalHigh !== null && (
                <span className="text-slate-400 font-normal text-xs ml-2">
                  ({(selectedCell.intervalLow * 100).toFixed(0)}% to {(selectedCell.intervalHigh * 100).toFixed(0)}%)
                </span>
              )}
            </div>
          ) : (
            <div className="text-amber-400/90 font-mono text-xs leading-relaxed">
              Not assessed — probability unavailable due to incomplete sensor coverage or boundary limits.
            </div>
          )}
        </div>
      </div>

      {/* 2. Boulders Section */}
      <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
          <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          Boulders
        </span>

        <div className="grid grid-cols-2 gap-3 pt-1 text-xs">
          <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80">
            <span className="text-[11px] text-slate-400 block mb-0.5">Raw Count</span>
            <div className="text-base font-mono">
              {displayValue(selectedCell.rawCount)}
            </div>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80">
            <span className="text-[11px] text-slate-400 block mb-0.5">Corrected Count</span>
            <div className="text-base font-mono">
              {displayValue(selectedCell.correctedCount)}
            </div>
          </div>
        </div>

        {selectedCell.rawCount === 0 && (
          <p className="text-[11px] text-emerald-300/90 font-mono">
            Processed: no boulders detected in this region.
          </p>
        )}
        {(selectedCell.rawCount === null || selectedCell.rawCount === undefined) && (
          <p className="text-[11px] text-amber-300/90 font-mono">Not processed: counts unavailable.</p>
        )}
        <p className="text-[11px] text-slate-400 leading-snug pt-0.5 italic">
          Corrected for detection recall (adjusts raw detections for estimated model recall rate under lighting and resolution limits).
        </p>
      </div>

      {/* 3. Height & 4. Slope Grid */}
      <div className="grid grid-cols-2 gap-2.5">
        {/* Height Section */}
        <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1.5">
          <span className="text-[11px] text-slate-400 uppercase tracking-wider block font-semibold flex items-center gap-1">
            <svg className="w-3.5 h-3.5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
            </svg>
            Height
          </span>
          <div>
            <span className="text-[11px] text-slate-400 block">Largest Height:</span>
            {displayHeight !== null && displayHeight !== undefined ? (
              <span className="font-mono text-slate-100 font-bold text-base">
                {displayHeight} m
              </span>
            ) : (
              <span className="text-amber-400 italic text-xs font-mono">Height unavailable</span>
            )}
          </div>
          <div className="text-[11px] font-mono text-slate-400">
            Method:{' '}
            <span className="text-slate-200 font-semibold">
              {tallest ? describeHeightMethod(tallest.heightMethod) : 'Unavailable'}
            </span>
          </div>
          {fallbackCount > 0 && (
            <div className="text-[11px] font-mono text-amber-300">
              {fallbackCount} height{fallbackCount > 1 ? 's' : ''} in this region use the diameter-based
              fallback (low confidence).
            </div>
          )}
          {tallest && tallest.heightUncertaintyM !== null && tallest.heightUncertaintyM !== undefined && (
            <div className="text-[11px] font-mono text-slate-400">±{tallest.heightUncertaintyM} m</div>
          )}
        </div>

        {/* Slope Section */}
        <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1.5">
          <span className="text-[11px] text-slate-400 uppercase tracking-wider block font-semibold flex items-center gap-1">
            <svg className="w-3.5 h-3.5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
            Slope
          </span>
          <div>
            <span className="text-[11px] text-slate-400 block">Gradient:</span>
            {selectedCell.slopeDeg !== null && selectedCell.slopeDeg !== undefined ? (
              <span className="font-mono text-slate-100 font-bold text-base">
                {selectedCell.slopeDeg}°
              </span>
            ) : (
              <span className="text-amber-400 italic text-xs font-mono">Slope unavailable</span>
            )}
          </div>
          <div className="text-[11px] font-mono text-slate-400">
            Slope gate:{' '}
            <span className="text-slate-200 font-semibold">
              {gateText[selectedCell.slopeGate] || selectedCell.slopeStatus || 'Unavailable'}
            </span>
          </div>
        </div>
      </div>

      {/* Explanation, reasons, thresholds, missing inputs */}
      <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2.5 text-xs">
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Why this result</span>
        {selectedCell.explanation ? (
          <p className="text-slate-300 leading-snug">{selectedCell.explanation}</p>
        ) : (
          <p className="text-amber-400 italic font-mono">No explanation provided by the backend.</p>
        )}
        {selectedCell.reasons.length > 0 && (
          <ul className="space-y-1">
            {selectedCell.reasons.map((r) => (
              <li key={r} className="font-mono text-[11px] text-slate-400">• {r}</li>
            ))}
          </ul>
        )}
        <div>
          <span className="text-[11px] text-slate-400 block mb-0.5">Missing inputs:</span>
          {missingInputs.length === 0 ? (
            <span className="font-mono text-[11px] text-emerald-300">None</span>
          ) : (
            <span className="font-mono text-[11px] text-amber-300">{missingInputs.join(', ')}</span>
          )}
        </div>
        <div>
          <span className="text-[11px] text-slate-400 block mb-0.5">Thresholds used (placeholders, not validated):</span>
          {analysisConfig ? (
            <ul className="font-mono text-[11px] text-slate-300 space-y-0.5">
              <li>Footprint diameter: {analysisConfig.lander_footprint_diameter_m} m</li>
              <li>Hazardous boulder height: {analysisConfig.hazard_height_threshold_m} m</li>
              <li>Slope gate: {analysisConfig.slope_gate_deg}°</li>
              <li>
                Caution at P ≥ {analysisConfig.caution_p_hazard}, Unsafe at P ≥ {analysisConfig.unsafe_p_hazard}
              </li>
            </ul>
          ) : (
            <span className="font-mono text-[11px] text-amber-400 italic">Unavailable (backend config not loaded)</span>
          )}
        </div>
      </div>

      {/* 5. Warnings Relevant to this Region */}
      <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
          <svg className="w-3.5 h-3.5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          Warnings Relevant to Region
        </span>

        {regionWarnings.length === 0 ? (
          <div className="flex items-center gap-2 text-xs text-emerald-400 pt-0.5">
            <svg className="w-4 h-4 text-emerald-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
            </svg>
            <span className="text-slate-300">No specific region warnings. All sensor inputs nominal.</span>
          </div>
        ) : (
          <ul className="space-y-1.5 text-xs pt-0.5">
            {regionWarnings.map((warning, idx) => (
              <li key={idx} className="flex items-start gap-2 text-amber-300 font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0 mt-1.5" />
                <span className="leading-snug">{warning}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Navigation Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-slate-800 text-xs">
        <button
          onClick={handlePrev}
          disabled={currentIndex <= 0}
          className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 disabled:pointer-events-none transition-colors flex items-center gap-1"
        >
          ← Prev Cell
        </button>

        <span className="text-slate-400 font-mono text-[11px]">
          [R{selectedCell.row}, C{selectedCell.col}]
        </span>

        <button
          onClick={handleNext}
          disabled={currentIndex >= hazardCells.length - 1}
          className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 disabled:pointer-events-none transition-colors flex items-center gap-1"
        >
          Next Cell →
        </button>
      </div>
    </aside>
  );
}
