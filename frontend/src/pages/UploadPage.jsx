import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMission } from '../context/useMission';
import {
  ACCEPTED_FILE_TYPES_STRING,
  MAX_IMAGE_WIDTH,
  MAX_IMAGE_HEIGHT,
  MAX_FILE_SIZE_MB,
} from '../constants/upload';

export default function UploadPage() {
  const {
    imageMeta,
    uploadError,
    setUploadError,
    uploadSuccess,
    uploadNote,
    setUploadNote,
    handleImageUpload,
    loadSampleData,
    detections,
    hazardCells,
  } = useMission();

  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  // Handle standard file selection
  const onFileChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleImageUpload(files);
    }
    if (e.target) {
      e.target.value = '';
    }
  };

  // Drag and drop handlers
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleImageUpload(files);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Page Title & Context */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs uppercase tracking-widest text-cyan-400 font-mono font-semibold">
            Lunar Reconnaissance & Safety Pipeline
          </span>
          <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-mono">
            Mock Data Mode
          </span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
          Orbital Satellite Image Ingestion
        </h1>
        <p className="text-slate-400 text-sm sm:text-base max-w-3xl">
          Upload lunar surface imagery to perform automated boulder detection and hazard grid evaluation for safe autonomous touchdown.
        </p>
      </div>

      {/* Multiple Files Info Note */}
      {uploadNote && (
        <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-500/40 text-amber-200 text-xs flex items-center justify-between shadow-md animate-in fade-in duration-200">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{uploadNote}</span>
          </div>
          <button
            onClick={() => setUploadNote(null)}
            className="text-amber-400 hover:text-white p-1"
            aria-label="Dismiss note"
          >
            ✕
          </button>
        </div>
      )}

      {/* Validation Alert: Error message */}
      {uploadError && (
        <div className="p-4 rounded-xl bg-red-950/60 border border-red-500/60 text-red-200 text-sm flex items-start gap-3 shadow-lg shadow-red-950/40 animate-in fade-in duration-200">
          <svg className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="flex-1">
            <h4 className="font-semibold text-red-100">Upload Validation Error</h4>
            <p className="mt-0.5 text-xs text-red-300 leading-relaxed">{uploadError}</p>
          </div>
          <button
            onClick={() => setUploadError(null)}
            className="text-red-400 hover:text-white p-1"
            aria-label="Dismiss error"
          >
            ✕
          </button>
        </div>
      )}

      {/* Success Notification */}
      {uploadSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-950/50 border border-emerald-500/50 text-emerald-200 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
            </svg>
            <span>{uploadSuccess}</span>
          </div>
          <span className="text-emerald-400 font-mono text-[11px]">Ready for inspection</span>
        </div>
      )}

      {/* Main Upload Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Upload Dropzone (Left column) */}
        <div className="lg:col-span-7 space-y-5">
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-200 flex flex-col items-center justify-center min-h-[340px] group ${
              isDragging
                ? 'border-cyan-400 bg-cyan-950/30 scale-[1.01]'
                : 'border-slate-700 hover:border-cyan-500/70 bg-slate-900/60 hover:bg-slate-900/90'
            }`}
          >
            {/* Hidden native input with strict image acceptance and multiple selection support */}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept={ACCEPTED_FILE_TYPES_STRING}
              onChange={onFileChange}
              className="hidden"
            />

            <div className="w-16 h-16 rounded-2xl bg-cyan-950/60 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mb-4 group-hover:scale-110 group-hover:border-cyan-400 transition-all shadow-lg shadow-cyan-950/50">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>

            <h3 className="text-base sm:text-lg font-semibold text-slate-100 group-hover:text-cyan-300 transition-colors">
              Drop lunar satellite image here, or{' '}
              <span className="text-cyan-400 underline decoration-cyan-500/40 underline-offset-4">browse</span>
            </h3>
            <p className="text-xs text-slate-400 mt-2 max-w-sm leading-relaxed">
              Accepts high-resolution orbital imagery in <strong>PNG, JPEG, TIFF, or WEBP</strong> format.
            </p>

            <div className="mt-4 flex items-center gap-2 text-[11px] text-slate-400">
              <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">Images only</span>
              <span>•</span>
              <span>Max size {MAX_FILE_SIZE_MB} MB</span>
              <span>•</span>
              <span>Max resolution up to {MAX_IMAGE_WIDTH}×{MAX_IMAGE_HEIGHT}px</span>
            </div>
          </div>

          {/* Quick preset button: Load Sample Illustration */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h4 className="text-sm font-semibold text-slate-200">Need sample lunar data?</h4>
              <p className="text-xs text-slate-400">
                Load a sample illustration (AI-generated, not real LROC data) with mock detections and an 8×8 hazard grid.
              </p>
            </div>
            <button
              type="button"
              onClick={loadSampleData}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 hover:text-white border border-slate-700 text-xs font-medium transition-colors flex items-center justify-center gap-2 flex-shrink-0"
            >
              <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Load Sample Illustration
            </button>
          </div>
        </div>

        {/* Chosen Image Preview & Metadata (Right column) */}
        <div className="lg:col-span-5 space-y-5">
          <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
                Active Image Preview
              </h3>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                {imageMeta.isSample ? 'Mock illustration' : 'User Upload'}
              </span>
            </div>

            {/* Image Preview Thumbnail */}
            <div className="relative aspect-square w-full rounded-xl overflow-hidden bg-slate-950 border border-slate-800 group shadow-inner">
              <img
                src={imageMeta.src}
                alt="Selected lunar landing target preview"
                className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950/80 via-transparent to-transparent pointer-events-none"></div>

              {/* Resolution badge overlay */}
              <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between text-[11px] text-white">
                <span className="px-2 py-0.5 rounded bg-slate-900/90 backdrop-blur font-mono border border-slate-700 flex items-center gap-1">
                  <span>{imageMeta.width} × {imageMeta.height} px</span>
                  {imageMeta.isSample && (
                    <span className="text-[10px] text-amber-300 font-sans font-medium">
                      (Mock value)
                    </span>
                  )}
                </span>
                <span className="px-2 py-0.5 rounded bg-slate-900/90 backdrop-blur font-mono border border-slate-700 flex items-center gap-1">
                  <span>{imageMeta.fileSize}</span>
                  {imageMeta.isSample && (
                    <span className="text-[10px] text-amber-300 font-sans font-medium">
                      (Mock value)
                    </span>
                  )}
                </span>
              </div>
            </div>

            {/* REQUIRED STATUS LINE: Pixel-scale metadata availability */}
            <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400">Pixel-Scale Metadata:</span>
                {imageMeta.pixelScaleM !== null ? (
                  <span className="font-mono font-semibold text-emerald-400 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                    <span>Available ({imageMeta.pixelScaleM} m/px)</span>
                    {imageMeta.isSample && (
                      <span className="text-[10px] font-sans px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 font-medium">
                        Mock value
                      </span>
                    )}
                  </span>
                ) : (
                  <span className="font-mono font-semibold text-amber-400 flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                    Unavailable
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 leading-normal">
                {imageMeta.pixelScaleM !== null
                  ? (imageMeta.isSample
                    ? 'Mock scale used for demonstration only.'
                    : `Spatial resolution calibrated: each pixel corresponds to ${imageMeta.pixelScaleM} meters on the lunar surface.`)
                  : 'Pixel scale is Unavailable until the backend provides it.'}
              </p>
            </div>

            {/* Quick Metadata Table */}
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Target Identifier:</span>
                <span className="font-mono text-slate-200">
                  {imageMeta.id}
                  {imageMeta.isSample && (
                    <span className="ml-1.5 text-[10px] text-amber-400 font-sans font-medium">
                      (Mock value)
                    </span>
                  )}
                </span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">File Name:</span>
                <span className="font-mono text-slate-200 truncate max-w-[200px]" title={imageMeta.fileName}>
                  {imageMeta.fileName}
                </span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Resolution:</span>
                <span className="font-mono text-slate-200">
                  {imageMeta.width} × {imageMeta.height} px
                  {imageMeta.isSample && (
                    <span className="ml-1.5 text-[10px] text-amber-400 font-sans font-medium">
                      (Mock value)
                    </span>
                  )}
                </span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">File Size:</span>
                <span className="font-mono text-slate-200">
                  {imageMeta.fileSize}
                  {imageMeta.isSample && (
                    <span className="ml-1.5 text-[10px] text-amber-400 font-sans font-medium">
                      (Mock value)
                    </span>
                  )}
                </span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Pixel Scale:</span>
                <span className="font-mono text-slate-200">
                  {imageMeta.pixelScaleM !== null ? (
                    <>
                      {imageMeta.pixelScaleM} m/px
                      {imageMeta.isSample && (
                        <span className="ml-1.5 text-[10px] text-amber-400 font-sans font-medium">
                          (Mock value)
                        </span>
                      )}
                    </>
                  ) : (
                    <span className="text-amber-400 italic">Unavailable</span>
                  )}
                </span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-800/60">
                <span className="text-slate-400">Precomputed Boulders:</span>
                <span className="font-mono text-cyan-300 font-bold">
                  {imageMeta.isSample ? (
                    <>
                      {detections.length} obstacles
                      <span className="ml-1.5 text-[10px] text-amber-400 font-sans font-normal">
                        (Mock value)
                      </span>
                    </>
                  ) : (
                    <span className="text-slate-400 font-normal">None (Not processed yet)</span>
                  )}
                </span>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-slate-400">Hazard Grid Partition:</span>
                <span className="font-mono text-slate-200">
                  {imageMeta.isSample ? (
                    <>
                      8×8 ({hazardCells.length} cells)
                      <span className="ml-1.5 text-[10px] text-amber-400 font-sans font-normal">
                        (Mock value)
                      </span>
                    </>
                  ) : (
                    <span className="text-slate-400 font-normal">None (Not processed yet)</span>
                  )}
                </span>
              </div>
            </div>

            {/* Navigation Buttons to next screens */}
            <div className="pt-2 grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <button
                type="button"
                onClick={() => navigate('/detections')}
                className="w-full py-2.5 px-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-medium text-xs transition-colors flex items-center justify-center gap-1.5 shadow-lg shadow-cyan-950/60"
              >
                Inspect Detections →
              </button>

              <button
                type="button"
                onClick={() => navigate('/hazard-map')}
                className="w-full py-2.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs border border-slate-700 transition-colors flex items-center justify-center gap-1.5"
              >
                View Hazard Map →
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
