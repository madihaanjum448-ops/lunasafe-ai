/**
 * Metadata configuration, field names, and warning definitions for LunaSafe AI.
 * Centralizing field names here ensures they are easy to rename later.
 *
 * IMPORTANT: these keys must match the camelCase field names stored on
 * imageMeta in MissionContext (not the snake_case names in the JSON file).
 * Both MetadataSummaryCard and getMetadataWarnings read from these same keys
 * so they can never disagree.
 */

export const METADATA_FIELDS = {
  PIXEL_SCALE: 'pixelScaleM',
  SUN_ELEVATION: 'sunElevationDeg',
  PROJECTION: 'projection',
};

export const METADATA_WARNINGS = {
  PIXEL_SCALE_MISSING: 'Pixel scale unavailable. Physical sizes in metres cannot be computed.',
  SUN_ELEVATION_MISSING: 'Sun angle unavailable. Shadow-based height is not possible. A diameter-based estimate will be used and flagged low confidence.',
  PROJECTION_MISSING: 'Map projection unavailable.',
  ALL_FOUND: 'All required metadata found.',
  BACKEND_NOTE: 'Read by the backend once it is connected.',
};

/**
 * Computes missing metadata warning messages from an imageMeta object.
 * Reads the same camelCase fields that MetadataSummaryCard renders, so
 * the two cards are always in sync.
 *
 * A value is considered missing when it is null, undefined, or ''.
 * A numeric 0 is also treated as missing (no physical scale of 0 is valid).
 *
 * @param {Object} imageMeta  - The imageMeta object from MissionContext
 * @returns {string[]}        - Warning strings for every missing field
 */
export function getMetadataWarnings(imageMeta) {
  if (!imageMeta) {
    return [
      METADATA_WARNINGS.PIXEL_SCALE_MISSING,
      METADATA_WARNINGS.SUN_ELEVATION_MISSING,
      METADATA_WARNINGS.PROJECTION_MISSING,
    ];
  }

  const warnings = [];

  const pixelScale = imageMeta[METADATA_FIELDS.PIXEL_SCALE];
  if (pixelScale === null || pixelScale === undefined || pixelScale === '' || pixelScale === 0) {
    warnings.push(METADATA_WARNINGS.PIXEL_SCALE_MISSING);
  }

  const sunElevation = imageMeta[METADATA_FIELDS.SUN_ELEVATION];
  if (sunElevation === null || sunElevation === undefined || sunElevation === '' || sunElevation === 0) {
    warnings.push(METADATA_WARNINGS.SUN_ELEVATION_MISSING);
  }

  const projection = imageMeta[METADATA_FIELDS.PROJECTION];
  if (projection === null || projection === undefined || projection === '') {
    warnings.push(METADATA_WARNINGS.PROJECTION_MISSING);
  }

  return warnings;
}
