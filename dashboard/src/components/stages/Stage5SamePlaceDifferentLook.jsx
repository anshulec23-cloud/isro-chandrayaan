import React from 'react';
import { SplitSquareVertical, Clock, Sun, Compass, Camera, AlertCircle } from 'lucide-react';
import MissionImageViewer from '../MissionImageViewer';

export default function Stage5SamePlaceDifferentLook({ stageData = {} }) {
  return (
    <div className="space-y-6">
      {/* Stage Header */}
      <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[11px] font-mono font-bold text-cyan-400 uppercase tracking-widest px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/40">
            STAGE 05
          </span>
          <span className="text-[11px] font-mono text-slate-400">
            // STEREO PERSPECTIVE & SHADOW ORIENTATION ANALYSIS
          </span>
        </div>
        <h2 className="text-xl font-bold font-mono text-white tracking-wide">
          Same Place, Different Look (TMC-2 NCA vs NCN)
        </h2>

        {/* Plain Language Framing Banner */}
        <div className="mt-4 p-4 rounded-xl bg-gradient-to-r from-blue-950/70 to-slate-900 border border-blue-800/50 flex items-start gap-3">
          <SplitSquareVertical size={20} className="text-cyan-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="text-xs font-mono font-bold text-cyan-300 uppercase tracking-wider">
              OPERATIONAL OBSERVATION
            </span>
            <p className="text-xs font-mono text-slate-200 leading-relaxed">
              &ldquo;Same location, captured at different viewing angles — notice the shadow differences on crater rims and steep terrain.&rdquo;
            </p>
          </div>
        </div>

        {/* Telemetry Comparison Table */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-5 font-mono text-xs">
          {/* Source: TMC NCA (Aft-looking) */}
          <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800 space-y-2">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <span className="font-bold text-cyan-400 text-xs">SOURCE: TMC-2 NCA</span>
              <span className="px-2 py-0.5 rounded text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-800">
                AFT-LOOKING
              </span>
            </div>
            <div className="space-y-1 text-slate-300 text-[11px]">
              <div className="flex justify-between">
                <span className="text-slate-500">Acquisition Time:</span>
                <span className="font-bold text-slate-200">2026-08-13T06:27:37.8526Z</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Sun Elevation:</span>
                <span className="text-slate-200 font-bold">50.94°</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Sun Azimuth:</span>
                <span className="text-slate-200 font-bold">69.56°</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Solar Incidence:</span>
                <span className="text-slate-200 font-bold">39.06°</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Camera Angle:</span>
                <span className="text-amber-400 font-bold">Inclined Aft Vector (-25°)</span>
              </div>
            </div>
          </div>

          {/* Reference: TMC NCN (Nadir-looking) */}
          <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800 space-y-2">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <span className="font-bold text-emerald-400 text-xs">REFERENCE: TMC-2 NCN</span>
              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800">
                NADIR-LOOKING
              </span>
            </div>
            <div className="space-y-1 text-slate-300 text-[11px]">
              <div className="flex justify-between">
                <span className="text-slate-500">Acquisition Time:</span>
                <span className="font-bold text-slate-200">2026-08-13T06:27:37.8557Z</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Sun Elevation:</span>
                <span className="text-slate-200 font-bold">50.94°</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Sun Azimuth:</span>
                <span className="text-slate-200 font-bold">69.56°</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Solar Incidence:</span>
                <span className="text-slate-200 font-bold">39.06°</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Camera Angle:</span>
                <span className="text-emerald-400 font-bold">Orthogonal Nadir (0°)</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Side-by-Side Dual Viewers */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Source Image */}
        <div className="space-y-2">
          <div className="flex items-center justify-between px-1 font-mono text-xs">
            <span className="text-cyan-400 font-bold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-cyan-400 inline-block" />
              TMC-2 NCA // AFT VIEW (INC: 39.06°)
            </span>
            <span className="text-slate-500 text-[11px]">2026-08-13 06:27:37Z</span>
          </div>
          <MissionImageViewer
            src="/previews/TMC_to_TMC_src_04_photometric_norm.png"
            alt="TMC NCA Aft"
            title="TMC NCA // Aft Perspective"
            subtitle="Normalized Overlap Crop"
            badge="SOURCE (WARPED)"
            height="h-[520px]"
            footerInfo="LOOKING AFT: CRATER RIDGES FORESHORTENED"
          />
        </div>

        {/* Reference Image */}
        <div className="space-y-2">
          <div className="flex items-center justify-between px-1 font-mono text-xs">
            <span className="text-emerald-400 font-bold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
              TMC-2 NCN // NADIR VIEW (INC: 39.06°)
            </span>
            <span className="text-slate-500 text-[11px]">2026-08-13 06:27:37Z</span>
          </div>
          <MissionImageViewer
            src="/previews/TMC_to_TMC_ref_04_photometric_norm.png"
            alt="TMC NCN Nadir"
            title="TMC NCN // Nadir Perspective"
            subtitle="Normalized Overlap Crop"
            badge="REFERENCE (BASE)"
            height="h-[520px]"
            footerInfo="LOOKING NADIR: PLAN VIEW WITHOUT OBLIQUE SLANT"
          />
        </div>
      </div>

      {/* Technical Summary */}
      <div className="bg-[#080d19] border border-slate-800/80 rounded-xl p-4 font-mono text-xs text-slate-400 flex items-start gap-3">
        <Camera size={18} className="text-cyan-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="text-slate-200 font-bold text-xs uppercase">
            Stereo Parallax vs Shadow Illumination
          </span>
          <p className="leading-relaxed">
            The two images share 92.34% geographic overlap in the equatorial moon belt. Because both cameras imaged the surface during the same orbit pass, the solar azimuth and elevation are identical, but the 25° forward-to-aft pitch difference between the cameras causes distinctive relief displacement and parallax shadowing on crater walls.
          </p>
        </div>
      </div>
    </div>
  );
}
