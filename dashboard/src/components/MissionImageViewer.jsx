import React, { useState, useRef } from 'react';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import { ZoomIn, ZoomOut, RotateCcw, Maximize2, Minimize2, Crosshair, Eye } from 'lucide-react';

export default function MissionImageViewer({
  src,
  alt = 'Lunar imagery',
  title,
  subtitle,
  badge,
  height = 'h-[440px]',
  initialScale = 1,
  className = '',
  footerInfo
}) {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [scaleDisplay, setScaleDisplay] = useState(100);

  const renderContent = (inModal = false) => (
    <div className={`relative flex flex-col bg-[#070a12] border border-slate-800 rounded-xl overflow-hidden group ${inModal ? 'w-full h-full' : height} ${className}`}>
      {/* Header bar */}
      {(title || badge) && (
        <div className="flex items-center justify-between px-4 py-2.5 bg-slate-900/90 border-b border-slate-800/80 z-10 backdrop-blur-md">
          <div className="flex items-center gap-2 overflow-hidden">
            <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shrink-0" />
            <span className="font-mono text-xs font-bold text-slate-200 uppercase tracking-wider truncate">
              {title || alt}
            </span>
            {subtitle && (
              <span className="text-[11px] text-slate-400 truncate hidden sm:inline">
                // {subtitle}
              </span>
            )}
          </div>
          {badge && (
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold tracking-wider bg-cyan-950/80 text-cyan-300 border border-cyan-700/50 shrink-0">
              {badge}
            </span>
          )}
        </div>
      )}

      {/* Main Pan/Zoom Stage */}
      <div className="relative flex-1 w-full overflow-hidden bg-[radial-gradient(#162038_1px,transparent_1px)] [background-size:16px_16px] cursor-grab active:cursor-grabbing">
        {/* Subtle grid crosshairs */}
        <div className="absolute top-3 left-3 text-slate-700 pointer-events-none z-10">
          <Crosshair size={14} />
        </div>
        <div className="absolute top-3 right-3 text-slate-700 pointer-events-none z-10">
          <Crosshair size={14} />
        </div>
        <div className="absolute bottom-12 left-3 text-slate-700 pointer-events-none z-10">
          <Crosshair size={14} />
        </div>

        <TransformWrapper
          initialScale={initialScale}
          minScale={0.2}
          maxScale={12}
          centerOnInit={true}
          limitToBounds={false}
          onTransformed={(ref) => {
            if (ref.state && ref.state.scale) {
              setScaleDisplay(Math.round(ref.state.scale * 100));
            }
          }}
        >
          {({ zoomIn, zoomOut, resetTransform }) => (
            <>
              {/* Floating controls HUD */}
              <div className="absolute bottom-3 right-3 flex items-center gap-1 bg-slate-900/90 border border-slate-700/80 rounded-lg p-1.5 z-20 backdrop-blur-md shadow-xl">
                <span className="font-mono text-[10px] text-slate-300 px-2 py-0.5 border-r border-slate-700/80">
                  {scaleDisplay}%
                </span>
                <button
                  onClick={() => zoomIn()}
                  className="p-1 text-slate-300 hover:text-cyan-400 hover:bg-slate-800 rounded transition-colors"
                  title="Zoom In (Scroll up)"
                >
                  <ZoomIn size={14} />
                </button>
                <button
                  onClick={() => zoomOut()}
                  className="p-1 text-slate-300 hover:text-cyan-400 hover:bg-slate-800 rounded transition-colors"
                  title="Zoom Out (Scroll down)"
                >
                  <ZoomOut size={14} />
                </button>
                <button
                  onClick={() => resetTransform()}
                  className="p-1 text-slate-300 hover:text-cyan-400 hover:bg-slate-800 rounded transition-colors"
                  title="Reset View"
                >
                  <RotateCcw size={14} />
                </button>
                {!inModal && (
                  <button
                    onClick={() => setIsFullscreen(true)}
                    className="p-1 text-slate-300 hover:text-cyan-400 hover:bg-slate-800 rounded transition-colors"
                    title="Fullscreen View"
                  >
                    <Maximize2 size={14} />
                  </button>
                )}
              </div>

              {/* Pan/Zoom Viewport */}
              <TransformComponent
                wrapperClass="!w-full !h-full flex items-center justify-center"
                contentClass="flex items-center justify-center"
              >
                <img
                  src={src}
                  alt={alt}
                  className="max-h-full max-w-full object-contain rounded select-none pointer-events-auto"
                  draggable={false}
                  loading="lazy"
                />
              </TransformComponent>
            </>
          )}
        </TransformWrapper>
      </div>

      {/* Optional bottom info bar */}
      {footerInfo && (
        <div className="px-4 py-2 bg-slate-950 border-t border-slate-800/80 text-[11px] font-mono text-slate-400 flex items-center justify-between">
          <span>{footerInfo}</span>
          <span className="text-slate-500">SCROLL TO ZOOM • DRAG TO PAN</span>
        </div>
      )}
    </div>
  );

  return (
    <>
      {renderContent(false)}

      {/* Fullscreen Overlay Modal */}
      {isFullscreen && (
        <div className="fixed inset-0 z-50 bg-black/95 flex flex-col p-4 backdrop-blur-xl animate-in fade-in duration-200">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
              <h3 className="font-mono text-sm font-bold text-white uppercase tracking-wider">
                TACTICAL ZOOM // {title || alt}
              </h3>
              {subtitle && <span className="text-xs text-slate-400">// {subtitle}</span>}
            </div>
            <button
              onClick={() => setIsFullscreen(false)}
              className="flex items-center gap-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-mono transition-colors"
            >
              <Minimize2 size={14} /> CLOSE
            </button>
          </div>
          <div className="flex-1 w-full h-[calc(100vh-80px)] mt-2">
            {renderContent(true)}
          </div>
        </div>
      )}
    </>
  );
}
