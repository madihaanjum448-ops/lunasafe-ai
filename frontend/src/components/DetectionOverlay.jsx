import React, { useState } from 'react';
import { useMission } from '../context/useMission';

export default function DetectionOverlay({ onSelectDetection }) {
  const { detections, confidenceThreshold } = useMission();
  const [hoveredId, setHoveredId] = useState(null);
  const [selectedId, setSelectedId] = useState(null);

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

  return (
    <g className="boulder-detections-layer">
      {/* SVG Definitions for glow effects and filters */}
      <defs>
        <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="6" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>

      {visibleDetections.map((d) => {
        const [x1, y1, x2, y2] = d.bbox;
        const width = Math.max(12, x2 - x1);
        const height = Math.max(12, y2 - y1);
        const isHovered = hoveredId === d.id;
        const isSelected = selectedId === d.id;

        // Label positioning - placed above the box, or inside if near top boundary
        const labelY = y1 > 50 ? y1 - 10 : y2 + 35;
        const confPercent = `${(d.confidence * 100).toFixed(0)}%`;
        const sizeText = d.size_m !== null ? `${d.size_m}m` : null;
        const labelText = sizeText ? `${confPercent} • ${sizeText}` : confPercent;
        const badgeWidth = labelText.length * 15 + 24;

        return (
          <g
            key={d.id}
            className="cursor-pointer transition-all duration-150"
            onMouseEnter={() => setHoveredId(d.id)}
            onMouseLeave={() => setHoveredId(null)}
            onClick={(e) => handleClick(e, d)}
          >
            {/* Extended invisible touch/hover hit area */}
            <rect
              x={x1 - 15}
              y={y1 - 15}
              width={width + 30}
              height={height + 30}
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
              strokeWidth={isSelected ? 6 : isHovered ? 5 : 3.5}
              strokeDasharray={isSelected ? 'none' : 'none'}
              rx={4}
              filter={isSelected || isHovered ? 'url(#glow)' : undefined}
            />

            {/* Corner Crosshairs for tactical sci-fi look */}
            <line x1={x1} y1={y1} x2={x1 + 10} y2={y1} stroke="#38bdf8" strokeWidth={4} />
            <line x1={x1} y1={y1} x2={x1} y2={y1 + 10} stroke="#38bdf8" strokeWidth={4} />
            <line x1={x2} y1={y1} x2={x2 - 10} y2={y1} stroke="#38bdf8" strokeWidth={4} />
            <line x1={x2} y1={y1} x2={x2} y2={y1 + 10} stroke="#38bdf8" strokeWidth={4} />
            <line x1={x1} y1={y2} x2={x1 + 10} y2={y2} stroke="#38bdf8" strokeWidth={4} />
            <line x1={x1} y1={y2} x2={x1} y2={y2 - 10} stroke="#38bdf8" strokeWidth={4} />
            <line x1={x2} y1={y2} x2={x2 - 10} y2={y2} stroke="#38bdf8" strokeWidth={4} />
            <line x1={x2} y1={y2} x2={x2} y2={y2 - 10} stroke="#38bdf8" strokeWidth={4} />

            {/* Confidence Label Badge */}
            <g transform={`translate(${x1}, ${labelY})`}>
              <rect
                x="0"
                y="-30"
                width={badgeWidth}
                height="32"
                rx="6"
                fill="#020617"
                fillOpacity="0.88"
                stroke={isSelected ? '#38bdf8' : '#0891b2'}
                strokeWidth={2}
              />
              <text
                x="12"
                y="-9"
                fill={isSelected ? '#ffffff' : '#38bdf8'}
                fontSize="20"
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
