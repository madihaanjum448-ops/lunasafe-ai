import React, { useState } from 'react';
import sampleResult from '../mock/sampleResult.json';
import sampleImageSrc from '../assets/lunar_sample.jpg';
import { MissionContext } from './MissionContextInstance';
import {
  MAX_FILE_SIZE_BYTES,
  MAX_IMAGE_WIDTH,
  MAX_IMAGE_HEIGHT,
  UPLOAD_ERROR_MESSAGES,
  MULTIPLE_FILES_NOTE,
  isValidFileType,
} from '../constants/upload';

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
  const [uploadNote, setUploadNote] = useState(null);

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
    setUploadNote(null);
    setUploadSuccess('Sample illustration loaded successfully.');
  };

  /**
   * Process a user-uploaded image file with validation:
   * 1. Wrong file type (not PNG, JPEG, TIFF or WEBP)
   * 2. File too big (over 50 MB)
   * 3. Empty file (0 bytes)
   * 4. Broken or corrupt image (browser cannot decode it)
   * 5. Resolution over 8192 x 8192 px
   * 6. If multiple files uploaded, use only the first and show a note
   */
  const handleImageUpload = (filesInput) => {
    setUploadError(null);
    setUploadSuccess(null);
    setUploadNote(null);

    const fileList =
      filesInput instanceof FileList || Array.isArray(filesInput)
        ? Array.from(filesInput)
        : (filesInput ? [filesInput] : []);

    if (fileList.length === 0) return;

    // 6. If multiple files uploaded, note that only the first file is used
    if (fileList.length > 1) {
      setUploadNote(MULTIPLE_FILES_NOTE);
    }

    const file = fileList[0];

    // 1. Wrong file type (not PNG, JPEG, TIFF or WEBP)
    if (!isValidFileType(file)) {
      setUploadError(UPLOAD_ERROR_MESSAGES.INVALID_TYPE);
      return;
    }

    // 2. File too big (over 50 MB)
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setUploadError(UPLOAD_ERROR_MESSAGES.FILE_TOO_LARGE);
      return;
    }

    // 3. Empty file (0 bytes)
    if (file.size === 0) {
      setUploadError(UPLOAD_ERROR_MESSAGES.EMPTY_FILE);
      return;
    }

    // 4 & 5. Decode image to verify it's not corrupt and check dimensions
    const objectUrl = URL.createObjectURL(file);
    const testImg = new Image();

    testImg.onload = () => {
      const realWidth = testImg.naturalWidth;
      const realHeight = testImg.naturalHeight;

      // 4. Broken or corrupt image (cannot decode valid dimensions)
      if (!realWidth || !realHeight) {
        URL.revokeObjectURL(objectUrl);
        setUploadError(UPLOAD_ERROR_MESSAGES.CORRUPT_IMAGE);
        return;
      }

      // 5. Resolution over 8192 x 8192 px
      if (realWidth > MAX_IMAGE_WIDTH || realHeight > MAX_IMAGE_HEIGHT) {
        URL.revokeObjectURL(objectUrl);
        setUploadError(UPLOAD_ERROR_MESSAGES.IMAGE_TOO_LARGE);
        return;
      }

      // All validation passed: clear any previous error and replace active image
      setUploadError(null);

      const realSizeBytes = file.size;
      const realFormattedSize =
        realSizeBytes >= 1024 * 1024
          ? `${(realSizeBytes / (1024 * 1024)).toFixed(2)} MB`
          : `${(realSizeBytes / 1024).toFixed(1)} KB`;

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

      // Clear mock analysis data for user uploads
      setDetections([]);
      setHazardCells([]);
      setWarnings([]);
      setSelectedCell(null);

      setUploadSuccess(`Successfully loaded "${file.name}" (${realWidth}×${realHeight}px, ${realFormattedSize}).`);
    };

    testImg.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      setUploadError(UPLOAD_ERROR_MESSAGES.CORRUPT_IMAGE);
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
        uploadNote,
        setUploadNote,
        loadSampleData,
        handleImageUpload,
      }}
    >
      {children}
    </MissionContext.Provider>
  );
}
export default MissionProvider;
