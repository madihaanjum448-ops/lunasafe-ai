import React from 'react';
import { useMission } from '../context/useMission';
import { PROVENANCE_LABELS } from '../constants/schema';

/**
 * Shows the result provenance using exactly one of the four approved labels:
 * "Offline demo", "External detections", "Model inference", "Validated site".
 */
export default function ResultBadge({ className = '' }) {
  const { hasResult, isMock, loading, resultLabel } = useMission();

  let text = 'No analysis yet';
  let tone = 'bg-slate-700/40 text-slate-300 border-slate-600';
  let tooltip = 'No analysis yet';

  if (loading) {
    text = 'Working…';
    tone = 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';
    tooltip = 'Working…';
  } else if (hasResult) {
    text = resultLabel || PROVENANCE_LABELS.OFFLINE_DEMO;
    tooltip = `${text} (is_mock: ${isMock ? 'true' : 'false'})`;
    tone = isMock
      ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
      : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
  }

  return (
    <span
      title={tooltip}
      className={`text-[10px] uppercase font-semibold tracking-wider px-1.5 py-0.5 rounded border whitespace-nowrap ${tone} ${className}`}
    >
      {text}
    </span>
  );
}
