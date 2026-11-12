import React, { useState } from 'react';
import { useTransformContext, useTransformEffect } from 'react-zoom-pan-pinch';
import { useMission } from '../context/useMission';
import { getLabelColorConfig, HAZARD_LABELS } from '../constants/schema';

/**
 * Renders the 8×8 Hazard Partition Grid SVG overlay.
 * Each cell is coloured directly by its label:
 * - "Safe candidate" -> Green
 * - "Caution" -> Yellow
 * - "Unsafe candidate" -> Red
 * - "Not assessed" -> Grey with dashed outline
 * Shows probability percentage inside cell when zoomed in enough to read it.
 */
export default function HazardGridOverlay() {
  const { hazardCells, imageMeta, selectedCell, setSelectedCell, showHeatmap } = useMission();
  const [hoveredCell, setHoveredCell] = useState(null);

  const transformContext = useTransformContext();
  const [zoomScale, setZoomScale] = useState(() => transformContext?.instance?.state?.scale ?? 1);

  useTransformEffect(({ state }) => {
    if (state?.scale) {
      setZoomScale(state.scale);
    }
  });

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
  const coordWidth = Math.max(80, Math.round(230 * scale));
  const probWidth = Math.max(48, Math.round(110 * scale));
  const pad = Math.round(12 * scale);

  // Check if cell is rendered large enough on screen for text to be legible
  const cellScreenPixels = zoomScale * cellWidth;
  const canReadText = cellScreenPixels >= 70;

  return (
    <g className="hazard-cells-layer">
      {hazardCells.map((cell) => {
        const x = cell.col * cellWidth;
        const y = cell.row * cellHeight;

        const isSelected = selectedCell && selectedCell.row === cell.row && selectedCell.col === cell.col;
        const isHovered = hoveredCell && hoveredCell.row === cell.row && hoveredCell.col === cell.col;

        const config = getLabelColorConfig(cell.label);
        const baseStroke = (isSelected ? 7 : isHovered ? 4.5 : 2) * scale;
        const fill = isSelected ? config.fillSelected : isHovered ? config.fillHovered : config.fill;
        const stroke = isSelected ? config.strokeSelected : isHovered ? config.strokeHovered : config.stroke;
        const strokeWidth = Math.max(1.5, baseStroke);
        const strokeDasharray = config.strokeDasharray;

        // Show probability & coordinate text if zoomed in enough or if user is interacting with this cell
        const showCellText = canReadText || isHovered || isSelected;

        const isNotAssessed = cell.label === HAZARD_LABELS.NOT_ASSESSED || cell.probability === null;

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
              fill={fill}
              stroke={stroke}
              strokeWidth={strokeWidth}
              strokeDasharray={strokeDasharray}
              rx={Math.max(2, 6 * scale)}
            />

            {/* Top-Left Grid Coordinates & Label Badge */}
            {showCellText && (
              <g transform={`translate(${x + pad}, ${y + pad + badgeHeight})`}>
                <rect
                  x="0"
                  y={-badgeHeight}
                  width={coordWidth}
                  height={badgeHeight}
                  rx={Math.max(2, 4 * scale)}
                  fill="#020617"
                  fillOpacity="0.88"
                  stroke={stroke}
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
                  R{cell.row}:C{cell.col} • {(cell.label || '').toUpperCase()}
                </text>
              </g>
            )}

            {/* Bottom-Right Hazard Probability Percentage Badge */}
            {showCellText && (
              <g transform={`translate(${x + cellWidth - probWidth - pad}, ${y + cellHeight - pad})`}>
                <rect
                  x="0"
                  y={-badgeHeight}
                  width={probWidth}
                  height={badgeHeight}
                  rx={Math.max(2, 4 * scale)}
                  fill="#020617"
                  fillOpacity="0.88"
                  stroke={stroke}
                  strokeWidth={Math.max(1, 1.5 * scale)}
                />
                <text
                  x={8 * scale}
                  y={-badgeHeight * 0.3}
                  fill={config.textFill}
                  fontSize={fontSize}
                  fontWeight="bold"
                  fontFamily="ui-monospace, monospace"
                >
                  {!isNotAssessed ? `${(cell.probability * 100).toFixed(0)}%` : 'N/A'}
                </text>
              </g>
            )}

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
