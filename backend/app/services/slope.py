
"""
LunaSafe AI - DEM slope calculation.

Uses Horn's 3x3 finite-difference method.

SCOPE AND LIMITATIONS:
- Computes slope from a DEM array supplied to this module.
- Does NOT download LOLA elevation data.
- Does NOT perform geospatial alignment or resampling.
- Assumes DEM elevation values and cell size use metres.
- Assumes the DEM covers the same footprint as the image.
- Has not been validated against a published lunar slope product.

Slope is calculated in degrees.

Grid reduction:
- max: conservative statistic; steepest patch determines cell slope.
- mean: average valid slope across the cell.
- Cells containing no valid values return None.
"""

from typing import List, Optional

import math
import numpy as np


# ---------------------------------------------------------
# 1. Calculate slope using Horn's 3x3 method
# ---------------------------------------------------------

def compute_slope_deg(
    dem: np.ndarray,
    cell_size_m: float,
) -> np.ndarray:
    """
    Calculate slope in degrees using Horn's 3x3 method.

    Args:
        dem:
            Two-dimensional DEM elevation array in metres.

        cell_size_m:
            DEM cell size in metres.

    Returns:
        Two-dimensional NumPy array containing slope in degrees.

    Edge handling:
        Edges are padded by repeating their nearest values.
    """

    # Validate input array.
    if not isinstance(dem, np.ndarray):
        raise ValueError("DEM must be a NumPy array.")

    if dem.ndim != 2:
        raise ValueError("DEM must be a 2-D array.")

    if dem.size == 0:
        raise ValueError("DEM cannot be empty.")

    if dem.shape[0] < 2 or dem.shape[1] < 2:
        raise ValueError(
            "DEM must contain at least 2 rows and 2 columns."
        )

    # Validate cell size.
    try:
        cell_size_m = float(cell_size_m)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("DEM cell size must be a valid number.")

    if not math.isfinite(cell_size_m) or cell_size_m <= 0:
        raise ValueError(
            "DEM cell size must be positive and finite."
        )

    # Convert elevation values to float64.
    try:
        dem = dem.astype(np.float64, copy=False)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("DEM must contain numeric elevation values.")

    # Replace invalid elevation values with NaN.
    dem = np.where(np.isfinite(dem), dem, np.nan)

    if np.all(np.isnan(dem)):
        raise ValueError(
            "DEM contains no valid elevation values."
        )

    # Pad the array by repeating edge values.
    z = np.pad(
        dem,
        pad_width=1,
        mode="edge",
    )

    # -----------------------------------------------------
    # Horn's 1981 finite-difference method
    # -----------------------------------------------------

    # X-direction elevation gradient.
    dzdx = (
        (
            z[:-2, 2:]
            + 2.0 * z[1:-1, 2:]
            + z[2:, 2:]
        )
        -
        (
            z[:-2, :-2]
            + 2.0 * z[1:-1, :-2]
            + z[2:, :-2]
        )
    ) / (8.0 * cell_size_m)

    # Y-direction elevation gradient.
    dzdy = (
        (
            z[2:, :-2]
            + 2.0 * z[2:, 1:-1]
            + z[2:, 2:]
        )
        -
        (
            z[:-2, :-2]
            + 2.0 * z[:-2, 1:-1]
            + z[:-2, 2:]
        )
    ) / (8.0 * cell_size_m)

    # Calculate slope magnitude.
    gradient = np.hypot(dzdx, dzdy)

    # Convert gradient to slope angle in degrees.
    slope_deg = np.degrees(
        np.arctan(gradient)
    )

    # Keep invalid DEM regions invalid.
    slope_deg = np.where(
        np.isfinite(slope_deg),
        slope_deg,
        np.nan,
    )

    return slope_deg


# ---------------------------------------------------------
# 2. Reduce slope raster into the hazard grid
# ---------------------------------------------------------

def slope_by_grid_cell(
    slope_deg: np.ndarray,
    rows: int,
    cols: int,
    statistic: str = "max",
) -> List[List[Optional[float]]]:
    """
    Reduce a slope raster into a rows x cols grid.

    Args:
        slope_deg:
            Two-dimensional slope raster in degrees.

        rows:
            Number of output grid rows.

        cols:
            Number of output grid columns.

        statistic:
            "max"  -> maximum valid slope in each cell.
            "mean" -> mean valid slope in each cell.

    Returns:
        A nested list of slope values.

        A cell containing no valid values returns None.
    """

    # Validate slope raster.
    if not isinstance(slope_deg, np.ndarray):
        raise ValueError(
            "Slope raster must be a NumPy array."
        )

    if slope_deg.ndim != 2:
        raise ValueError(
            "Slope raster must be two-dimensional."
        )

    if slope_deg.size == 0:
        raise ValueError(
            "Slope raster cannot be empty."
        )

    height, width = slope_deg.shape

    if height <= 0 or width <= 0:
        raise ValueError(
            "Slope raster dimensions must be positive."
        )

    # Validate grid dimensions.
    if (
        not isinstance(rows, int)
        or not isinstance(cols, int)
        or isinstance(rows, bool)
        or isinstance(cols, bool)
        or rows <= 0
        or cols <= 0
    ):
        raise ValueError(
            "Grid rows and columns must be positive integers."
        )

    if rows > height or cols > width:
        raise ValueError(
            "Grid dimensions cannot exceed slope raster dimensions."
        )

    # Validate statistic.
    if statistic not in {"max", "mean"}:
        raise ValueError(
            "Statistic must be either 'max' or 'mean'."
        )

    # Convert to floating-point values.
    slope_deg = slope_deg.astype(
        np.float64,
        copy=False,
    )

    # Reject physically invalid slope values.
    valid = np.isfinite(slope_deg)

    if np.any(
        valid
        & (
            (slope_deg < 0)
            | (slope_deg > 90)
        )
    ):
        raise ValueError(
            "Slope values must be between 0 and 90 degrees."
        )

    # -----------------------------------------------------
    # Divide raster into output grid cells
    # -----------------------------------------------------

    output: List[List[Optional[float]]] = []

    for row_index in range(rows):

        output_row: List[Optional[float]] = []

        row_start = int(
            row_index * height / rows
        )

        row_end = int(
            (row_index + 1) * height / rows
        )

        for col_index in range(cols):

            col_start = int(
                col_index * width / cols
            )

            col_end = int(
                (col_index + 1) * width / cols
            )

            block = slope_deg[
                row_start:row_end,
                col_start:col_end,
            ]

            # Ignore NaN and infinite values.
            valid_values = block[
                np.isfinite(block)
            ]

            if valid_values.size == 0:

                output_row.append(None)

            elif statistic == "max":

                output_row.append(
                    float(np.max(valid_values))
                )

            else:

                output_row.append(
                    float(np.mean(valid_values))
                )

        output.append(output_row)

    return output
