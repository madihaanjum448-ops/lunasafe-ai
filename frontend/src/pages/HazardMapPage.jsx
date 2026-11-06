import React from 'react';
import ImageViewer from '../components/ImageViewer';
import HazardGridOverlay from '../components/HazardGridOverlay';
import DetectionOverlay from '../components/DetectionOverlay';
import HazardLegend from '../components/HazardLegend';
import RegionExplanationPanel from '../components/RegionExplanationPanel';
import WarningsBanner from '../components/WarningsBanner';
import { useMission } from '../context/useMission';

export default function HazardMapPage() {
  const { showHeatmap, showDetectionsInHazardMap, selectedCell } = useMission();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Page Header with PROMINENT "Mock data" Label */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase tracking-widest text-cyan-400 font-mono font-semibold">
              Landing Safety Analytics
            </span>
            {/* Visible Mock Data Label */}
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 font-mono font-bold tracking-wide">
              Mock Data
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Lunar Surface Hazard Map
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
            8×8 topological landing zone grid categorized into safe (green), caution (yellow), and unsafe (red).
            Click any cell to inspect hazard telemetry and site clearance explanations.
          </p>
        </div>

        {/* Prominent Header Badge: Mock Data Indicator */}
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
      </div>

      {/* Descent Warnings if present */}
      <WarningsBanner />

      {/* Legend & Layer Controls */}
      <HazardLegend />

      {/* Main Workspace: Pan-and-zoom hazard map & Region Explanation side panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Interactive Hazard Heatmap Canvas */}
        <div className="lg:col-span-7 xl:col-span-8">
          <ImageViewer
            overlayTitle="8×8 Safety Partition Heatmap"
            extraToolbarActions={
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
            }
          >
            {/* Heatmap 8x8 Grid SVG Layer */}
            <HazardGridOverlay />

            {/* Optional Boulder Detections Layer on top */}
            {showDetectionsInHazardMap && <DetectionOverlay />}
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
