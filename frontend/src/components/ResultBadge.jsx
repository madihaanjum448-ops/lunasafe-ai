import React from 'react';
import { useMission } from '../context/useMission';

/**
 * Shows whether the data on screen is demo data (is_mock: true) or a real AI result (is_mock: false).
 */
export default function ResultBadge({ className = '' }) {
  const { hasResult, isMock, loading, resultLabel } = useMission();

  let text = 'No analysis yet';
  let tone = 'bg-slate-700/40 text-slate-300 border-slate-600';
  if (loading) {
    text = 'Working…';
    tone = 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';
  } else if (resultLabel) {
    text = `${resultLabel} (is_mock: ${isMock ? 'true' : 'false'})`;
    tone = isMock
      ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
      : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
  } else if (hasResult && isMock) {
    text = 'Demo data (is_mock: true)';
    tone = 'bg-amber-500/20 text-amber-300 border-amber-500/40';
  } else if (hasResult) {
    text = 'Real AI result (is_mock: false)';
    tone = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
  }

  return (
    <span
      className={`text-[10px] uppercase font-semibold tracking-wider px-1.5 py-0.5 rounded border ${tone} ${className}`}
    >
      {text}
    </span>
  );
}
