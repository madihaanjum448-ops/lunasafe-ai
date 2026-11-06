import React, { useRef, useState, useEffect } from 'react';
import { TransformWrapper, TransformComponent, useControls } from 'react-zoom-pan-pinch';
import { useMission } from '../context/useMission';

/**
 * Floating zoom/pan toolbar inside the viewer
 */
function ViewerControls({ currentScale }) {
  const { zoomIn, zoomOut, resetTransform } = useControls();

  return (
    <div className="absolute top-4 right-4 z-20 flex items-center gap-1.5 bg-slate-900/90 backdrop-blur-md border border-slate-700/80 rounded-xl p-1.5 shadow-xl">
      <button
        onClick={() => zoomIn(0.3)}
        className="p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
        title="Zoom In"
        aria-label="Zoom In"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
        </svg>
      </button>

      <button
        onClick={() => zoomOut(0.3)}
        className="p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
        title="Zoom Out"
        aria-label="Zoom Out"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20 12H4" />
        </svg>
      </button>

      <button
        onClick={() => resetTransform()}
        className="p-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
        title="Reset & Fit to View"
        aria-label="Reset and Fit to View"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      </button>

      <div className="h-5 w-px bg-slate-700 mx-1"></div>

      <div className="px-2 py-1 text-xs font-mono font-semibold text-cyan-300 min-w-[50px] text-center">
        {(currentScale * 100).toFixed(0)}%
      </div>
    </div>
  );
}

/**
 * Reusable image viewer with pan & zoom and registered SVG overlay
 */
export default function ImageViewer({ children, overlayTitle, extraToolbarActions }) {
  const { imageMeta } = useMission();
  const stageRef = useRef(null);
  const [stageDims, setStageDims] = useState(null);
  const [scale, setScale] = useState(1);

  // Measure container width and height once mounted or on image change
  useEffect(() => {
    const el = stageRef.current;
    if (!el) return;

    const measure = () => {
      const rect = el.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        setStageDims({ width: rect.width, height: rect.height });
      }
    };

    measure();
  }, [imageMeta.id, imageMeta.width, imageMeta.height]);

  // Compute initial scale as min(containerWidth / imageWidth, containerHeight / imageHeight)
  const containerWidth = stageDims?.width || 800;
  const containerHeight = stageDims?.height || 500;
  const fitScale = Math.min(
    containerWidth / imageMeta.width,
    containerHeight / imageMeta.height
  );
  // Fit with 4% padding so full image is visible
  const initialScale = Math.max(0.005, Number((fitScale * 0.96).toFixed(4)));
  // Set minScale below that so user can zoom out further
  const minScale = Math.max(0.001, Number((initialScale * 0.5).toFixed(4)));

  return (
    <div className="relative w-full h-[70vh] bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl flex flex-col">
      {/* Top Header Bar */}
      <div className="relative z-10 flex-shrink-0 flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 bg-slate-900/85 backdrop-blur border-b border-slate-800 text-xs">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 font-medium text-slate-200">
            <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
            {overlayTitle || 'Surface Telemetry Viewer'}
          </span>
          <span className="text-slate-400 font-mono hidden sm:inline">
            Canvas: {imageMeta.width} × {imageMeta.height} px {imageMeta.isSample && '(Mock value)'}
          </span>
        </div>

        <div className="flex items-center gap-3">
          {extraToolbarActions}
          <div className="hidden md:flex items-center gap-1 text-[11px] text-slate-400">
            <kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 font-mono">
              Scroll
            </kbd>{' '}
            Zoom •{' '}
            <kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 font-mono">
              Drag
            </kbd>{' '}
            Pan
          </div>
        </div>
      </div>

      {/* Main Pan & Zoom Stage with fixed flex-1 height */}
      <div
        ref={stageRef}
        className="relative flex-1 w-full h-full bg-slate-950 overflow-hidden cursor-grab active:cursor-grabbing"
      >
        {stageDims ? (
          <TransformWrapper
            key={`${imageMeta.id}-${stageDims.width}x${stageDims.height}`}
            initialScale={initialScale}
            minScale={minScale}
            maxScale={8}
            centerOnInit={true}
            wheel={{ step: 0.1 }}
            doubleClick={{ mode: 'zoomIn' }}
            onTransformed={(ref) => {
              if (ref && ref.state) {
                setScale(ref.state.scale);
              }
            }}
          >
            <ViewerControls currentScale={scale} />

            <TransformComponent
              wrapperClass="!w-full !h-full"
              contentClass="!w-full !h-full flex items-center justify-center"
            >
              {/* 1. ONE wrapper div with explicit width = image width px and height = image height px, position: relative */}
              <div
                style={{
                  position: 'relative',
                  width: `${imageMeta.width}px`,
                  height: `${imageMeta.height}px`,
                }}
              >
                {/* 2. <img> with width:100%; height:100%; max-width:none; display:block */}
                <img
                  src={imageMeta.src}
                  alt="Lunar satellite observation"
                  style={{
                    width: '100%',
                    height: '100%',
                    maxWidth: 'none',
                    display: 'block',
                    pointerEvents: 'none',
                    userSelect: 'none',
                  }}
                  draggable={false}
                />

                {/* 2. SVG overlay with position:absolute; inset:0; width:100%; height:100%; viewBox="0 0 {width} {height}" */}
                <svg
                  style={{
                    position: 'absolute',
                    top: 0,
                    right: 0,
                    bottom: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    pointerEvents: 'auto',
                  }}
                  viewBox={`0 0 ${imageMeta.width} ${imageMeta.height}`}
                  preserveAspectRatio="none"
                >
                  {children}
                </svg>
              </div>
            </TransformComponent>
          </TransformWrapper>
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-500 font-mono text-xs">
            Initializing zoom/pan viewport...
          </div>
        )}
      </div>

      {/* Bottom Status Ribbon */}
      <div className="flex-shrink-0 px-4 py-2 bg-slate-900/90 border-t border-slate-800 text-[11px] text-slate-400 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-3">
          <span>Image: <strong className="text-slate-200">{imageMeta.fileName}</strong></span>
          <span>
            Size: <span className="font-mono text-slate-300">{imageMeta.fileSize}</span>
            {imageMeta.isSample && <span className="text-amber-400 font-mono ml-1">(Mock value)</span>}
          </span>
        </div>
        <div>
          <span>Scale status: </span>
          {imageMeta.pixelScaleM !== null ? (
            <span className="text-emerald-400 font-mono font-medium">
              {imageMeta.pixelScaleM} m/pixel {imageMeta.isSample ? '(Mock value)' : '(Available)'}
            </span>
          ) : (
            <span className="text-amber-400 font-mono">
              Unavailable
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
