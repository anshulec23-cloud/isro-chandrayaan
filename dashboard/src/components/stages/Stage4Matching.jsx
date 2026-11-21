import React, { useState } from 'react';
import { Filter } from 'lucide-react';
import MissionImageViewer from '../MissionImageViewer';

export default function Stage4Matching() {
  const [viewMode, setViewMode] = useState('detail'); // 'detail' or 'full'

  const isDetail = viewMode === 'detail';

  const candidatesSrc = isDetail ? '/previews/stage4_detail_candidates.png' : '/previews/stage4_matches_candidates.png';
  const inliersSrc = isDetail ? '/previews/stage4_detail_inliers.png' : '/previews/stage4_matches_inliers.png';

  return (
    <div className="space-y-6">
      {/* Stage Header */}
      <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-6">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[11px] font-mono font-bold text-cyan-400 uppercase tracking-widest px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/40">
                STAGE 04
              </span>
              <span className="text-[11px] font-mono text-slate-400">
                // MULTI-MODAL FEATURE CORRESPONDENCE & USAC_MAGSAC
              </span>
            </div>
            <h2 className="text-xl font-bold font-mono text-white tracking-wide">
              Feature Matching: Raw Candidates vs MAGSAC++ Inliers
            </h2>
            <p className="text-xs font-mono text-slate-400 mt-1 max-w-3xl">
              Lunar surface matching requires extracting robust crater rim keypoints invariant to scale, rotation, and illumination. LUMEN computes multi-scale candidates and applies OpenCV’s USAC_MAGSAC global homography estimator to eliminate outliers.
            </p>
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-2 bg-slate-900 p-1 rounded-lg border border-slate-800 font-mono text-xs">
            <button
              onClick={() => setViewMode('detail')}
              className={`px-3 py-1.5 rounded-md font-bold transition-all ${
                isDetail
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-700/60 shadow-[0_0_10px_rgba(6,182,212,0.2)]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              CRATER MATCH DETAIL
            </button>
            <button
              onClick={() => setViewMode('full')}
              className={`px-3 py-1.5 rounded-md font-bold transition-all ${
                !isDetail
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-700/60 shadow-[0_0_10px_rgba(6,182,212,0.2)]'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              FULL STRIP CORRESPONDENCE
            </button>
          </div>
        </div>

        {/* Real Match Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-5 font-mono text-xs">
          <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Raw Candidates</span>
            <span className="text-amber-400 font-bold text-base block mt-0.5">371 matches</span>
          </div>
          <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">MAGSAC++ Inliers</span>
            <span className="text-emerald-400 font-bold text-base block mt-0.5">92 verified</span>
          </div>
          <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Inlier Ratio</span>
            <span className="text-cyan-300 font-bold text-base block mt-0.5">24.8%</span>
          </div>
          <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Estimator</span>
            <span className="text-slate-200 font-bold text-xs block mt-0.5 truncate">USAC_MAGSAC</span>
          </div>
          <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Confidence</span>
            <span className="text-emerald-400 font-bold text-base block mt-0.5">99.9%</span>
          </div>
        </div>
      </div>

      {/* Side-by-Side Comparison: Candidates (Messy) vs Inliers (Clean) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Panel A: Raw Candidate Matches (Messy) */}
        <div className="space-y-2">
          <div className="flex items-center justify-between px-1 font-mono text-xs">
            <span className="text-amber-400 font-bold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-400 inline-block" />
              VIEW A: RAW CANDIDATES (371 MATCHES)
            </span>
            <span className="text-slate-500 text-[11px]">Includes Outliers & Cross-Talk</span>
          </div>
          <MissionImageViewer
            src={candidatesSrc}
            alt="Raw candidate matches"
            title="Raw Candidates // Pre-filtering"
            subtitle="SIFT + Grid Sampler"
            badge="MESSY CANDIDATES"
            height="h-[520px]"
            footerInfo="YELLOW/AMBER TIE-LINES LINK CORRESPONDING KEYPOINTS"
          />
        </div>

        {/* Panel B: Clean MAGSAC++ Inliers (Clean) */}
        <div className="space-y-2">
          <div className="flex items-center justify-between px-1 font-mono text-xs">
            <span className="text-emerald-400 font-bold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
              VIEW B: MAGSAC++ INLIERS (92 VERIFIED)
            </span>
            <span className="text-emerald-400 text-[11px]">Consistent Geometric Flow</span>
          </div>
          <MissionImageViewer
            src={inliersSrc}
            alt="MAGSAC++ inlier matches"
            title="MAGSAC++ Inliers // Robust Filtered"
            subtitle="Global Projective Homography Fit"
            badge="GEOMETRIC INLIERS"
            height="h-[520px]"
            footerInfo="NEON GREEN LINES: RIGID CORRESPONDENCES (OUTLIERS PURGED)"
          />
        </div>
      </div>

      {/* Rationale Note */}
      <div className="bg-[#080d19] border border-slate-800/80 rounded-xl p-4 font-mono text-xs text-slate-400 space-y-1">
        <span className="text-slate-200 font-bold text-xs uppercase flex items-center gap-2">
          <Filter size={14} className="text-cyan-400" />
          Why USAC_MAGSAC Outperforms Standard RANSAC
        </span>
        <p className="leading-relaxed">
          Standard RANSAC uses a hard error threshold that easily accepts false crater matches in low-contrast lunar regolith. USAC_MAGSAC applies a marginalizing sample consensus with σ-consensus, evaluating the full residual noise distribution without a rigid cutoff. This isolates genuine topography correspondences with 99.9% mathematical certainty.
        </p>
      </div>
    </div>
  );
}
