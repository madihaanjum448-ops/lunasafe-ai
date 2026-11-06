import React from 'react';
import ImageViewer from '../components/ImageViewer';
import HazardGridOverlay from '../components/HazardGridOverlay';
import DetectionOverlay from '../components/DetectionOverlay';
import HazardLegend from '../components/HazardLegend';
import RegionExplanationPanel from '../components/RegionExplanationPanel';
import WarningsBanner from '../components/WarningsBanner';
import { useMission } from '../context/useMission';

export default function HazardMapPage() {
  const { showHeatmap, showDetectionsInHazardMap, selectedCell, imageMeta, loadSampleData } = useMission();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase tracking-widest text-cyan-400 font-mono font-semibold">
              Landing Safety Analytics
            </span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 font-mono font-bold tracking-wide">
              {imageMeta.isSample ? 'Mock Data' : 'User Upload'}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Lunar Surface Hazard Map
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
            {imageMeta.isSample
              ? '8×8 topological landing zone grid categorized into safe (green), caution (yellow), and unsafe (red). Click any cell to inspect hazard telemetry and site clearance explanations.'
              : 'Pan and zoom across your uploaded lunar image.'}
          </p>
        </div>

        {/* Prominent Header Badge: Mock Data Indicator (shown on sample illustration) */}
        {imageMeta.isSample && (
          <div className="flex items-center gap-2 self-start md:self-auto">
            <div className="px-3.5 py-2 rounded-xl bg-slate-900 border border-amber-500/30 flex items-center gap-2.5 shadow-lg">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse"></span>
              <div>
                <span className="text-[10px] uppercase tracking-wider text-slate-400 block font-semibold">
                  Evaluation Mode
                </span>
                <span className="text-xs font-bold text-amber-300 font-mono">
                  Mock Data Stream
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Prominent Message when User Upload is Active */}
      {!imageMeta.isSample && (
        <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-500/50 text-amber-200 text-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-lg">
          <div className="flex items-center gap-3">
            <svg className="w-5 h-5 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <span className="font-semibold block sm:inline">
                Not processed yet. The analysis backend is not connected.
              </span>
              <span className="text-xs text-amber-300/80 sm:ml-2 block sm:inline">
                Hazard grid evaluation requires connection to the backend pipeline.
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

      {/* Descent Warnings if present on sample */}
      {imageMeta.isSample && <WarningsBanner />}

      {/* Legend & Layer Controls */}
      <HazardLegend />

      {/* Main Workspace: Pan-and-zoom hazard map & Region Explanation side panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Interactive Hazard Heatmap Canvas */}
        <div className="lg:col-span-7 xl:col-span-8">
          <ImageViewer
            overlayTitle={imageMeta.isSample ? "8×8 Safety Partition Heatmap" : "Uploaded Image Viewer"}
            extraToolbarActions={
              imageMeta.isSample ? (
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-slate-400">
                    Heatmap: {showHeatmap ? <span className="text-emerald-400">Active</span> : <span className="text-slate-500">Hidden</span>}
                  </span>
                  {selectedCell && (
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-500/30">
                      Selected: [R{selectedCell.row}, C{selectedCell.col}]
                    </span>
                  )}
                </div>
              ) : (
                <span className="text-xs font-mono text-amber-400">
                  Raw Ingest Mode
                </span>
              )
            }
          >
            {/* Heatmap 8x8 Grid SVG Layer (only rendered on sample data) */}
            {imageMeta.isSample && <HazardGridOverlay />}

            {/* Optional Boulder Detections Layer on top (only on sample data) */}
            {imageMeta.isSample && showDetectionsInHazardMap && <DetectionOverlay />}
          </ImageViewer>
        </div>

        {/* Region Explanation Side Panel */}
        <div className="lg:col-span-5 xl:col-span-4 sticky top-20">
          <RegionExplanationPanel />
        </div>
      </div>
    </div>
  );
}
