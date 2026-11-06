import React, { useState } from 'react';
import ImageViewer from '../components/ImageViewer';
import DetectionOverlay from '../components/DetectionOverlay';
import ConfidenceSlider from '../components/ConfidenceSlider';
import WarningsBanner from '../components/WarningsBanner';
import { useMission } from '../context/useMission';

export default function DetectionsPage() {
  const { detections, confidenceThreshold, imageMeta, loadSampleData } = useMission();
  const [selectedDetection, setSelectedDetection] = useState(null);

  const visibleDetections = detections.filter(
    (d) => d.confidence >= confidenceThreshold
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs uppercase tracking-widest text-cyan-400 font-mono font-semibold">
              Obstacle Detection Module
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-mono">
              {imageMeta.isSample ? 'Mock Data' : 'User Upload'}
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            High-Resolution Boulder Detections
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl">
            {imageMeta.isSample
              ? 'Pan and zoom across the landing site. Each detected surface hazard is framed with an aligned SVG bounding box and confidence rating.'
              : 'Pan and zoom across your uploaded lunar image.'}
          </p>
        </div>

        {/* Quick summary badges (shown on sample illustration) */}
        {imageMeta.isSample && (
          <div className="flex items-center gap-2 self-start md:self-auto">
            <div className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs flex items-center gap-2">
              <span className="text-slate-400">Total Catalog:</span>
              <span className="font-mono font-bold text-white">{detections.length}</span>
            </div>
            <div className="px-3 py-1.5 rounded-xl bg-cyan-950/60 border border-cyan-500/40 text-xs flex items-center gap-2 text-cyan-300">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
              <span className="font-mono font-bold">{visibleDetections.length} visible</span>
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
                Mock detections are hidden for user uploads.
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

      {/* Warnings Banner if present and on sample illustration */}
      {imageMeta.isSample && <WarningsBanner />}

      {/* Confidence Filter Slider Control (only on sample illustration) */}
      {imageMeta.isSample && <ConfidenceSlider />}

      {/* Main Workspace: Image Viewer & Detection Details Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Pan-and-zoom viewer stage */}
        <div className="lg:col-span-8 xl:col-span-9">
          <ImageViewer
            overlayTitle={imageMeta.isSample ? "Boulder Detection Layer" : "Uploaded Image Viewer"}
            extraToolbarActions={
              imageMeta.isSample ? (
                <span className="text-xs font-mono text-cyan-400">
                  Filter: ≥ {(confidenceThreshold * 100).toFixed(0)}%
                </span>
              ) : (
                <span className="text-xs font-mono text-amber-400">
                  Raw Ingest Mode
                </span>
              )
            }
          >
            {imageMeta.isSample && (
              <DetectionOverlay onSelectDetection={(det) => setSelectedDetection(det)} />
            )}
          </ImageViewer>
        </div>

        {/* Selected Boulder Inspector Card (Right Column) */}
        <div className="lg:col-span-4 xl:col-span-3 space-y-4">
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-semibold text-white text-sm flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
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

            {imageMeta.isSample ? (
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

                  {/* Estimated size */}
                  <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center justify-between">
                    <span className="text-slate-400">Estimated Size:</span>
                    {selectedDetection.size_m !== null ? (
                      <span className="font-mono font-bold text-slate-200">
                        {selectedDetection.size_m} meters
                      </span>
                    ) : (
                      <span className="font-mono italic text-amber-400">Unavailable</span>
                    )}
                  </div>

                  {/* Bounding box pixels */}
                  <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1.5">
                    <span className="text-slate-400 block">Bounding Box [x1, y1, x2, y2]:</span>
                    <div className="font-mono text-[11px] text-cyan-300 bg-slate-900 p-2 rounded border border-slate-800">
                      [{selectedDetection.bbox.join(', ')}]
                    </div>
                  </div>

                  {/* Calculated box dimensions */}
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
                  Not processed yet. The analysis backend is not connected.
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
