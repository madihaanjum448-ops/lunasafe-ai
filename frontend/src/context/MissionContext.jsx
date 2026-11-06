import React, { useState } from 'react';
import sampleResult from '../mock/sampleResult.json';
import sampleImageSrc from '../assets/lunar_sample.jpg';
import { MissionContext } from './MissionContextInstance';

export function MissionProvider({ children }) {
  // Currently loaded image state
  const [imageMeta, setImageMeta] = useState({
    id: sampleResult.image.id,
    src: sampleImageSrc,
    width: sampleResult.image.width,
    height: sampleResult.image.height,
    pixelScaleM: sampleResult.image.pixel_scale_m,
    fileName: 'sample_lunar_illustration.png',
    fileSize: '12.8 MB',
    isSample: true,
  });

  // Detection and hazard data from mock source
  const [detections, setDetections] = useState(sampleResult.detections);
  const [hazardCells, setHazardCells] = useState(sampleResult.hazard_cells);
  const [warnings, setWarnings] = useState(sampleResult.warnings);

  // Confidence threshold filter for boulder detections (0.00 - 1.00)
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.60);

  // Currently selected hazard grid cell for Region Explanation panel
  const [selectedCell, setSelectedCell] = useState(null);

  // Layer toggles
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [showDetectionsInHazardMap, setShowDetectionsInHazardMap] = useState(false);

  // Upload feedback state
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(null);

  /**
   * Reset data back to default mock lunar sample
   */
  const loadSampleData = () => {
    setImageMeta({
      id: sampleResult.image.id,
      src: sampleImageSrc,
      width: sampleResult.image.width,
      height: sampleResult.image.height,
      pixelScaleM: sampleResult.image.pixel_scale_m,
      fileName: 'sample_lunar_illustration.png',
      fileSize: '12.8 MB',
      isSample: true,
    });
    setDetections(sampleResult.detections);
    setHazardCells(sampleResult.hazard_cells);
    setWarnings(sampleResult.warnings);
    setSelectedCell(null);
    setUploadError(null);
    setUploadSuccess('Sample illustration loaded successfully.');
  };

  /**
   * Process a user-uploaded image file with validation
   */
  const handleImageUpload = (file) => {
    setUploadError(null);
    setUploadSuccess(null);

    if (!file) return;

    // Validate MIME type or file extension
    const validImageTypes = [
      'image/jpeg',
      'image/png',
      'image/webp',
      'image/tiff',
      'image/bmp',
      'image/gif'
    ];

    const isImageMime = validImageTypes.includes(file.type);
    const hasImageExt = /\.(jpe?g|png|webp|tiff?|bmp)$/i.test(file.name);

    if (!isImageMime && !hasImageExt) {
      setUploadError(
        `Invalid file format "${file.name}". Please upload a valid satellite image (PNG, JPEG, TIFF, or WEBP).`
      );
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    const testImg = new Image();

    testImg.onload = () => {
      // Read real width, height, and file size directly from the file in the browser
      const realWidth = testImg.naturalWidth;
      const realHeight = testImg.naturalHeight;
      const realSizeBytes = file.size;
      const realFormattedSize =
        realSizeBytes >= 1024 * 1024
          ? `${(realSizeBytes / (1024 * 1024)).toFixed(2)} MB`
          : `${(realSizeBytes / 1024).toFixed(1)} KB`;

      // Scale is set to null (displayed as "Unavailable" until backend provides it)
      setImageMeta({
        id: `img_${Date.now().toString(36)}`,
        src: objectUrl,
        width: realWidth,
        height: realHeight,
        pixelScaleM: null, // Scale metadata unavailable until backend provides it
        fileName: file.name,
        fileSize: realFormattedSize,
        isSample: false,
      });

      // Clear mock analysis data: do not show mock detections, hazard cells, or warnings for user uploads
      setDetections([]);
      setHazardCells([]);
      setWarnings([]);
      setSelectedCell(null);

      setUploadSuccess(`Successfully loaded "${file.name}" (${realWidth}×${realHeight}px, ${realFormattedSize}).`);
    };

    testImg.onerror = () => {
      setUploadError(
        `Failed to decode "${file.name}". The image file may be corrupted or unreadable.`
      );
    };

    testImg.src = objectUrl;
  };

  return (
    <MissionContext.Provider
      value={{
        imageMeta,
        setImageMeta,
        detections,
        hazardCells,
        warnings,
        confidenceThreshold,
        setConfidenceThreshold,
        selectedCell,
        setSelectedCell,
        showHeatmap,
        setShowHeatmap,
        showDetectionsInHazardMap,
        setShowDetectionsInHazardMap,
        uploadError,
        setUploadError,
        uploadSuccess,
        setUploadSuccess,
        loadSampleData,
        handleImageUpload,
      }}
    >
      {children}
    </MissionContext.Provider>
  );
}
export default MissionProvider;
