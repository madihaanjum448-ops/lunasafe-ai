import React from 'react';
import { useMission } from '../context/useMission';

/**
 * Format helper adhering strictly to: "If a value is null, show 'Unavailable'"
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
  const { selectedCell, setSelectedCell, hazardCells, imageMeta } = useMission();

  if (!imageMeta.isSample) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 text-center text-slate-400 flex flex-col items-center justify-center min-h-[300px]">
        <div className="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 mb-3">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h4 className="text-slate-200 font-semibold text-sm">Hazard Evaluation Pending</h4>
        <p className="text-xs text-amber-300/90 mt-1 max-w-xs font-mono">
          Not processed yet. The analysis backend is not connected.
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
        <h4 className="text-slate-200 font-semibold text-sm">Select a Hazard Cell</h4>
        <p className="text-xs text-slate-400 mt-1 max-w-xs">
          Click on any grid cell on the hazard map to inspect terrain safety metrics, boulder density, and landing recommendations.
        </p>
      </div>
    );
  }

  // Safety class badge styling
  const getClassBadge = (cellClass) => {
    switch (cellClass) {
      case 'safe':
        return (
          <span className="px-2.5 py-1 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-mono text-xs font-bold uppercase tracking-wider">
            Safe Landing Zone
          </span>
        );
      case 'caution':
        return (
          <span className="px-2.5 py-1 rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/40 font-mono text-xs font-bold uppercase tracking-wider">
            Caution Advised
          </span>
        );
      case 'unsafe':
      default:
        return (
          <span className="px-2.5 py-1 rounded-md bg-red-500/20 text-red-300 border border-red-500/40 font-mono text-xs font-bold uppercase tracking-wider">
            Unsafe / High Hazard
          </span>
        );
    }
  };

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

  // Physical ground coverage calculation if scale is available
  const cellPxWidth = imageMeta.width / 8;
  const cellPxHeight = imageMeta.height / 8;
  const groundMeters =
    imageMeta.pixelScaleM !== null
      ? `${(cellPxWidth * imageMeta.pixelScaleM).toFixed(0)}m × ${(cellPxHeight * imageMeta.pixelScaleM).toFixed(0)}m`
      : 'Unavailable';

  return (
    <aside className="bg-slate-900/95 border border-slate-800 rounded-2xl p-5 backdrop-blur-md shadow-2xl flex flex-col gap-4 text-sm animate-in fade-in slide-in-from-right-4 duration-200">
      {/* Header with Coordinates and Close */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700">
              Sector [R{selectedCell.row}, C{selectedCell.col}]
            </span>
            <span className="text-slate-400 text-xs">Cell #{currentIndex + 1} of 64</span>
          </div>
          <h3 className="text-base font-bold text-white mt-1">Region Safety Assessment</h3>
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

      {/* Safety Class Badge & Hazard Score */}
      <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-between">
        <div>
          <span className="text-xs text-slate-400 block mb-1">Safety Classification</span>
          {getClassBadge(selectedCell.class)}
        </div>

        <div className="text-right">
          <span className="text-xs text-slate-400 block mb-1">Hazard Score</span>
          <div className="text-xl font-bold font-mono text-white">
            {selectedCell.score !== null && selectedCell.score !== undefined ? (
              <span className={selectedCell.score > 0.7 ? 'text-red-400' : selectedCell.score > 0.35 ? 'text-amber-400' : 'text-emerald-400'}>
                {selectedCell.score.toFixed(2)}
              </span>
            ) : (
              displayValue(null)
            )}
          </div>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 gap-2.5">
        {/* Boulder Count */}
        <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800/80">
          <div className="text-[11px] text-slate-400 uppercase tracking-wider mb-1 flex items-center gap-1">
            <svg className="w-3.5 h-3.5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            Boulder Count
          </div>
          <div className="text-base font-mono">
            {displayValue(selectedCell.boulder_count)}
          </div>
        </div>

        {/* Largest Boulder */}
        <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800/80">
          <div className="text-[11px] text-slate-400 uppercase tracking-wider mb-1 flex items-center gap-1">
            <svg className="w-3.5 h-3.5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
            </svg>
            Largest Boulder
          </div>
          <div className="text-base font-mono">
            {displayValue(selectedCell.largest_boulder_m, 'm')}
          </div>
        </div>

        {/* Boulder Density */}
        <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800/80">
          <div className="text-[11px] text-slate-400 uppercase tracking-wider mb-1 flex items-center gap-1">
            <svg className="w-3.5 h-3.5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
            </svg>
            Boulder Density
          </div>
          <div className="text-base font-mono">
            {displayValue(selectedCell.density, 'boulders/100m²')}
          </div>
        </div>

        {/* Ground Footprint */}
        <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800/80">
          <div className="text-[11px] text-slate-400 uppercase tracking-wider mb-1 flex items-center gap-1">
            <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
            Cell Ground Area
          </div>
          <div className="text-xs font-mono text-slate-200">
            {groundMeters}
          </div>
        </div>
      </div>

      {/* Explanation Text */}
      <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800">
        <span className="text-xs font-semibold text-slate-300 block mb-1.5 flex items-center gap-1.5">
          <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Terrain Analysis & Explanation
        </span>
        <p className="text-xs text-slate-300 leading-relaxed">
          {selectedCell.explanation || <span className="text-amber-400 italic">Unavailable</span>}
        </p>
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
