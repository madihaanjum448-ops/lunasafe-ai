import React, { useState } from 'react';
import { useMission } from '../context/useMission';

export default function HazardGridOverlay() {
  const { hazardCells, imageMeta, selectedCell, setSelectedCell, showHeatmap } = useMission();
  const [hoveredCell, setHoveredCell] = useState(null);

  if (!showHeatmap || !hazardCells || hazardCells.length === 0) {
    return null;
  }

  // Derive grid dimensions dynamically from cell data (defaults to 8x8)
  const maxRow = hazardCells.reduce((max, c) => Math.max(max, c.row), 0);
  const maxCol = hazardCells.reduce((max, c) => Math.max(max, c.col), 0);
  const gridRows = maxRow + 1 || 8;
  const gridCols = maxCol + 1 || 8;

  // Each cell width = imageWidth / gridCols and height = imageHeight / gridRows
  const cellWidth = imageMeta.width / gridCols;
  const cellHeight = imageMeta.height / gridRows;

  // Scale factor proportional to image size so text and borders remain legible
  const scale = Math.max(0.25, Math.min(imageMeta.width, imageMeta.height) / 4096);
  const fontSize = Math.max(10, Math.round(18 * scale));
  const badgeHeight = Math.max(18, Math.round(34 * scale));
  const coordWidth = Math.max(70, Math.round(195 * scale));
  const scoreWidth = Math.max(55, Math.round(135 * scale));
  const pad = Math.round(12 * scale);

  // Visual styling for each landing safety classification
  const getCellStyles = (cellClass, isSelected, isHovered) => {
    const baseStroke = (isSelected ? 7 : isHovered ? 4.5 : 2) * scale;
    switch (cellClass) {
      case 'safe':
        return {
          fill: isSelected ? 'rgba(34, 197, 94, 0.55)' : isHovered ? 'rgba(34, 197, 94, 0.45)' : 'rgba(34, 197, 94, 0.32)',
          stroke: isSelected ? '#ffffff' : isHovered ? '#86efac' : '#22c55e',
          strokeWidth: Math.max(1.5, baseStroke),
          textFill: '#dcfce7',
        };
      case 'caution':
        return {
          fill: isSelected ? 'rgba(234, 179, 8, 0.60)' : isHovered ? 'rgba(234, 179, 8, 0.48)' : 'rgba(234, 179, 8, 0.35)',
          stroke: isSelected ? '#ffffff' : isHovered ? '#fef08a' : '#eab308',
          strokeWidth: Math.max(1.5, baseStroke),
          textFill: '#fef9c3',
        };
      case 'unsafe':
      default:
        return {
          fill: isSelected ? 'rgba(239, 68, 68, 0.65)' : isHovered ? 'rgba(239, 68, 68, 0.52)' : 'rgba(239, 68, 68, 0.38)',
          stroke: isSelected ? '#ffffff' : isHovered ? '#fca5a5' : '#ef4444',
          strokeWidth: Math.max(1.5, baseStroke),
          textFill: '#fee2e2',
        };
    }
  };

  return (
    <g className="hazard-cells-layer">
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
            {/* Cell Rectangle covering exact cell bounds */}
            <rect
              x={x}
              y={y}
              width={cellWidth}
              height={cellHeight}
              fill={styles.fill}
              stroke={styles.stroke}
              strokeWidth={styles.strokeWidth}
              rx={Math.max(2, 6 * scale)}
            />

            {/* Top-Left Grid Coordinates Badge */}
            <g transform={`translate(${x + pad}, ${y + pad + badgeHeight})`}>
              <rect
                x="0"
                y={-badgeHeight}
                width={coordWidth}
                height={badgeHeight}
                rx={Math.max(2, 4 * scale)}
                fill="#020617"
                fillOpacity="0.88"
                stroke={styles.stroke}
                strokeWidth={Math.max(1, 1.5 * scale)}
              />
              <text
                x={8 * scale}
                y={-badgeHeight * 0.3}
                fill="#f8fafc"
                fontSize={fontSize}
                fontWeight="700"
                fontFamily="ui-monospace, monospace"
              >
                R{cell.row}:C{cell.col} • {(cell.class || '').toUpperCase()}
              </text>
            </g>

            {/* Bottom-Right Hazard Score Badge */}
            <g transform={`translate(${x + cellWidth - scoreWidth - pad}, ${y + cellHeight - pad})`}>
              <rect
                x="0"
                y={-badgeHeight}
                width={scoreWidth}
                height={badgeHeight}
                rx={Math.max(2, 4 * scale)}
                fill="#020617"
                fillOpacity="0.88"
                stroke={styles.stroke}
                strokeWidth={Math.max(1, 1.5 * scale)}
              />
              <text
                x={8 * scale}
                y={-badgeHeight * 0.3}
                fill={styles.textFill}
                fontSize={fontSize}
                fontWeight="bold"
                fontFamily="ui-monospace, monospace"
              >
                Score: {cell.score !== null && cell.score !== undefined ? cell.score.toFixed(2) : 'N/A'}
              </text>
            </g>

            {/* Selected Cell Reticle Marker */}
            {isSelected && (
              <g>
                <circle
                  cx={x + cellWidth / 2}
                  cy={y + cellHeight / 2}
                  r={Math.max(12, 32 * scale)}
                  fill="none"
                  stroke="#ffffff"
                  strokeWidth={Math.max(2, 4 * scale)}
                />
                <circle
                  cx={x + cellWidth / 2}
                  cy={y + cellHeight / 2}
                  r={Math.max(4, 10 * scale)}
                  fill="#ffffff"
                />
                <line
                  x1={x + cellWidth / 2 - 45 * scale}
                  y1={y + cellHeight / 2}
                  x2={x + cellWidth / 2 + 45 * scale}
                  y2={y + cellHeight / 2}
                  stroke="#ffffff"
                  strokeWidth={Math.max(1.5, 3 * scale)}
                />
                <line
                  x1={x + cellWidth / 2}
                  y1={y + cellHeight / 2 - 45 * scale}
                  x2={x + cellWidth / 2}
                  y2={y + cellHeight / 2 + 45 * scale}
                  stroke="#ffffff"
                  strokeWidth={Math.max(1.5, 3 * scale)}
                />
              </g>
            )}
          </g>
        );
      })}
    </g>
  );
}
