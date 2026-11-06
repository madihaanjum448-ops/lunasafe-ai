import React, { useState } from 'react';
import { useMission } from '../context/useMission';

export default function DetectionOverlay({ onSelectDetection }) {
  const { detections, confidenceThreshold, imageMeta } = useMission();
  const [hoveredId, setHoveredId] = useState(null);
  const [selectedId, setSelectedId] = useState(null);

  if (!detections || detections.length === 0) {
    return null;
  }

  // Filter detections based on threshold slider
  const visibleDetections = detections.filter(
    (item) => item.confidence >= confidenceThreshold
  );

  const handleClick = (e, detection) => {
    e.stopPropagation();
    setSelectedId(detection.id);
    if (onSelectDetection) {
      onSelectDetection(detection);
    }
  };

  // Scale factor proportional to image dimensions so boxes and labels remain readable
  const scale = Math.max(0.25, Math.min(imageMeta.width, imageMeta.height) / 4096);
  const fontSize = Math.max(10, Math.round(20 * scale));
  const badgeHeight = Math.max(18, Math.round(32 * scale));
  const cornerLength = Math.max(4, Math.round(12 * scale));

  return (
    <g className="boulder-detections-layer">
      <defs>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation={Math.max(2, 6 * scale)} result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      {visibleDetections.map((d) => {
        const [x1, y1, x2, y2] = d.bbox;
        const width = Math.max(4, x2 - x1);
        const height = Math.max(4, y2 - y1);
        const isHovered = hoveredId === d.id;
        const isSelected = selectedId === d.id;

        const confPercent = `${(d.confidence * 100).toFixed(0)}%`;
        const sizeText = d.size_m !== null ? `${d.size_m}m` : null;
        const labelText = sizeText ? `${confPercent} • ${sizeText}` : confPercent;
        const badgeWidth = Math.max(35, Math.round((labelText.length * 13 + 22) * scale));

        // Label positioning - placed above the box, or below if near top boundary
        const labelOffset = Math.round(8 * scale);
        const labelY = y1 > badgeHeight + labelOffset ? y1 - labelOffset : y2 + badgeHeight + labelOffset;
        const strokeWidth = Math.max(1.5, (isSelected ? 6 : isHovered ? 4.5 : 3) * scale);

        return (
          <g
            key={d.id}
            className="cursor-pointer transition-all duration-150"
            onMouseEnter={() => setHoveredId(d.id)}
            onMouseLeave={() => setHoveredId(null)}
            onClick={(e) => handleClick(e, d)}
          >
            {/* Extended touch/hover hit area */}
            <rect
              x={x1 - 10 * scale}
              y={y1 - 10 * scale}
              width={width + 20 * scale}
              height={height + 20 * scale}
              fill="transparent"
            />

            {/* Boulder Bounding Box */}
            <rect
              x={x1}
              y={y1}
              width={width}
              height={height}
              fill={isSelected ? 'rgba(56, 189, 248, 0.35)' : isHovered ? 'rgba(6, 182, 212, 0.25)' : 'rgba(6, 182, 212, 0.12)'}
              stroke={isSelected ? '#38bdf8' : isHovered ? '#67e8f9' : '#06b6d4'}
              strokeWidth={strokeWidth}
              rx={Math.max(2, 4 * scale)}
              filter={isSelected || isHovered ? 'url(#glow)' : undefined}
            />

            {/* Corner Crosshairs */}
            <line x1={x1} y1={y1} x2={x1 + cornerLength} y2={y1} stroke="#38bdf8" strokeWidth={strokeWidth} />
            <line x1={x1} y1={y1} x2={x1} y2={y1 + cornerLength} stroke="#38bdf8" strokeWidth={strokeWidth} />
            <line x1={x2} y1={y1} x2={x2 - cornerLength} y2={y1} stroke="#38bdf8" strokeWidth={strokeWidth} />
            <line x1={x2} y1={y1} x2={x2} y2={y1 + cornerLength} stroke="#38bdf8" strokeWidth={strokeWidth} />
            <line x1={x1} y1={y2} x2={x1 + cornerLength} y2={y2} stroke="#38bdf8" strokeWidth={strokeWidth} />
            <line x1={x1} y1={y2} x2={x1} y2={y2 - cornerLength} stroke="#38bdf8" strokeWidth={strokeWidth} />
            <line x1={x2} y1={y2} x2={x2 - cornerLength} y2={y2} stroke="#38bdf8" strokeWidth={strokeWidth} />
            <line x1={x2} y1={y2} x2={x2} y2={y2 - cornerLength} stroke="#38bdf8" strokeWidth={strokeWidth} />

            {/* Scaled Confidence Label Badge */}
            <g transform={`translate(${x1}, ${labelY})`}>
              <rect
                x="0"
                y={-badgeHeight}
                width={badgeWidth}
                height={badgeHeight}
                rx={Math.max(2, 4 * scale)}
                fill="#020617"
                fillOpacity="0.9"
                stroke={isSelected ? '#38bdf8' : '#0891b2'}
                strokeWidth={Math.max(1, 1.8 * scale)}
              />
              <text
                x={8 * scale}
                y={-badgeHeight * 0.3}
                fill={isSelected ? '#ffffff' : '#38bdf8'}
                fontSize={fontSize}
                fontWeight="700"
                fontFamily="ui-monospace, monospace"
                letterSpacing="0.5"
              >
                {labelText}
              </text>
            </g>
          </g>
        );
      })}
    </g>
  );
}
