import { useState } from 'react';

export default function EvaluationView() {
  const [blend, setBlend] = useState(50);
  const [viewMode, setViewMode] = useState('blend'); // blend, checkerboard

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6 p-6 h-full">
      {/* Visual Evaluation Panel */}
      <section className="bg-surface-container-low border border-outline p-6 relative flex flex-col">
        <div className="absolute top-2 right-2 font-telemetry-data text-[11px] text-outline">MOD-E1</div>
        <div className="flex justify-between items-center mb-6">
          <h2 className="font-telemetry-data text-[14px] tracking-widest text-primary uppercase">Visual Evaluation</h2>
          <div className="flex gap-4">
            <button 
              onClick={() => setViewMode('blend')} 
              className={`font-telemetry-data text-[11px] uppercase px-3 py-1 border ${viewMode === 'blend' ? 'border-primary text-on-primary bg-primary' : 'border-outline text-on-surface'}`}
            >
              Alpha Blend
            </button>
            <button 
              onClick={() => setViewMode('checkerboard')}
              className={`font-telemetry-data text-[11px] uppercase px-3 py-1 border ${viewMode === 'checkerboard' ? 'border-primary text-on-primary bg-primary' : 'border-outline text-on-surface'}`}
            >
              Checkerboard
            </button>
          </div>
        </div>
        
        <div className="flex-1 border border-primary relative flex items-center justify-center min-h-[400px] bg-black overflow-hidden">
          {viewMode === 'blend' ? (
            <>
              <img src="/moon_surface.jpg" className="absolute inset-0 w-full h-full object-cover object-center mix-blend-normal pointer-events-none" />
              <img src="/moon_crater.jpg" className="absolute inset-0 w-full h-full object-cover object-center mix-blend-screen pointer-events-none" style={{ opacity: blend / 100 }} />
            </>
          ) : (
             <div className="absolute inset-0 flex pointer-events-none">
                <img src="/moon_surface.jpg" className="w-1/2 h-full object-cover object-center" />
                <img src="/moon_crater.jpg" className="w-1/2 h-full object-cover object-center" />
             </div>
          )}
          <div className="absolute inset-0 pointer-events-none border-t border-b border-primary/30 z-10" style={{background: 'repeating-linear-gradient(0deg, transparent, transparent 40px, rgba(255,193,116,0.05) 40px, rgba(255,193,116,0.05) 41px)'}}></div>
        </div>
        
        {viewMode === 'blend' && (
          <div className="mt-6">
            <label className="font-telemetry-data text-[11px] text-on-surface block mb-2 flex justify-between">
              <span>ALPHA BLEND RATIO</span>
              <span className="text-primary">{blend}%</span>
            </label>
            <input 
              type="range" 
              min="0" 
              max="100" 
              value={blend} 
              onChange={(e) => setBlend(e.target.value)} 
              className="w-full accent-primary h-1 bg-outline-variant appearance-none"
            />
          </div>
        )}
      </section>

      {/* Metrics Panel */}
      <section className="bg-surface-container-low border border-outline p-6 relative flex flex-col">
        <div className="absolute top-2 right-2 font-telemetry-data text-[11px] text-outline">MOD-E2</div>
        <h2 className="font-telemetry-data text-[14px] tracking-widest mb-6 text-primary uppercase">Quantitative Metrics</h2>
        
        <div className="space-y-6">
          <div className="border border-outline p-4">
            <div className="font-telemetry-data text-[11px] text-on-surface-variant mb-2">ROOT MEAN SQUARE ERROR (RMSE)</div>
            <div className="font-display-lg text-[48px] text-primary leading-none">0.82 <span className="text-[16px]">px</span></div>
          </div>
          
          <div className="border border-outline p-4">
            <div className="font-telemetry-data text-[11px] text-on-surface-variant mb-2">STRUCTURAL SIMILARITY (SSIM)</div>
            <div className="font-display-lg text-[48px] text-on-surface leading-none">0.94</div>
          </div>

          <div className="border border-outline p-4">
            <div className="font-telemetry-data text-[11px] text-on-surface-variant mb-2">INLIER RATIO</div>
            <div className="font-display-lg text-[48px] text-on-surface leading-none">84.2%</div>
            <div className="font-telemetry-data text-[11px] text-primary mt-2">450 INLIERS / 534 TOTAL</div>
          </div>
          
          <div className="border border-outline p-4 bg-primary/10 border-primary">
            <div className="font-telemetry-data text-[11px] text-primary mb-2">REGISTRATION STATUS</div>
            <div className="font-telemetry-data text-[16px] text-primary font-bold">SUB-PIXEL ACCURACY ACHIEVED</div>
          </div>
        </div>
      </section>
    </div>
  );
}
