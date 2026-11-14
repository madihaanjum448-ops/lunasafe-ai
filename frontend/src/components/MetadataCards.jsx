import React from 'react';
import { METADATA_WARNINGS } from '../constants/metadata';

/**
 * Reusable amber "Unavailable" badge, used when a metadata value is null/undefined.
 */
function UnavailableBadge() {
  return (
    <span className="text-amber-400 italic">Unavailable</span>
  );
}

/**
 * Reusable "(Mock value)" label shown beside sample metadata values.
 */
function MockBadge() {
  return (
    <span className="ml-1.5 text-[10px] text-amber-400 font-sans font-medium">
      (Mock value)
    </span>
  );
}

/**
 * A single row in the metadata summary table.
 *
 * @param {Object} props
 * @param {string}  props.label       - Row label
 * @param {*}       props.value       - Raw value (null means unavailable)
 * @param {string}  [props.unit]      - Optional unit string appended after value
 * @param {boolean} props.isSample    - Whether the active image is the mock sample
 * @param {boolean} [props.last]      - Omits bottom border on the last row
 */
function MetaRow({ label, value, unit = '', isSample, last = false }) {
  const hasValue = value !== null && value !== undefined && value !== '';

  return (
    <div className={`flex items-center justify-between py-1.5${last ? '' : ' border-b border-slate-800/60'}`}>
      <span className="text-slate-400 text-xs">{label}</span>
      <span className="font-mono text-xs text-slate-200 text-right">
        {hasValue ? (
          <>
            {value}{unit && ` ${unit}`}
            {isSample && <MockBadge />}
          </>
        ) : (
          <UnavailableBadge />
        )}
      </span>
    </div>
  );
}

/**
 * MetadataSummaryCard
 *
 * Shows three metadata rows: Pixel Scale (m/px), Sun Elevation Angle (°),
 * and Map Projection. Sample data shows mock values with a "(Mock value)"
 * label; real user uploads always show "Unavailable" with a backend note.
 *
 * Values are read exclusively from imageMeta (populated from the mock JSON
 * or the upload handler). Field names live in constants/metadata.js.
 *
 * @param {Object}  props
 * @param {Object}  props.imageMeta - The active image metadata from MissionContext
 */
export function MetadataSummaryCard({ imageMeta, note }) {
  const displayNote = note !== undefined
    ? note
    : (!imageMeta.isSample ? METADATA_WARNINGS.BACKEND_NOTE : null);

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-lg space-y-1">
      {/* Card header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-violet-400" />
          Metadata Summary
        </h3>
        {displayNote && (
          <span className="text-[11px] text-slate-400 italic">
            {displayNote}
          </span>
        )}
      </div>

      {/* Three metadata rows */}
      <MetaRow
        label="Pixel Scale"
        value={imageMeta.pixelScaleM}
        unit="m/px"
        isSample={imageMeta.isSample}
      />
      <MetaRow
        label="Sun Elevation Angle"
        value={imageMeta.sunElevationDeg}
        unit="°"
        isSample={imageMeta.isSample}
      />
      <MetaRow
        label="Map Projection"
        value={imageMeta.projection}
        isSample={imageMeta.isSample}
        last
      />
    </div>
  );
}

/**
 * MetadataWarningsCard
 *
 * Derives which metadata values are missing from imageMeta and shows one
 * warning line per missing field. If nothing is missing, shows a green
 * "All required metadata found." confirmation.
 *
 * @param {Object}  props
 * @param {Object}  props.imageMeta - The active image metadata from MissionContext
 * @param {string[]} props.metaWarnings - Pre-computed array of warning strings
 */
export function MetadataWarningsCard({ metaWarnings }) {
  const allFound = metaWarnings.length === 0;

  return (
    <div className={`rounded-2xl p-4 shadow-lg border text-xs space-y-2 ${
      allFound
        ? 'bg-emerald-950/40 border-emerald-500/40'
        : 'bg-amber-950/30 border-amber-500/40'
    }`}>
      {/* Card header */}
      <div className="flex items-center gap-2 pb-1 border-b border-slate-800/40">
        {allFound ? (
          <svg className="w-4 h-4 text-emerald-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        ) : (
          <svg className="w-4 h-4 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        )}
        <h3 className={`font-semibold ${allFound ? 'text-emerald-300' : 'text-amber-300'}`}>
          Warnings
        </h3>
      </div>

      {allFound ? (
        <p className="text-emerald-200 leading-relaxed">
          {METADATA_WARNINGS.ALL_FOUND}
        </p>
      ) : (
        <ul className="space-y-1.5 text-amber-200/90 leading-relaxed">
          {metaWarnings.map((warning) => (
            <li key={warning} className="flex items-start gap-2">
              <span className="mt-0.5 w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
              <span>{warning}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
