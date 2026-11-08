import React, { useState } from 'react';
import { useMission } from '../context/useMission';
import { confidenceBand, BAND_STYLES } from '../constants/detections';

/**
 * SVG overlay that draws confidence-coloured bounding boxes (and optional
 * confidence labels) for every visible detection.
 *
 * Props
 * -----
 * onSelectDetection  callback(detection)   – called when user clicks a box
 * showBoxes          boolean               – render bounding rectangles
 * showLabels         boolean               – render confidence badge text
 *
 * Both flags default to true so the overlay is fully visible when used
 * without explicit props (e.g. from the HazardMapPage overlay).
 */
export default function DetectionOverlay({
  onSelectDetection,
  showBoxes  = true,
  showLabels = true,
}) {
  const { detections, confidenceThreshold, imageMeta } = useMission();
  const [hoveredId, setHoveredId]   = useState(null);
  const [selectedId, setSelectedId] = useState(null);

  if (!detections || detections.length === 0) return null;

  // Apply confidence threshold filter
  const visibleDetections = detections.filter(
    (item) => item.confidence >= confidenceThreshold
  );

  if (visibleDetections.length === 0) return null;

  const handleClick = (e, detection) => {
    e.stopPropagation();
    setSelectedId(detection.id);
    if (onSelectDetection) onSelectDetection(detection);
  };

  // Scale geometry proportional to image size so boxes stay legible at any resolution
  const scale       = Math.max(0.25, Math.min(imageMeta.width, imageMeta.height) / 4096);
  const fontSize    = Math.max(10,  Math.round(20 * scale));
  const badgeHeight = Math.max(18,  Math.round(32 * scale));
  const cornerLen   = Math.max(4,   Math.round(12 * scale));

  return (
    <g className="boulder-detections-layer">
      <defs>
        <filter id="det-glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation={Math.max(2, 6 * scale)} result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      {visibleDetections.map((d) => {
        const [x1, y1, x2, y2] = d.bbox;
        const w          = Math.max(4, x2 - x1);
        const h          = Math.max(4, y2 - y1);
        const isHovered  = hoveredId  === d.id;
        const isSelected = selectedId === d.id;

        // Pick colour tokens from the confidence band
        const band    = confidenceBand(d.confidence);
        const palette = BAND_STYLES[band];

        const fill = isSelected
          ? palette.fillSelected
          : isHovered
            ? palette.fillHovered
            : palette.fill;
        const stroke = isSelected
          ? palette.strokeSelected
          : isHovered
            ? palette.strokeHovered
            : palette.stroke;
        const strokeWidth = Math.max(1.5,
          (isSelected ? 6 : isHovered ? 4.5 : 3) * scale
        );
        const rx      = Math.max(2, 4 * scale);
        const glowRef = isSelected || isHovered ? 'url(#det-glow)' : undefined;

        // Label content and dimensions
        const confPct  = `${(d.confidence * 100).toFixed(0)}%`;
        const sizeText = d.size_m !== null ? `${d.size_m}m` : null;
        const labelTxt = sizeText ? `${confPct} • ${sizeText}` : confPct;
        const badgeW   = Math.max(35, Math.round((labelTxt.length * 13 + 22) * scale));

        // Position label above box, or below if box is near the top
        const labelOff = Math.round(8 * scale);
        const labelY   = y1 > badgeHeight + labelOff
          ? y1 - labelOff
          : y2 + badgeHeight + labelOff;

        return (
          <g
            key={d.id}
            className="cursor-pointer transition-all duration-150"
            onMouseEnter={() => setHoveredId(d.id)}
            onMouseLeave={() => setHoveredId(null)}
            onClick={(e) => handleClick(e, d)}
          >
            {/* Invisible hit-area extends 10 px beyond every edge */}
            <rect
              x={x1 - 10 * scale}
              y={y1 - 10 * scale}
              width={w + 20 * scale}
              height={h + 20 * scale}
              fill="transparent"
            />

            {/* ── Bounding Box ── */}
            {showBoxes && (
              <>
                <rect
                  x={x1} y={y1} width={w} height={h}
                  fill={fill}
                  stroke={stroke}
                  strokeWidth={strokeWidth}
                  rx={rx}
                  filter={glowRef}
                />

                {/* Corner crosshairs (4 corners × 2 lines each) */}
                {[
                  [x1, y1,  1,  0], [x1, y1,  0,  1],
                  [x2, y1, -1,  0], [x2, y1,  0,  1],
                  [x1, y2,  1,  0], [x1, y2,  0, -1],
                  [x2, y2, -1,  0], [x2, y2,  0, -1],
                ].map(([cx, cy, dx, dy], i) => (
                  <line
                    key={i}
                    x1={cx}  y1={cy}
                    x2={cx + dx * cornerLen}
                    y2={cy + dy * cornerLen}
                    stroke={stroke}
                    strokeWidth={strokeWidth}
                  />
                ))}
              </>
            )}

            {/* ── Confidence / size label badge ── */}
            {showLabels && (
              <g transform={`translate(${x1}, ${labelY})`}>
                <rect
                  x="0" y={-badgeHeight}
                  width={badgeW} height={badgeHeight}
                  rx={Math.max(2, 4 * scale)}
                  fill="#020617" fillOpacity="0.9"
                  stroke={isSelected ? stroke : palette.stroke}
                  strokeWidth={Math.max(1, 1.8 * scale)}
                />
                <text
                  x={8 * scale} y={-badgeHeight * 0.3}
                  fill={palette.textFill}
                  fontSize={fontSize}
                  fontWeight="700"
                  fontFamily="ui-monospace, monospace"
                  letterSpacing="0.5"
                >
                  {labelTxt}
                </text>
              </g>
            )}
          </g>
        );
      })}
    </g>
  );
}
