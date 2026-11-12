import React, { useEffect, useRef, useState } from 'react';
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
import { normalizeResult } from '../constants/schema';
import sampleAnalyzeRequest from '../mock/sampleAnalyzeRequest.json';
import sampleAnalyzeResponse from '../mock/sampleAnalyzeResponse.json';
import { analyze, getConfig, uploadImage } from '../api/client';

const initialNormalizedSample = normalizeResult(sampleResult);

export function MissionProvider({ children }) {
  // Currently loaded image state
  const [imageMeta, setImageMeta] = useState({
    id: sampleResult.image.id,
    src: sampleImageSrc,
    width: sampleResult.image.width,
    height: sampleResult.image.height,
    pixelScaleM: sampleResult.image.pixel_scale_m,
    sunElevationDeg: sampleResult.image.sun_elevation_deg,
    projection: sampleResult.image.projection,
    fileName: 'sample_lunar_illustration.png',
    fileSize: '12.8 MB',
    isSample: true,
  });

  // Detection and hazard data from normalized source
  const [detections, setDetections] = useState(initialNormalizedSample.detections);
  const [hazardCells, setHazardCells] = useState(initialNormalizedSample.hazardCells);
  const [warnings, setWarnings] = useState(initialNormalizedSample.warnings);

  // Confidence threshold filter for boulder detections (0.00 - 1.00)
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.60);

  // Currently selected hazard grid cell for Region Explanation panel
  const [selectedCell, setSelectedCell] = useState(null);

  // Layer toggles
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [showDetectionsInHazardMap, setShowDetectionsInHazardMap] = useState(false);
  // Boulder Detections page layer toggles (persisted across page switches)
  const [showBoulderBoxes, setShowBoulderBoxes] = useState(true);
  const [showConfidenceLabels, setShowConfidenceLabels] = useState(true);


  // Upload feedback state
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [uploadNote, setUploadNote] = useState(null);

  // Backend integration state
  const [loading, setLoading] = useState(false);
  const [loadingLabel, setLoadingLabel] = useState('');
  const [apiError, setApiError] = useState(null);
  const [hasResult, setHasResult] = useState(true); // starts on the bundled sample
  const [isMock, setIsMock] = useState(true);
  const [backendImage, setBackendImage] = useState(null);
  const [missingMetadata, setMissingMetadata] = useState([]);
  const [backendWarnings, setBackendWarnings] = useState([]);
  const [analysisConfig, setAnalysisConfig] = useState(null);
  const [pendingDetections, setPendingDetections] = useState(null);
  const [thresholds, setThresholds] = useState({});
  const [resultSource, setResultSource] = useState('sample'); // 'sample' | 'backend' | 'precomputed'
  const [resultLabel, setResultLabel] = useState(null);
  const uploadedFileRef = useRef(null);
  const uploadSeq = useRef(0);

  // Default thresholds for the explanation panel (placeholders, not validated limits)
  useEffect(() => {
    let cancelled = false;
    getConfig()
      .then((cfg) => {
        if (!cancelled) setAnalysisConfig(cfg);
      })
      .catch(() => {
        /* backend may be offline; the panel then shows thresholds as unavailable */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  /**
   * Send the file to /api/upload so the backend reads metadata and reports what is missing.
   * Manual values (from the form) are passed through; the backend never invents missing ones.
   */
  const syncWithBackend = async (file, manualMeta = {}) => {
    const seq = ++uploadSeq.current;
    setLoading(true);
    setLoadingLabel('Validating image and reading metadata…');
    setApiError(null);
    try {
      const res = await uploadImage(file, manualMeta);
      if (seq !== uploadSeq.current) return;
      const info = res.image || {};
      setBackendImage(info);
      setMissingMetadata(res.missing_metadata || []);
      setBackendWarnings(res.warnings || []);
      setImageMeta((prev) => ({
        ...prev,
        pixelScaleM: info.pixel_scale_m ?? null,
        sunElevationDeg: info.sun_elevation_deg ?? null,
        projection: info.projection ?? null,
      }));
    } catch (err) {
      if (seq !== uploadSeq.current) return;
      setApiError(err.message);
    } finally {
      if (seq === uploadSeq.current) setLoading(false);
    }
  };

  /** Re-send the current file with manually entered metadata. */
  const applyManualMetadata = (manualMeta) => {
    if (!uploadedFileRef.current) {
      setApiError('Upload an image first.');
      return;
    }
    syncWithBackend(uploadedFileRef.current, manualMeta);
  };

  /** Load detections produced by the AI module (JSON: an array, or { detections, shadow_lengths_px, recall }). */
  const loadDetectionsFile = async (file) => {
    setApiError(null);
    try {
      const parsed = JSON.parse(await file.text());
      const list = Array.isArray(parsed) ? parsed : parsed.detections;
      if (!Array.isArray(list) || list.some((d) => !d || !Array.isArray(d.bbox))) {
        throw new Error('Expected a list of detections, each with id, bbox and confidence.');
      }
      setPendingDetections({
        name: file.name,
        detections: list,
        shadow_lengths_px: Array.isArray(parsed) ? {} : parsed.shadow_lengths_px || {},
        recall: Array.isArray(parsed) ? null : parsed.recall || null,
        isMock: Array.isArray(parsed) ? false : Boolean(parsed.is_mock),
      });
    } catch (err) {
      setPendingDetections(null);
      setApiError(`Could not read detections file: ${err.message}`);
    }
  };

  const setThreshold = (key, value) =>
    setThresholds((prev) => ({ ...prev, [key]: value === '' ? null : value }));
  const resetThresholds = () => setThresholds({});

  const thresholdOverrides = () =>
    Object.fromEntries(
      Object.entries(thresholds)
        .filter(([, v]) => v !== null && v !== '' && !Number.isNaN(Number(v)))
        .map(([k, v]) => [k, Number(v)])
    );

  /** Show a saved analysis (offline demo or a case-study JSON) without calling the backend. */
  const applyPrecomputed = (raw, { useSampleImage }) => {
    const n = normalizeResult(raw);
    const info = n.image || {};
    setImageMeta((prev) =>
      useSampleImage
        ? {
            id: info.id || 'offline_demo',
            src: sampleImageSrc,
            width: info.width,
            height: info.height,
            pixelScaleM: info.pixel_scale_m ?? null,
            sunElevationDeg: info.sun_elevation_deg ?? null,
            projection: info.projection ?? null,
            fileName: 'sample_lunar_illustration.png',
            fileSize: '—',
            isSample: true,
          }
        : {
            ...prev,
            width: info.width || prev.width,
            height: info.height || prev.height,
            pixelScaleM: info.pixel_scale_m ?? prev.pixelScaleM,
            sunElevationDeg: info.sun_elevation_deg ?? prev.sunElevationDeg,
            projection: info.projection ?? prev.projection,
          }
    );
    setDetections(n.detections);
    setHazardCells(n.hazardCells);
    setWarnings(n.warnings);
    setIsMock(n.isMock);
    setHasResult(true);
    setResultSource('precomputed');
    setSelectedCell(null);
    setApiError(null);
  };

  /** Offline fallback: pre-computed demo result bundled with the app (works without the backend). */
  const loadOfflineDemo = () => {
    uploadSeq.current += 1; // ignore any request still in flight
    setLoading(false);
    setResultLabel(null);
    applyPrecomputed(sampleAnalyzeResponse, { useSampleImage: true });
    setUploadSuccess('Offline demo loaded (pre-computed, is_mock: true). No backend needed.');
  };

  /**
   * Known-site case study: loads /case-study/site.jpg and /case-study/result.json
   * without calling the backend.
   */
  const loadCaseStudy = async () => {
    uploadSeq.current += 1;
    setLoading(true);
    setLoadingLabel('Loading known-site case study…');
    setUploadError(null);
    setApiError(null);
    setUploadNote(null);
    setUploadSuccess(null);

    try {
      const jsonRes = await fetch('/case-study/result.json');
      if (!jsonRes.ok) {
        throw new Error('Case study files not found in public/case-study/.');
      }
      const contentType = jsonRes.headers.get('content-type') || '';
      if (contentType.includes('text/html')) {
        throw new Error('Case study files not found in public/case-study/.');
      }
      let raw;
      try {
        raw = await jsonRes.json();
      } catch {
        throw new Error('Case study files not found in public/case-study/.');
      }

      const realDims = await new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight });
        img.onerror = () => reject(new Error('Case study files not found in public/case-study/.'));
        img.src = '/case-study/site.jpg';
      });

      if (!realDims.width || !realDims.height) {
        throw new Error('Case study files not found in public/case-study/.');
      }

      setImageMeta({
        id: 'case_study',
        src: '/case-study/site.jpg',
        width: realDims.width,
        height: realDims.height,
        pixelScaleM: raw.image?.pixel_scale_m ?? null,
        sunElevationDeg: raw.image?.sun_elevation_deg ?? null,
        projection: raw.image?.projection ?? null,
        fileName: 'Known-site case study',
        fileSize: '—',
        isSample: false,
      });

      const rawWithRealDims = {
        ...raw,
        hazard_cells: raw.hazard_cells || raw.cells,
        image: {
          ...(raw.image || {}),
          width: realDims.width,
          height: realDims.height,
        },
      };

      applyPrecomputed(rawWithRealDims, { useSampleImage: false });
      setResultLabel('Pre-computed case study');
      setPendingDetections(null);
      uploadedFileRef.current = null;
      setUploadSuccess('Pre-computed case study loaded (no backend call).');
    } catch {
      setUploadError('Case study files not found in public/case-study/.');
      setApiError('Case study files not found in public/case-study/.');
    } finally {
      setLoading(false);
    }
  };

  /** Load a saved /api/analyze response (for example the known-site case study) onto the current image. */
  const loadResultFile = async (file) => {
    setApiError(null);
    if (imageMeta.isSample) {
      setApiError('Upload the site image first, then load its saved result so the overlays sit on the right picture.');
      return;
    }
    try {
      const raw = JSON.parse(await file.text());
      if (!Array.isArray(raw.hazard_cells) && !Array.isArray(raw.cells)) {
        throw new Error('Expected an /api/analyze response with hazard_cells.');
      }
      applyPrecomputed({ ...raw, hazard_cells: raw.hazard_cells || raw.cells }, { useSampleImage: false });
      setUploadSuccess(`Saved result "${file.name}" loaded (no backend call).`);
    } catch (err) {
      setApiError(`Could not read saved result: ${err.message}`);
    }
  };

  /**
   * Run /api/analyze. Uses loaded detections (real if is_mock is false) or, when none are loaded,
   * the bundled demo detections, which are always flagged is_mock: true.
   */
  const runAnalysis = async () => {
    setApiError(null);
    setLoading(true);
    setLoadingLabel('Running hazard analysis…');
    try {
      const demo = !pendingDetections;
      const image = imageMeta.isSample
        ? sampleAnalyzeRequest.image
        : backendImage || {
            id: imageMeta.id,
            width: imageMeta.width,
            height: imageMeta.height,
            pixel_scale_m: imageMeta.pixelScaleM,
            sun_elevation_deg: imageMeta.sunElevationDeg,
            projection: imageMeta.projection,
            metadata_source: 'unknown',
          };
      const payload = demo
        ? {
            image,
            detections: sampleAnalyzeRequest.detections,
            shadow_lengths_px: sampleAnalyzeRequest.shadow_lengths_px || {},
            config: { ...sampleAnalyzeRequest.config, ...thresholdOverrides() },
            slope_by_cell: sampleAnalyzeRequest.slope_by_cell,
            recall: sampleAnalyzeRequest.recall,
            is_mock: true,
          }
        : {
            image,
            detections: pendingDetections.detections,
            shadow_lengths_px: pendingDetections.shadow_lengths_px,
            recall: pendingDetections.recall,
            is_mock: pendingDetections.isMock,
            ...(Object.keys(thresholdOverrides()).length > 0
              ? { config: { ...(analysisConfig || {}), ...thresholdOverrides() } }
              : {}),
          };
      const result = await analyze(payload);
      const n = normalizeResult(result);
      setDetections(n.detections);
      setHazardCells(n.hazardCells);
      setWarnings(n.warnings);
      setIsMock(n.isMock);
      setHasResult(true);
      setResultSource('backend');
      setSelectedCell(null);
    } catch (err) {
      setApiError(err.message);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Reset data back to default mock lunar sample
   */
  const loadSampleData = () => {
    uploadSeq.current += 1;
    setLoading(false);
    setImageMeta({
      id: sampleResult.image.id,
      src: sampleImageSrc,
      width: sampleResult.image.width,
      height: sampleResult.image.height,
      pixelScaleM: sampleResult.image.pixel_scale_m,
      sunElevationDeg: sampleResult.image.sun_elevation_deg,
      projection: sampleResult.image.projection,
      fileName: 'sample_lunar_illustration.png',
      fileSize: '12.8 MB',
      isSample: true,
    });
    setDetections(initialNormalizedSample.detections);
    setHazardCells(initialNormalizedSample.hazardCells);
    setWarnings(initialNormalizedSample.warnings);
    setSelectedCell(null);
    setUploadError(null);
    setUploadNote(null);
    setApiError(null);
    setHasResult(true);
    setIsMock(true);
    setResultSource('sample');
    setResultLabel(null);
    setBackendImage(null);
    setMissingMetadata([]);
    setBackendWarnings([]);
    setPendingDetections(null);
    uploadedFileRef.current = null;
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
        pixelScaleM: null,         // Unavailable until backend provides it
        sunElevationDeg: null,     // Unavailable until backend provides it
        projection: null,          // Unavailable until backend provides it
        fileName: file.name,
        fileSize: realFormattedSize,
        isSample: false,
      });

      // Clear previous analysis data for user uploads
      setDetections([]);
      setHazardCells([]);
      setWarnings([]);
      setSelectedCell(null);
      setHasResult(false);
      setIsMock(false);
      setResultSource('backend');
      setResultLabel(null);
      setBackendImage(null);
      setMissingMetadata([]);
      setBackendWarnings([]);
      setPendingDetections(null);

      // Ask the backend to validate the file and read metadata
      uploadedFileRef.current = file;
      syncWithBackend(file);

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
        showBoulderBoxes,
        setShowBoulderBoxes,
        showConfidenceLabels,
        setShowConfidenceLabels,
        uploadError,
        setUploadError,
        uploadSuccess,
        setUploadSuccess,
        uploadNote,
        setUploadNote,
        loadSampleData,
        handleImageUpload,
        loading,
        loadingLabel,
        apiError,
        setApiError,
        hasResult,
        isMock,
        missingMetadata,
        backendWarnings,
        analysisConfig,
        pendingDetections,
        loadDetectionsFile,
        applyManualMetadata,
        runAnalysis,
        thresholds,
        setThreshold,
        resetThresholds,
        resultSource,
        resultLabel,
        loadOfflineDemo,
        loadCaseStudy,
        loadResultFile,
      }}
    >
      {children}
    </MissionContext.Provider>
  );
}
export default MissionProvider;
