import React, { useState } from 'react';
import { Grid3X3, CheckCircle2, ShieldCheck, Award, Eye, Layers, Maximize2 } from 'lucide-react';
import MissionImageViewer from '../MissionImageViewer';

export default function Stage6Registration({ stageData = {} }) {
  const [activeView, setActiveView] = useState('detail'); // 'detail', 'full', 'geotiff'

  const getActiveImage = () => {
    switch (activeView) {
      case 'detail':
        return {
          src: '/previews/stage6_checkerboard_crater_detail.png',
          title: 'Checkerboard Alignment // Crater Rim Detail',
          subtitle: 'Alternating 50px squares of Reference & Warped Source',
          badge: 'CRATER DETAIL CROP',
          footer: 'NOTICE CONTINUOUS CRATER BOUNDARIES ACROSS SQUARE TRANSITIONS'
        };
      case 'full':
        return {
          src: '/previews/TMC_to_TMC_checkerboard.jpg',
          title: 'Checkerboard Alignment // Full Overlap Swath',
          subtitle: 'Complete 148 x 1913 px intersection strip',
          badge: 'FULL SWATH',
          footer: 'FIT-TO-CONTAINER PREVENTS STRIP BUG • SCROLL TO ZOOM IN'
        };
      case 'geotiff':
        return {
          src: '/previews/TMC_to_TMC_registered.png',
          title: 'Final Registered GeoTIFF // Orthorectified Output',
          subtitle: 'EPSG:4326 Warped Product carrying reference CRS',
          badge: 'GEOTIFF PREVIEW',
          footer: 'PROJECTIVE WARP FROM MAGSAC++ HOMOGRAPHY'
        };
      default:
        return {};
    }
  };

  const activeImg = getActiveImage();

  return (
    <div className="space-y-6">
      {/* Stage Header */}
      <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[11px] font-mono font-bold text-emerald-400 uppercase tracking-widest px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/40">
            STAGE 06
          </span>
          <span className="text-[11px] font-mono text-slate-400">
            // HELD-OUT (CROSS-VALIDATED) ACCURACY
          </span>
        </div>
        <h2 className="text-xl font-bold font-mono text-white tracking-wide">
          Final Registration Result & Sub-Pixel Accuracy
        </h2>
        <p className="text-xs font-mono text-slate-400 mt-1 max-w-3xl">
          The calculated projective homography matrix warps the source image onto the reference coordinate frame. Alignment is visually verified using a checkerboard pattern and mathematically confirmed against completely independent ground checkpoints.
        </p>

        {/* Dual RMSE Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-5">
          {/* Card 1: Independent SIFT Checkpoints RMSE */}
          <div className="p-5 rounded-xl bg-gradient-to-br from-emerald-950/40 via-slate-900 to-slate-900 border border-emerald-500/40 shadow-[0_0_20px_rgba(16,185,129,0.1)]">
            <div className="flex items-center justify-between font-mono text-xs mb-3">
              <span className="text-emerald-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck size={16} />
                INDEPENDENT VALIDATION RMSE
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-700/60">
                UNBIASED GROUND TRUTH
              </span>
            </div>
            <div className="flex items-baseline gap-4 font-mono">
              <div className="text-4xl lg:text-5xl font-black text-emerald-400 tracking-tight">
                1.96 <span className="text-xl text-emerald-500/80 font-normal">px</span>
              </div>
              <div className="text-2xl lg:text-3xl font-bold text-slate-300">
                ~10.2 <span className="text-lg text-slate-400 font-normal">m</span>
              </div>
            </div>
            <p className="text-[11px] font-mono text-slate-400 mt-3 leading-relaxed border-t border-slate-800 pt-2">
              5-fold cross-validation: the homography is fitted on 80% of the 92 inlier tie-points and tested on the 20% it never saw. Native-resolution 12 x 12 km window at 5.2 m/px. Not sub-pixel: aft/nadir stereo parallax limits a single homography.
            </p>
          </div>

          {/* Card 2: Matcher Reprojection RMSE */}
          <div className="p-5 rounded-xl bg-slate-900/90 border border-slate-800">
            <div className="flex items-center justify-between font-mono text-xs mb-3">
              <span className="text-cyan-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                <Grid3X3 size={16} />
                MATCHER-BASED RMSE
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-300 border border-cyan-800/60">
                INLIER REPROJECTION
              </span>
            </div>
            <div className="flex items-baseline gap-4 font-mono">
              <div className="text-4xl lg:text-5xl font-black text-cyan-400 tracking-tight">
                1.85 <span className="text-xl text-cyan-500/80 font-normal">px</span>
              </div>
              <div className="text-2xl lg:text-3xl font-bold text-slate-300">
                ~9.6 <span className="text-lg text-slate-400 font-normal">m</span>
              </div>
            </div>
            <p className="text-[11px] font-mono text-slate-400 mt-3 leading-relaxed border-t border-slate-800 pt-2">
              Residual reprojection error of the inliers that were used to fit the homography. Optimistic by construction.
            </p>
          </div>
        </div>

        {/* Explanatory Callout: Matcher vs Independent */}
        <div className="mt-4 p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300 flex items-start gap-2.5">
          <span className="text-cyan-400 font-bold shrink-0">KEY FINDING:</span>
          <span>
            The fit residual (1.85 px) is measured on the points used to fit the transformation. The held-out RMSE (1.96 px, ~10 m) is measured on points the fit never saw, so it is the number to quote. Source: docs/results/benchmark.json (scripts/benchmark.py).
          </span>
        </div>
      </div>

      {/* Main Interactive Checkerboard Viewer */}
      <div className="space-y-3">
        {/* View Switcher Buttons */}
        <div className="flex items-center justify-between flex-wrap gap-2 font-mono text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-bold uppercase text-[11px]">SELECT VISUALIZATION:</span>
            <div className="flex gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800">
              <button
                onClick={() => setActiveView('detail')}
                className={`px-3 py-1.5 rounded-md font-bold transition-all ${
                  activeView === 'detail'
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-700/60 shadow-[0_0_10px_rgba(16,185,129,0.2)]'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                CRATER DETAIL (RECOMMENDED)
              </button>
              <button
                onClick={() => setActiveView('full')}
                className={`px-3 py-1.5 rounded-md font-bold transition-all ${
                  activeView === 'full'
                    ? 'bg-cyan-950 text-cyan-300 border border-cyan-700/60 shadow-[0_0_10px_rgba(6,182,212,0.2)]'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                FULL SWATH CHECKERBOARD
              </button>
              <button
                onClick={() => setActiveView('geotiff')}
                className={`px-3 py-1.5 rounded-md font-bold transition-all ${
                  activeView === 'geotiff'
                    ? 'bg-cyan-950 text-cyan-300 border border-cyan-700/60 shadow-[0_0_10px_rgba(6,182,212,0.2)]'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                REGISTERED GEOTIFF
              </button>
            </div>
          </div>

          <div className="flex items-center gap-3 text-slate-400 text-[11px]">
            <span>SSIM: <strong className="text-white">0.535</strong></span>
            <span>INLIERS: <strong className="text-emerald-400">92 / 371 (24.8%)</strong></span>
            <span>GRID: <strong className="text-cyan-400">5.2 m/px</strong></span>
          </div>
        </div>

        {/* Viewer with zoom/pan */}
        <MissionImageViewer
          src={activeImg.src}
          alt={activeImg.title}
          title={activeImg.title}
          subtitle={activeImg.subtitle}
          badge={activeImg.badge}
          height="h-[540px]"
          initialScale={1}
          footerInfo={activeImg.footer}
        />
      </div>
    </div>
  );
}
