import React from 'react';
import { useMission } from '../context/useMission';

export default function ConfidenceSlider() {
  const { confidenceThreshold, setConfidenceThreshold, detections } = useMission();

  const visibleCount = detections.filter((d) => d.confidence >= confidenceThreshold).length;
  const totalCount = detections.length;

  const presets = [
    { label: '0.40', value: 0.40 },
    { label: '0.60', value: 0.60 },
    { label: '0.75', value: 0.75 },
    { label: '0.90', value: 0.90 },
  ];

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 sm:p-5 backdrop-blur-sm shadow-lg">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400"></span>
            <label htmlFor="confidence-slider" className="text-sm font-semibold text-slate-100">
              Confidence Threshold Filter
            </label>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Hide boulder detections with detection confidence below this cutoff
          </p>
        </div>

        {/* Live Counter Badge */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <div className="px-3 py-1 rounded-lg bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 font-mono text-xs flex items-center gap-2">
            <span className="text-slate-400">Showing:</span>
            <span className="font-bold text-white text-sm">{visibleCount}</span>
            <span className="text-slate-500">/ {totalCount}</span>
          </div>

          <div className="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 font-mono text-xs text-slate-200">
            Cutoff: <span className="text-cyan-400 font-bold">{(confidenceThreshold * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>

      {/* Slider Bar */}
      <div className="space-y-2">
        <div className="relative flex items-center">
          <input
            id="confidence-slider"
            type="range"
            min="0.00"
            max="1.00"
            step="0.01"
            value={confidenceThreshold}
            onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
            className="w-full h-2.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/50"
          />
        </div>

        {/* Scale labels & Quick presets */}
        <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
          <span className="font-mono">0.0 (Show All)</span>

          <div className="flex items-center gap-1.5">
            <span className="text-[11px] text-slate-400 mr-1 hidden sm:inline">Presets:</span>
            {presets.map((preset) => (
              <button
                key={preset.value}
                onClick={() => setConfidenceThreshold(preset.value)}
                className={`px-2 py-0.5 text-[11px] font-mono rounded transition-colors ${
                  Math.abs(confidenceThreshold - preset.value) < 0.02
                    ? 'bg-cyan-500/30 text-cyan-300 border border-cyan-500/50'
                    : 'bg-slate-800/80 text-slate-400 hover:text-slate-200 hover:bg-slate-700'
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>

          <span className="font-mono">1.0 (Strict)</span>
        </div>
      </div>
    </div>
  );
}
