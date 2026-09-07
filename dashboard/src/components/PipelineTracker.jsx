import React from 'react';
import { 
  FileCode2, 
  MapPin, 
  SunMedium, 
  Sparkles, 
  SplitSquareVertical, 
  Grid3X3, 
  Scale, 
  CheckCircle2, 
  Info,
  AlertTriangle
} from 'lucide-react';

export const PIPELINE_STAGES = [
  {
    id: 1,
    tag: "STAGE 01",
    name: "PDS4 Ingestion",
    subtitle: "XML & GCP Inspector",
    status: "VALIDATED",
    icon: FileCode2,
    badgeColor: "emerald"
  },
  {
    id: 2,
    tag: "STAGE 02",
    name: "Orthorectification",
    subtitle: "Pushbroom → EPSG:4326",
    status: "VALIDATED",
    icon: MapPin,
    badgeColor: "emerald"
  },
  {
    id: 3,
    tag: "STAGE 03",
    name: "Photometric Norm",
    subtitle: "Synthetic Relief Approx",
    status: "APPROX",
    icon: SunMedium,
    badgeColor: "amber"
  },
  {
    id: 4,
    tag: "STAGE 04",
    name: "Feature Matching",
    subtitle: "Candidates vs MAGSAC++",
    status: "VALIDATED",
    icon: Sparkles,
    badgeColor: "emerald"
  },
  {
    id: 5,
    tag: "STAGE 05",
    name: "Same Place, Diff Look",
    subtitle: "TMC NCA vs NCN Shadowing",
    status: "VALIDATED",
    icon: SplitSquareVertical,
    badgeColor: "emerald"
  },
  {
    id: 6,
    tag: "STAGE 06",
    name: "Final Registration",
    subtitle: "Checkerboard & Sub-pixel RMSE",
    status: "VALIDATED",
    icon: Grid3X3,
    badgeColor: "emerald"
  },
  {
    id: 7,
    tag: "STAGE 07",
    name: "Scope & Honesty",
    subtitle: "Proven vs Architectural",
    status: "FINDING",
    icon: Scale,
    badgeColor: "cyan"
  }
];

export default function PipelineTracker({ activeStage, onSelectStage }) {
  return (
    <nav className="w-72 bg-[#090d18] border-r border-slate-800/80 flex flex-col h-full shrink-0 select-none">
      {/* Tracker Header */}
      <div className="px-5 py-4 border-b border-slate-800/80 flex items-center justify-between">
        <div>
          <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-slate-400">
            PIPELINE ORCHESTRATOR
          </span>
          <h2 className="text-xs font-mono font-extrabold text-white tracking-wider">
            7-STAGE EXECUTION FLOW
          </h2>
        </div>
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-700/50">
          7/7 READY
        </span>
      </div>

      {/* Stage Buttons */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1.5 custom-scrollbar">
        {PIPELINE_STAGES.map((stage) => {
          const isActive = activeStage === stage.id;
          const Icon = stage.icon;

          return (
            <button
              key={stage.id}
              onClick={() => onSelectStage(stage.id)}
              className={`w-full text-left p-3 rounded-xl border transition-all flex items-start gap-3 group relative ${
                isActive
                  ? 'bg-slate-800/90 border-cyan-500/60 shadow-[0_0_20px_rgba(6,182,212,0.15)] ring-1 ring-cyan-500/40'
                  : 'bg-[#0d1322]/60 border-slate-800/60 hover:bg-slate-800/50 hover:border-slate-700'
              }`}
            >
              {/* Active Indicator Bar */}
              {isActive && (
                <span className="absolute left-0 top-3 bottom-3 w-1 bg-cyan-400 rounded-r shadow-[0_0_8px_#22d3ee]" />
              )}

              {/* Stage Icon */}
              <div
                className={`mt-0.5 w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border transition-colors ${
                  isActive
                    ? 'bg-cyan-950/80 border-cyan-500/60 text-cyan-300 shadow-[0_0_10px_rgba(6,182,212,0.2)]'
                    : 'bg-slate-900 border-slate-800 text-slate-400 group-hover:text-slate-200 group-hover:border-slate-700'
                }`}
              >
                <Icon size={16} />
              </div>

              {/* Stage Text */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-1 mb-0.5">
                  <span className="text-[10px] font-mono font-bold tracking-wider text-slate-400">
                    {stage.tag}
                  </span>
                  {stage.status === 'VALIDATED' ? (
                    <span className="flex items-center gap-1 text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded bg-emerald-950/70 text-emerald-400 border border-emerald-800/50">
                      <CheckCircle2 size={9} />
                      VALIDATED
                    </span>
                  ) : stage.status === 'APPROX' ? (
                    <span className="flex items-center gap-1 text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded bg-amber-950/70 text-amber-300 border border-amber-800/50">
                      <AlertTriangle size={9} />
                      APPROX
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded bg-cyan-950/70 text-cyan-300 border border-cyan-800/50">
                      <Info size={9} />
                      HONESTY
                    </span>
                  )}
                </div>

                <div
                  className={`text-xs font-mono font-bold truncate ${
                    isActive ? 'text-white' : 'text-slate-200 group-hover:text-white'
                  }`}
                >
                  {stage.name}
                </div>

                <div className="text-[11px] text-slate-400 truncate mt-0.5 font-mono">
                  {stage.subtitle}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Footer Info */}
      <div className="p-3 border-t border-slate-800/80 bg-[#070a13] text-[11px] font-mono text-slate-500">
        <div className="flex items-center justify-between">
          <span>DATA GROUND TRUTH</span>
          <span className="text-emerald-400">DOCS/AUDIT.MD ✓</span>
        </div>
      </div>
    </nav>
  );
}
