import React, { useState } from 'react';
import { Sun, AlertTriangle } from 'lucide-react';
import MissionImageViewer from '../MissionImageViewer';

export default function Stage3Photometric() {
  const [viewMode, setViewMode] = useState('detail'); // 'detail' or 'full'

  const isDetail = viewMode === 'detail';

  const rawSrc = isDetail ? '/previews/stage3_detail_raw.png' : '/previews/stage3_raw.png';
  const incSrc = isDetail ? '/previews/stage3_detail_incidence.png' : '/previews/stage3_incidence_map.png';
  const normSrc = isDetail ? '/previews/stage3_detail_corrected.png' : '/previews/stage3_lommel_seeliger.png';

  return (
    <div className="space-y-6">
      {/* Stage Header */}
      <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-6">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[11px] font-mono font-bold text-amber-400 uppercase tracking-widest px-2 py-0.5 rounded bg-amber-950/60 border border-amber-800/40">
                STAGE 03
              </span>
              <span className="text-[11px] font-mono text-amber-300/80">
                // ILLUSTRATIVE APPROXIMATION (SYNTHETIC RELIEF DEM)
              </span>
            </div>
            <h2 className="text-xl font-bold font-mono text-white tracking-wide">
              Photometric Normalization (Illustrative Approximation using Synthetic Relief)
            </h2>
            <p className="text-xs font-mono text-slate-400 mt-1 max-w-3xl">
              Illustrative demonstration of the Lommel-Seeliger scattering correction using synthetic relief. True lunar topography slope normals require an external DEM (SLDEM2015/GLD100) not present on disk; the automated pipeline applies flat-plate solar incidence (39.06°).
            </p>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-2 bg-slate-900 p-1 rounded-lg border border-slate-800 font-mono text-xs">
            <button
              onClick={() => setViewMode('detail')}
              className={`px-3 py-1.5 rounded-md font-bold transition-all ${
                isDetail
                  ? 'bg-amber-950/80 text-amber-300 border border-amber-700/60 shadow-[0_0_10px_rgba(245,158,11,0.2)]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              CRATER DETAIL ZOOM
            </button>
            <button
              onClick={() => setViewMode('full')}
              className={`px-3 py-1.5 rounded-md font-bold transition-all ${
                !isDetail
                  ? 'bg-amber-950/80 text-amber-300 border border-amber-700/60 shadow-[0_0_10px_rgba(245,158,11,0.2)]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              FULL SWATH STRIP
            </button>
          </div>
        </div>

        {/* Real Physics Telemetry Parameters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5 font-mono text-xs">
          <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Solar Elevation</span>
            <span className="text-cyan-400 font-bold text-sm block mt-0.5">50.94°</span>
          </div>
          <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Solar Azimuth</span>
            <span className="text-slate-200 font-bold text-sm block mt-0.5">69.56°</span>
          </div>
          <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Flat-Plate Incidence</span>
            <span className="text-emerald-400 font-bold text-sm block mt-0.5">39.06°</span>
          </div>
          <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Relief Derivation</span>
            <span className="text-amber-400 font-bold text-xs block mt-0.5 truncate">Synthetic (Blur*500)</span>
          </div>
        </div>

        {/* Methodological Disclosure Banner */}
        <div className="mt-4 p-3.5 bg-amber-950/30 border border-amber-800/60 rounded-xl flex items-start gap-3 font-mono text-xs text-amber-200/90">
          <AlertTriangle size={18} className="text-amber-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold text-amber-300 uppercase tracking-wide">Methodological Disclosure — Synthetic Relief:</span>
            <p className="mt-0.5 text-slate-300 leading-relaxed">
              True per-pixel topographic slope normals require external lunar DEM rasters (SLDEM2015 / GLD100), which are not present in local storage. This 3-panel visualization demonstrates the Lommel-Seeliger scattering formulation using synthetic relief estimated via Gaussian image gradients (<code className="text-amber-300">cv2.GaussianBlur * 500</code>). The production automated pipeline executes flat-plate solar incidence (<code className="text-amber-300">39.06°</code>).
            </p>
          </div>
        </div>
      </div>

      {/* 3-Panel Progressive Normalization Pipeline */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Panel 1: Raw Image */}
        <div className="space-y-2">
          <div className="flex items-center justify-between px-1 font-mono text-xs">
            <span className="text-slate-300 font-bold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-slate-400 inline-block" />
              1. RAW INPUT IMAGE
            </span>
            <span className="text-slate-500 text-[10px]">BEFORE NORM</span>
          </div>
          <MissionImageViewer
            src={rawSrc}
            alt="Raw overlap image"
            title="Panel 1: Raw Radiance"
            subtitle={isDetail ? "Crater Region 800-1400" : "Full Overlap Swath"}
            badge="INPUT"
            height="h-[480px]"
            footerInfo="UNCOMPENSATED SHADOWS & HARSH CONTRAST"
          />
        </div>

        {/* Panel 2: Computed Incidence Angle Map */}
        <div className="space-y-2">
          <div className="flex items-center justify-between px-1 font-mono text-xs">
            <span className="text-amber-400 font-bold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-400 inline-block" />
              2. COMPUTED INCIDENCE MAP (SYNTHETIC)
            </span>
            <span className="text-amber-500/80 text-[10px]">APPROXIMATED</span>
          </div>
          <MissionImageViewer
            src={incSrc}
            alt="Computed incidence angle map"
            title="Panel 2: Local Incidence (i)"
            subtitle="Synthetic Relief Slopes (0°-90°)"
            badge="INFERNO MAP"
            height="h-[480px]"
            footerInfo="SYNTHETIC RELIEF APPROXIMATION (cv2.GaussianBlur) • NOT REAL DEM"
          />
        </div>

        {/* Panel 3: Lommel-Seeliger Corrected */}
        <div className="space-y-2">
          <div className="flex items-center justify-between px-1 font-mono text-xs">
            <span className="text-emerald-400 font-bold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
              3. LOMMEL-SEELIGER CORRECTED
            </span>
            <span className="text-emerald-500/80 text-[10px]">CLAHE EQUALIZED</span>
          </div>
          <MissionImageViewer
            src={normSrc}
            alt="Photometrically corrected image"
            title="Panel 3: Normalized Surface"
            subtitle="Invariant crater contrast"
            badge="MATCH READY"
            height="h-[480px]"
            footerInfo="SHADOWS BALANCED FOR AI FEATURE EXTRACTION"
          />
        </div>
      </div>

      {/* Mathematical Explanation */}
      <div className="bg-[#080d19] border border-slate-800/80 rounded-xl p-4 font-mono text-xs text-slate-400 space-y-1">
        <div className="text-slate-200 font-bold text-xs uppercase flex items-center gap-2">
          <Sun size={14} className="text-amber-400" />
          The Lommel-Seeliger Reflectance Formula
        </div>
        <p className="leading-relaxed">
          The pipeline models lunar regolith scattering via{' '}
          <code className="bg-slate-900 px-1.5 py-0.5 rounded text-cyan-300">
            R(i, e, α) = f(α) • [cos(i) / (cos(i) + cos(e))]
          </code>. By scaling the observed radiance by the ratio of standard target geometry to actual illumination, crater rim albedo differences are normalized across separate orbits.
        </p>
      </div>
    </div>
  );
}
