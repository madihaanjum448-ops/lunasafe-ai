import React, { useRef, useState } from 'react';
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
        title="Reset Zoom & Pan"
        aria-label="Reset Zoom and Pan"
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
 * Reusable image viewer with pan & zoom and perfectly registered SVG overlay
 */
export default function ImageViewer({ children, overlayTitle, extraToolbarActions }) {
  const { imageMeta } = useMission();
  const [scale, setScale] = useState(0.22);
  const containerRef = useRef(null);

  return (
    <div
      ref={containerRef}
      className="relative w-full h-[600px] md:h-[720px] bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl flex flex-col"
    >
      {/* Top Header Bar */}
      <div className="relative z-10 flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 bg-slate-900/85 backdrop-blur border-b border-slate-800 text-xs">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 font-medium text-slate-200">
            <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
            {overlayTitle || 'Surface Telemetry Viewer'}
          </span>
          <span className="text-slate-400 font-mono hidden sm:inline">
            Native Canvas: {imageMeta.width} × {imageMeta.height} px {imageMeta.isSample && '(Mock value)'}
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

      {/* Main Pan & Zoom Stage */}
      <div className="relative flex-1 w-full h-full bg-slate-950 cursor-grab active:cursor-grabbing">
        <TransformWrapper
          initialScale={0.22}
          minScale={0.08}
          maxScale={6}
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
            {/* Registered container matching image natural dimensions */}
            <div
              className="relative select-none"
              style={{
                width: `${imageMeta.width}px`,
                height: `${imageMeta.height}px`,
              }}
            >
              {/* Satellite Image */}
              <img
                src={imageMeta.src}
                alt="Lunar satellite observation"
                width={imageMeta.width}
                height={imageMeta.height}
                className="block w-full h-full object-contain pointer-events-none select-none"
                draggable={false}
              />

              {/* SVG Overlay: viewBox precisely equals image dimensions */}
              <svg
                className="absolute inset-0 w-full h-full pointer-events-auto"
                viewBox={`0 0 ${imageMeta.width} ${imageMeta.height}`}
                preserveAspectRatio="none"
              >
                {children}
              </svg>
            </div>
          </TransformComponent>
        </TransformWrapper>
      </div>

      {/* Bottom Status Ribbon */}
      <div className="px-4 py-2 bg-slate-900/90 border-t border-slate-800 text-[11px] text-slate-400 flex flex-wrap items-center justify-between gap-2">
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
