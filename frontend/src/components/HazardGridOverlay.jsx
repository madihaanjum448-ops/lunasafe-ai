import React, { useState } from 'react';
import { useMission } from '../context/useMission';

export default function HazardGridOverlay() {
  const { hazardCells, imageMeta, selectedCell, setSelectedCell, showHeatmap } = useMission();
  const [hoveredCell, setHoveredCell] = useState(null);

  if (!showHeatmap) {
    return null;
  }

  const gridCols = 8;
  const gridRows = 8;
  const cellWidth = imageMeta.width / gridCols;
  const cellHeight = imageMeta.height / gridRows;

  // Visual styling for each landing safety classification
  const getCellStyles = (cellClass, isSelected, isHovered) => {
    switch (cellClass) {
      case 'safe':
        return {
          fill: isSelected ? 'rgba(34, 197, 94, 0.55)' : isHovered ? 'rgba(34, 197, 94, 0.45)' : 'rgba(34, 197, 94, 0.32)',
          stroke: isSelected ? '#ffffff' : isHovered ? '#86efac' : '#22c55e',
          strokeWidth: isSelected ? 8 : isHovered ? 5 : 2.5,
          textFill: '#dcfce7',
          badgeBg: '#14532d',
        };
      case 'caution':
        return {
          fill: isSelected ? 'rgba(234, 179, 8, 0.60)' : isHovered ? 'rgba(234, 179, 8, 0.48)' : 'rgba(234, 179, 8, 0.35)',
          stroke: isSelected ? '#ffffff' : isHovered ? '#fef08a' : '#eab308',
          strokeWidth: isSelected ? 8 : isHovered ? 5 : 2.5,
          textFill: '#fef9c3',
          badgeBg: '#713f12',
        };
      case 'unsafe':
      default:
        return {
          fill: isSelected ? 'rgba(239, 68, 68, 0.65)' : isHovered ? 'rgba(239, 68, 68, 0.52)' : 'rgba(239, 68, 68, 0.38)',
          stroke: isSelected ? '#ffffff' : isHovered ? '#fca5a5' : '#ef4444',
          strokeWidth: isSelected ? 8 : isHovered ? 5 : 2.5,
          textFill: '#fee2e2',
          badgeBg: '#7f1d1d',
        };
    }
  };

  return (
    <g className="hazard-cells-layer">
      {/* 8x8 Grid Cells */}
      {hazardCells.map((cell) => {
        const x = cell.col * cellWidth;
        const y = cell.row * cellHeight;

        const isSelected = selectedCell && selectedCell.row === cell.row && selectedCell.col === cell.col;
        const isHovered = hoveredCell && hoveredCell.row === cell.row && hoveredCell.col === cell.col;
        const styles = getCellStyles(cell.class, isSelected, isHovered);

        return (
          <g
            key={`cell_${cell.row}_${cell.col}`}
            className="cursor-pointer transition-all duration-150"
            onClick={(e) => {
              e.stopPropagation();
              setSelectedCell(cell);
            }}
            onMouseEnter={() => setHoveredCell(cell)}
            onMouseLeave={() => setHoveredCell(null)}
          >
            {/* Cell Rectangle */}
            <rect
              x={x}
              y={y}
              width={cellWidth}
              height={cellHeight}
              fill={styles.fill}
              stroke={styles.stroke}
              strokeWidth={styles.strokeWidth}
              rx={6}
            />

            {/* Grid Coordinates & Hazard Score Overlay */}
            <g transform={`translate(${x + 20}, ${y + 40})`}>
              {/* Background badge for readability */}
              <rect
                x="-8"
                y="-26"
                width="190"
                height="34"
                rx="6"
                fill="#020617"
                fillOpacity="0.85"
                stroke={styles.stroke}
                strokeWidth="1.5"
              />
              <text
                x="6"
                y="-4"
                fill="#f8fafc"
                fontSize="18"
                fontWeight="700"
                fontFamily="ui-monospace, monospace"
              >
                R{cell.row}:C{cell.col} • {(cell.class || '').toUpperCase()}
              </text>
            </g>

            {/* Cell Hazard Score badge on bottom right */}
            <g transform={`translate(${x + cellWidth - 140}, ${y + cellHeight - 20})`}>
              <rect
                x="-10"
                y="-26"
                width="135"
                height="32"
                rx="6"
                fill="#020617"
                fillOpacity="0.85"
                stroke={styles.stroke}
                strokeWidth="1.5"
              />
              <text
                x="4"
                y="-4"
                fill={styles.textFill}
                fontSize="18"
                fontWeight="bold"
                fontFamily="ui-monospace, monospace"
              >
                Score: {cell.score !== null && cell.score !== undefined ? cell.score.toFixed(2) : 'N/A'}
              </text>
            </g>

            {/* Selected Cell Marker Animation Effect */}
            {isSelected && (
              <g>
                <circle cx={x + cellWidth / 2} cy={y + cellHeight / 2} r="30" fill="none" stroke="#ffffff" strokeWidth="4" />
                <circle cx={x + cellWidth / 2} cy={y + cellHeight / 2} r="10" fill="#ffffff" />
                <line x1={x + cellWidth / 2 - 45} y1={y + cellHeight / 2} x2={x + cellWidth / 2 + 45} y2={y + cellHeight / 2} stroke="#ffffff" strokeWidth="3" />
                <line x1={x + cellWidth / 2} y1={y + cellHeight / 2 - 45} x2={x + cellWidth / 2} y2={y + cellHeight / 2 + 45} stroke="#ffffff" strokeWidth="3" />
              </g>
            )}
          </g>
        );
      })}
    </g>
  );
}
