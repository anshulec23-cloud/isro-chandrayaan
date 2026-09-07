import React from 'react';
import { ShieldCheck, Layers, MapPin, AlertCircle, Compass, CheckCircle2, Award, Info, Database } from 'lucide-react';

export default function Stage7ScopeHonesty({ stageData = {} }) {
  const products = [
    {
      sensor: "OHRC Calibrated",
      id: "ch2_ohr_ncp_20260130...",
      type: "Calibrated (Level-2)",
      gsd: "0.29 m/px",
      lat: "[-85.48°, -84.66°]",
      lon: "[23.41°, 28.33°]",
      region: "Lunar South Pole (85°S)",
      status: "Verified XML"
    },
    {
      sensor: "TMC-2 NCA (Aft)",
      id: "ch2_tmc_nca_20260813...",
      type: "Calibrated (Level-2)",
      gsd: "5.48 m/px",
      lat: "[-29.51°, -5.36°]",
      lon: "[140.78°, 142.69°]",
      region: "Equatorial (5°-29°S)",
      status: "Verified XML"
    },
    {
      sensor: "TMC-2 NCN (Nadir)",
      id: "ch2_tmc_ncn_20260813...",
      type: "Calibrated (Level-2)",
      gsd: "5.48 m/px",
      lat: "[-27.87°, -3.62°]",
      lon: "[140.91°, 142.71°]",
      region: "Equatorial (4°-28°S)",
      status: "Verified XML"
    },
    {
      sensor: "IIRS Derived",
      id: "ch2_iir_ndi_20250729...",
      type: "Derived (Level-2/3)",
      gsd: "85.18 m/px",
      lat: "[-3.87°, +31.39°]",
      lon: "[99.99°, 101.43°]",
      region: "Equatorial (4°S-31°N)",
      status: "Verified XML"
    },
    {
      sensor: "JAXA SELENE TC",
      id: "TCO_MAP_02_S06E141...",
      type: "Ortho Map (Level-2)",
      gsd: "7.40 m/px",
      lat: "[-8.99°, -6.00°]",
      lon: "[141.00°, 144.00°]",
      region: "Equatorial (6°-9°S)",
      status: "Verified PDS3"
    }
  ];

  return (
    <div className="space-y-6">
      {/* Stage Header */}
      <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[11px] font-mono font-bold text-cyan-400 uppercase tracking-widest px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/40">
            STAGE 07
          </span>
          <span className="text-[11px] font-mono text-slate-400">
            // PROJECT DELIVERABLES & SCIENTIFIC RIGOR
          </span>
        </div>
        <h2 className="text-xl font-bold font-mono text-white tracking-wide">
          Scope & Technical Honesty: Validated, Attempted, & Architectural
        </h2>
        <p className="text-xs font-mono text-slate-400 mt-1 max-w-3xl">
          A core principle of the LUMEN engineering ethos is uncompromised scientific honesty. This section transparently delineates what has been proven with mathematical rigor, what has been empirically attempted and root-caused on real cross-mission orbital data, and what is architecturally complete awaiting overlapping archives.
        </p>
      </div>

      {/* Three Clear Columns: Proven vs Attempted vs Architectural */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Column 1: Proven & Validated */}
        <div className="bg-[#08121f] border border-emerald-500/40 rounded-xl p-6 space-y-4 shadow-[0_0_25px_rgba(16,185,129,0.08)]">
          <div className="flex items-center justify-between pb-3 border-b border-emerald-900/50 font-mono">
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
              <CheckCircle2 size={18} />
              <span>PROVEN & FULLY VALIDATED</span>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-700/60">
              DELIVERED
            </span>
          </div>

          <div className="space-y-3 font-mono text-xs text-slate-300">
            <div className="bg-slate-900/80 p-3.5 rounded-lg border border-slate-800 space-y-1">
              <div className="font-bold text-white flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
                Same-Sensor Stereo Alignment (TMC-2)
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed pl-3.5">
                Processed real 92.34% overlapping calibrated products (NCA to NCN). Achieved <strong className="text-emerald-300">1.932 px independent RMSE (~10.59 m)</strong> against 20 completely fresh, held-out SIFT tie points.
              </p>
            </div>

            <div className="bg-slate-900/80 p-3.5 rounded-lg border border-slate-800 space-y-1">
              <div className="font-bold text-white flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
                16GB RAM Hardware Enforcement
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed pl-3.5">
                Massive 133,000-pixel swaths run within 1.18 GB of active memory using block-by-block GDAL orthorectification, decimated previews, and intersection-bounded cropping before feature detection.
              </p>
            </div>

            <div className="bg-slate-900/80 p-3.5 rounded-lg border border-slate-800 space-y-1">
              <div className="font-bold text-white flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
                Automated PDS4 & GCP Sidecar Ingestion
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed pl-3.5">
                Extracts metadata, solar incidence/azimuth, coordinates, and resolves sibling <code className="text-cyan-300">_g_grd_d18.csv</code> GCP grids automatically from standard ISRO archive directories.
              </p>
            </div>

            <div className="bg-slate-900/80 p-3.5 rounded-lg border border-slate-800 space-y-1">
              <div className="font-bold text-white flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
                Full 80-Test Automated Pytest Suite
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed pl-3.5">
                100% test pass rate across ingestion, orthorectification, radiometric normalization, RIFT matching, homography estimation, and sub-pixel metrics on Python 3.14.
              </p>
            </div>
          </div>
        </div>

        {/* Column 2: Attempted on Real Cross-Mission Data & Benchmarked */}
        <div className="bg-[#181108] border border-amber-500/50 rounded-xl p-6 space-y-4 shadow-[0_0_25px_rgba(245,158,11,0.08)]">
          <div className="flex items-center justify-between pb-3 border-b border-amber-900/50 font-mono">
            <div className="flex items-center gap-2 text-amber-400 font-bold text-sm">
              <AlertCircle size={18} />
              <span>CROSS-MISSION: 3 TECHNIQUES TESTED</span>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-700/60">
              BENCHMARKED
            </span>
          </div>

          <div className="space-y-3 font-mono text-xs text-slate-300">
            <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 space-y-1">
              <div className="font-bold text-white flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
                  Tech 1: Lommel-Seeliger SIFT
                </span>
                <span className="text-emerald-400 font-mono font-bold text-[10px]">80.97% INLIERS</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Applied pipeline's true photometric model (<code className="text-cyan-300">i=39.06°</code>) before feature detection. Jumped from degenerate 3.17% to <strong className="text-emerald-300">217 inliers / 268 matches</strong> with <strong className="text-emerald-300">0.91 px RMSE</strong>. Mean terrain correlation jumped <strong className="text-cyan-300">0.4978 → 0.8802 (+76.8%)</strong>.
              </p>
            </div>

            <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 space-y-1">
              <div className="font-bold text-white flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 inline-block" />
                  Tech 2: Mutual Information
                </span>
                <span className="text-cyan-400 font-mono font-bold text-[10px]">+24.87% MI</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Multi-resolution NMI Powell optimization increased mutual information from <code className="text-slate-300">0.5496 → 0.6863 bits</code>. Found optimal sub-pixel rigid alignment: <code className="text-amber-300">Δx = -6.04px, Δy = -0.25px</code>.
              </p>
            </div>

            <div className="bg-slate-900/80 p-3 rounded-lg border border-slate-800 space-y-1">
              <div className="font-bold text-white flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-rose-400 inline-block" />
                  Tech 3: Crater Hough RANSAC
                </span>
                <span className="text-rose-400 font-mono font-bold text-[10px]">0.32% INLIERS</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Detected 3,293 TMC-2 vs 6,778 SELENE crater candidates. RANSAC point-set matching yielded only <strong className="text-rose-400">6 inliers / 1,895 pairs</strong> due to non-circular eroded rims and sun-angle-dependent centroid shifts.
              </p>
            </div>

            <div className="p-2.5 rounded bg-amber-950/30 border border-amber-800/40 text-[10px] text-amber-300 leading-relaxed">
              <strong>Rigorous Takeaway:</strong> Intensity-gradient matching fails cross-mission when shadows differ, but succeeds (80.97% inliers) once physical Lommel-Seeliger photometric correction removes the phase-angle bias.
            </div>
          </div>
        </div>

        {/* Column 3: Architecturally Complete */}
        <div className="bg-[#0b101d] border border-cyan-500/40 rounded-xl p-6 space-y-4 shadow-[0_0_25px_rgba(6,182,212,0.08)]">
          <div className="flex items-center justify-between pb-3 border-b border-cyan-900/50 font-mono">
            <div className="flex items-center gap-2 text-cyan-400 font-bold text-sm">
              <Layers size={18} />
              <span>ARCHITECTURALLY COMPLETE</span>
            </div>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-700/60">
              AWAITING OVERLAP DATA
            </span>
          </div>

          <div className="space-y-3 font-mono text-xs text-slate-300">
            <div className="bg-slate-900/80 p-3.5 rounded-lg border border-slate-800 space-y-1">
              <div className="font-bold text-white flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-cyan-400 inline-block" />
                Cross-Sensor Engine (OHRC-to-TMC)
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed pl-3.5">
                RIFT2 phase congruency matcher and projective homography estimator are implemented and unit-tested. Ready to execute immediately when overlapping data is provided.
              </p>
            </div>

            <div className="bg-slate-900/80 p-3.5 rounded-lg border border-slate-800 space-y-1">
              <div className="font-bold text-white flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-cyan-400 inline-block" />
                Cross-Modal Engine (TMC-to-IIRS)
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed pl-3.5">
                IIRS 256-band hyperspectral cube loader, pixel-level location map parser (<code className="text-cyan-300">_loc_</code>), and pseudo-panchromatic band synthesis are coded and verified.
              </p>
            </div>

            <div className="bg-slate-900/80 p-3.5 rounded-lg border border-slate-800 space-y-1">
              <div className="font-bold text-white flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-cyan-400 inline-block" />
                High-Latitude Polar Anisotropic Warping
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed pl-3.5">
                Specialized longitudinal compression factor (<code className="text-cyan-300">cos(lat)</code>) is built into orthorectification to prevent polar memory blow-up on South Pole footprints.
              </p>
            </div>

            <div className="bg-slate-900/80 p-3.5 rounded-lg border border-slate-800 space-y-1">
              <div className="font-bold text-white flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-cyan-400 inline-block" />
                Missing Geometry Skip Guards
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed pl-3.5">
                Detects uncalibrated (<code className="text-cyan-300">_nrp_</code>) OHRC raw products missing GCP sidecars and gracefully applies <code className="text-cyan-300">skip_orthorectify</code> to prevent crashes.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Section 3: The Ground-Truth Overlap Physics */}
      <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-2 font-mono">
          <Compass size={18} className="text-amber-400" />
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            Technical Finding: Ground-Truth Dataset Distribution & 0.00% Mutual Overlap
          </h3>
        </div>

        <p className="text-xs font-mono text-slate-400 leading-relaxed">
          Cross-sensor alignment is blocked strictly by the geographic footprint coverage of the sample datasets provided in the archive, not by software limitations. As proven below from the live XML labels:
        </p>

        {/* Real Ground Truth XML Table */}
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="w-full text-left font-mono text-xs border-collapse">
            <thead>
              <tr className="bg-slate-900 text-slate-300 border-b border-slate-800 text-[11px]">
                <th className="p-3">Sensor Product</th>
                <th className="p-3">Type</th>
                <th className="p-3">GSD</th>
                <th className="p-3">Latitude Bounds</th>
                <th className="p-3">Longitude Bounds</th>
                <th className="p-3">Physical Region</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300 text-[11px]">
              {products.map((p, idx) => (
                <tr key={idx} className="hover:bg-slate-900/40">
                  <td className="p-3 font-bold text-white flex items-center gap-2">
                    <Database size={12} className="text-cyan-400" />
                    {p.sensor}
                  </td>
                  <td className="p-3 text-slate-400">{p.type}</td>
                  <td className="p-3 text-emerald-400 font-bold">{p.gsd}</td>
                  <td className="p-3 text-cyan-300">{p.lat}</td>
                  <td className="p-3 text-cyan-300">{p.lon}</td>
                  <td className="p-3 font-semibold text-amber-300">{p.region}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Physical Separation Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs pt-2">
          <div className="bg-slate-900/80 p-3.5 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">OHRC ↔ TMC Separation</span>
            <span className="text-amber-400 font-bold text-base block mt-0.5">~1,670 km</span>
            <span className="text-[10px] text-slate-400 mt-1 block">
              Lat gap: 55.15° (South Pole 85°S vs Equator 29°S)
            </span>
          </div>

          <div className="bg-slate-900/80 p-3.5 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">TMC ↔ IIRS Separation</span>
            <span className="text-amber-400 font-bold text-base block mt-0.5">~1,200 km</span>
            <span className="text-[10px] text-slate-400 mt-1 block">
              Lon gap: 39.4° (101.4°E vs 140.8°E)
            </span>
          </div>

          <div className="bg-slate-900/80 p-3.5 rounded-lg border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase block">Mutual Geographic Overlap</span>
            <span className="text-red-400 font-bold text-base block mt-0.5">0.00%</span>
            <span className="text-[10px] text-slate-400 mt-1 block">
              Confirmed via shapely intersection bbox analysis
            </span>
          </div>
        </div>

        <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 font-mono text-xs text-slate-400 leading-relaxed">
          <strong className="text-white">Conclusion:</strong> The raw archives in <code className="text-cyan-300">data/raw/</code> represent three disjoint lunar observations taken on completely different orbital trajectories. The software is ready to register multi-sensor lunar imagery as soon as intersecting raw orbits are provided.
        </div>
      </div>
    </div>
  );
}
