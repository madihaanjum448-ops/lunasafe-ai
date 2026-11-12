import React, { useState } from 'react';
import ImageViewer from '../components/ImageViewer';
import DetectionOverlay from '../components/DetectionOverlay';
import HazardGridOverlay from '../components/HazardGridOverlay';
import ConfidenceSlider from '../components/ConfidenceSlider';
import WarningsBanner from '../components/WarningsBanner';
import { useMission } from '../context/useMission';
import { BAND_STYLES, CONFIDENCE_HIGH_MIN, CONFIDENCE_MED_MIN } from '../constants/detections';

/* ─────────────────────────────────────────────────────────────────
   LayersPanel
   Three toggles (boulder boxes / confidence labels / hazard heatmap)
   + a small per-band colour legend.  State lives in MissionContext so
   it persists when the user navigates to the Hazard Map page and back.
   ───────────────────────────────────────────────────────────────── */
function LayersPanel() {
  const {
    showBoulderBoxes,    setShowBoulderBoxes,
    showConfidenceLabels, setShowConfidenceLabels,
    showHeatmap,         setShowHeatmap,
  } = useMission();

  const toggleRow = (label, checked, onChange, sublabel = null) => (
    <label className="flex items-center gap-3 cursor-pointer group">
      <span className="relative flex-shrink-0">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="sr-only peer"
        />
        {/* Custom pill toggle */}
        <span
          className={`block w-9 h-5 rounded-full transition-colors duration-200 ${
            checked ? 'bg-cyan-500' : 'bg-slate-700'
          }`}
        />
        <span
          className={`absolute left-0.5 top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200 ${
            checked ? 'translate-x-4' : 'translate-x-0'
          }`}
        />
      </span>
      <span className="flex flex-col">
        <span className={`text-xs font-medium leading-tight ${checked ? 'text-slate-100' : 'text-slate-400'}`}>
          {label}
        </span>
        {sublabel && (
          <span className="text-[11px] text-slate-500 leading-tight">{sublabel}</span>
        )}
      </span>
    </label>
  );

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-lg space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
        <svg className="w-4 h-4 text-cyan-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
            d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
        <h3 className="text-sm font-semibold text-slate-100">Layers</h3>
      </div>

      {/* Toggle rows */}
      <div className="space-y-3">
        {toggleRow('Boulder boxes', showBoulderBoxes, setShowBoulderBoxes)}
        {toggleRow('Confidence labels', showConfidenceLabels, setShowConfidenceLabels,
          showBoulderBoxes ? null : 'Enable boulder boxes first')}
        {toggleRow('Hazard heatmap', showHeatmap, setShowHeatmap,
          'Hazard grid')}
      </div>

      {/* Confidence band colour legend */}
      <div className="border-t border-slate-800 pt-3 space-y-1.5">
        <span className="text-[11px] uppercase tracking-widest text-slate-500 font-semibold">
          Confidence bands
        </span>
        {Object.values(BAND_STYLES).map((b) => (
          <div key={b.label} className="flex items-center gap-2 text-xs">
            <span className={`w-4 h-4 rounded-sm border-2 flex-shrink-0 ${b.swatchBg} ${b.swatchBorder}`} />
            <span className={`font-medium ${b.textClass}`}>{b.label}</span>
            <span className="text-slate-500">{b.labelRange}</span>
          </div>
        ))}
        <p className="text-[11px] text-slate-500 leading-snug pt-0.5">
          Thresholds: high ≥ {(CONFIDENCE_HIGH_MIN * 100).toFixed(0)}%,
          medium ≥ {(CONFIDENCE_MED_MIN * 100).toFixed(0)}%.
        </p>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────
   DetectionsPage
   ───────────────────────────────────────────────────────────────── */
export default function DetectionsPage() {
  const {
    detections,
    confidenceThreshold,
    imageMeta,
    loadSampleData,
    showBoulderBoxes,
    showConfidenceLabels,
    hasResult,
    isMock,
    loading,
    apiError,
  } = useMission();

  const [selectedDetection, setSelectedDetection] = useState(null);

  const visibleDetections = detections.filter(
    (d) => d.confidence >= confidenceThreshold
  );

  // True when the sample is loaded but the slider has filtered out every box
  const allFilteredOut = hasResult && detections.length > 0 && visibleDetections.length === 0;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* ── Page Header ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase tracking-widest text-cyan-400 font-mono font-semibold">
              Obstacle Detection Module
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-mono">
              {hasResult ? (isMock ? 'Demo data' : 'Real AI result') : 'User Upload'}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            High-Resolution Boulder Detections
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
            {hasResult
              ? 'Pan and zoom across the landing site. Each detected surface hazard is framed with a confidence-coloured bounding box. Toggle layers and adjust the threshold using the controls below.'
              : 'Pan and zoom across your uploaded lunar image.'}
          </p>
        </div>

        {/* Summary badges (sample only) */}
        {hasResult && (
          <div className="flex items-center gap-2 self-start md:self-auto">
            <div className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs flex items-center gap-2">
              <span className="text-slate-400">Total Catalog:</span>
              <span className="font-mono font-bold text-white">{detections.length}</span>
            </div>
            <div className="px-3 py-1.5 rounded-xl bg-cyan-950/60 border border-cyan-500/40 text-xs flex items-center gap-2 text-cyan-300">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span className="font-mono font-bold">{visibleDetections.length} visible</span>
            </div>
          </div>
        )}
      </div>

      {/* ── "Not processed yet" banner for real uploads ── */}
      {!hasResult && (
        <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-500/50 text-amber-200 text-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-lg">
          <div className="flex items-center gap-3">
            <svg className="w-5 h-5 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <span className="font-semibold block sm:inline">
                {loading ? 'Working…' : apiError ? `Not processed: ${apiError}` : 'Not processed yet. Run the analysis on the Upload page.'}
              </span>
              <span className="text-xs text-amber-300/80 sm:ml-2 block sm:inline">
                Detections appear after you run the analysis.
              </span>
            </div>
          </div>
          <button
            onClick={loadSampleData}
            className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-cyan-300 hover:text-white border border-slate-700 text-xs font-medium whitespace-nowrap transition-colors self-start sm:self-auto"
          >
            Load Sample Illustration
          </button>
        </div>
      )}

      {/* ── Warnings banner (sample only) ── */}
      {hasResult && <WarningsBanner />}

      {/* ── Confidence threshold slider (sample only) ── */}
      {hasResult && <ConfidenceSlider />}

      {/* ── Main workspace ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

        {/* Left: image viewer */}
        <div className="lg:col-span-8 xl:col-span-9">
          <ImageViewer
            overlayTitle={hasResult ? 'Boulder Detection Layer' : 'Uploaded Image Viewer'}
            extraToolbarActions={
              hasResult ? (
                <span className="text-xs font-mono text-cyan-400">
                  Filter: ≥ {(confidenceThreshold * 100).toFixed(0)}%
                </span>
              ) : (
                <span className="text-xs font-mono text-amber-400">Raw Ingest Mode</span>
              )
            }
          >
            {hasResult && (
              <>
                {/* Heatmap layer (shared with Hazard Map page via context) */}
                <HazardGridOverlay />

                {/* Detection boxes + labels (controlled by Layers panel) */}
                <DetectionOverlay
                  onSelectDetection={(det) => setSelectedDetection(det)}
                  showBoxes={showBoulderBoxes}
                  showLabels={showConfidenceLabels}
                />
              </>
            )}
          </ImageViewer>

          {/* "No detections above this confidence" – only shown for sample when all filtered out */}
          {allFilteredOut && (
            <div className="mt-3 px-4 py-3 rounded-xl bg-slate-900/80 border border-slate-700 text-slate-400 text-xs flex items-center gap-2">
              <svg className="w-4 h-4 text-slate-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              No detections above this confidence.
            </div>
          )}
        </div>

        {/* Right column: Layers panel + boulder inspector + tips */}
        <div className="lg:col-span-4 xl:col-span-3 space-y-4">

          {/* Layers panel (sample only) */}
          {hasResult && <LayersPanel />}

          {/* Boulder Inspector card */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-semibold text-white text-sm flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-cyan-400" />
                Boulder Telemetry
              </h3>
              {selectedDetection && (
                <button
                  onClick={() => setSelectedDetection(null)}
                  className="text-xs text-slate-400 hover:text-white"
                >
                  Clear
                </button>
              )}
            </div>

            {hasResult ? (
              selectedDetection ? (
                <div className="space-y-3.5 text-xs">
                  <div className="p-3 rounded-xl bg-slate-950 border border-cyan-500/40 flex items-center justify-between">
                    <div>
                      <span className="text-[11px] text-slate-400 block">Boulder ID</span>
                      <span className="font-mono font-bold text-white text-base">#{selectedDetection.id}</span>
                    </div>
                    <div className="text-right">
                      <span className="text-[11px] text-slate-400 block">Confidence</span>
                      <span className="font-mono font-bold text-cyan-400 text-base">
                        {(selectedDetection.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>

                  {/* Diameter */}
                  <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between">
                    <span className="text-slate-400">Diameter:</span>
                    {selectedDetection.diameterM !== null && selectedDetection.diameterM !== undefined ? (
                      <span className="font-mono font-bold text-slate-200">{selectedDetection.diameterM} m</span>
                    ) : (
                      <span className="font-mono italic text-amber-400">Unavailable</span>
                    )}
                  </div>

                  {/* Shadow Length */}
                  <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between">
                    <span className="text-slate-400">Shadow Length:</span>
                    {selectedDetection.shadowLengthM !== null && selectedDetection.shadowLengthM !== undefined ? (
                      <span className="font-mono font-bold text-slate-200">{selectedDetection.shadowLengthM} m</span>
                    ) : (
                      <span className="font-mono italic text-amber-400">Unavailable</span>
                    )}
                  </div>

                  {/* Height & Uncertainty */}
                  <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between">
                    <span className="text-slate-400">Height:</span>
                    {selectedDetection.heightM !== null && selectedDetection.heightM !== undefined ? (
                      <span className="font-mono font-bold text-slate-200">
                        {selectedDetection.heightM} m
                        {selectedDetection.heightUncertaintyM !== null && selectedDetection.heightUncertaintyM !== undefined && (
                          <span className="text-slate-400 font-normal text-[11px] ml-1">
                            (±{selectedDetection.heightUncertaintyM} m)
                          </span>
                        )}
                      </span>
                    ) : (
                      <span className="font-mono italic text-amber-400">Unavailable</span>
                    )}
                  </div>

                  {/* Height Method */}
                  <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between">
                    <span className="text-slate-400">Height Method:</span>
                    {selectedDetection.heightMethod ? (
                      <span className="font-mono text-cyan-300">{selectedDetection.heightMethod}</span>
                    ) : (
                      <span className="font-mono italic text-amber-400">Unavailable</span>
                    )}
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1">
                    <span className="text-slate-400 block text-[11px]">Bounding Box [x1, y1, x2, y2]:</span>
                    <div className="font-mono text-[11px] text-cyan-300 bg-slate-900 p-2 rounded border border-slate-800">
                      [{selectedDetection.bbox.join(', ')}]
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <div className="p-2 rounded bg-slate-950/60 border border-slate-800">
                      <span className="text-slate-400 block">Box Width:</span>
                      <span className="font-mono text-slate-200">
                        {selectedDetection.bbox[2] - selectedDetection.bbox[0]} px
                      </span>
                    </div>
                    <div className="p-2 rounded bg-slate-950/60 border border-slate-800">
                      <span className="text-slate-400 block">Box Height:</span>
                      <span className="font-mono text-slate-200">
                        {selectedDetection.bbox[3] - selectedDetection.bbox[1]} px
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="py-8 text-center text-slate-400 text-xs space-y-2">
                  <div className="w-10 h-10 rounded-full bg-slate-800/80 mx-auto flex items-center justify-center text-slate-500">
                    <svg className="w-5 h-5 text-cyan-400/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                    </svg>
                  </div>
                  <p className="font-medium text-slate-300">No Boulder Selected</p>
                  <p className="text-[11px] text-slate-400 max-w-[200px] mx-auto">
                    Click on any boulder bounding box in the viewer to inspect its coordinates and dimensions.
                  </p>
                </div>
              )
            ) : (
              <div className="py-8 text-center text-slate-400 text-xs space-y-2.5">
                <div className="w-10 h-10 rounded-full bg-amber-500/10 border border-amber-500/30 mx-auto flex items-center justify-center text-amber-400">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <p className="font-medium text-slate-200">No Detection Data</p>
                <p className="text-[11px] text-amber-300/90 max-w-[200px] mx-auto leading-relaxed">
                  {loading ? 'Working…' : apiError ? `Not processed: ${apiError}` : 'Not processed yet. Run the analysis on the Upload page.'}
                </p>
              </div>
            )}
          </div>

          {/* Tips card */}
          <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80 text-xs text-slate-400 space-y-1.5">
            <span className="font-semibold text-slate-300 block">Registration Telemetry:</span>
            <p className="text-[11px] leading-relaxed">
              SVG overlay coordinates are synchronized to the {imageMeta.width}×{imageMeta.height} base raster.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
