import React, { useState } from 'react';
import Stage1Ingestion from '../components/stages/Stage1Ingestion';
import Stage2Orthorectification from '../components/stages/Stage2Orthorectification';
import Stage3Photometric from '../components/stages/Stage3Photometric';
import Stage4Matching from '../components/stages/Stage4Matching';
import Stage5SamePlaceDifferentLook from '../components/stages/Stage5SamePlaceDifferentLook';
import Stage6Registration from '../components/stages/Stage6Registration';
import Stage7ScopeHonesty from '../components/stages/Stage7ScopeHonesty';

const STAGE_CONFIG = [
  { id: 1, mod: "MOD-B1", tag: "01. INGESTION", label: "PDS4 Ingestion", status: "VALIDATED" },
  { id: 2, mod: "MOD-B2", tag: "02. ORTHO", label: "Orthorectification", status: "VALIDATED" },
  { id: 3, mod: "MOD-B3", tag: "03. PHOTOMETRIC", label: "Photometric Norm", status: "APPROX" },
  { id: 4, mod: "MOD-B4", tag: "04. MATCHING", label: "Feature Matching", status: "VALIDATED" },
  { id: 5, mod: "MOD-B5", tag: "05. DIFF LOOK", label: "Same Place, Diff Look", status: "VALIDATED" },
  { id: 6, mod: "MOD-B6", tag: "06. REGISTRATION", label: "Final Registration", status: "VALIDATED" },
  { id: 7, mod: "MOD-B7", tag: "07. HONESTY", label: "Scope & Honesty", status: "FINDING" },
];

export default function PipelinePage({ data = {} }) {
  const [activeStageId, setActiveStageId] = useState(1);
  const stages = data.stages || {};
  const currentStageCfg = STAGE_CONFIG.find(s => s.id === activeStageId) || STAGE_CONFIG[0];

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Top Header & 7-Stage Navigation Tracker */}
      <div className="border-b border-dashed border-[#262626] pb-5">
        <div className="flex items-start justify-between flex-wrap gap-4 mb-4">
          <div>
            <span className="mod-tag">MOD-B0 // AUTOMATED MULTI-SENSOR REGISTRATION PIPELINE</span>
            <h2 className="section-title text-base">
              02. PIPELINE EXECUTION FLOW (7 STAGES)
            </h2>
            <p className="text-xs text-[#777777] font-mono mt-1">
              Select any stage below to inspect verified telemetry, intermediate products, and validation proofs.
            </p>
          </div>

          <div className="text-right font-mono text-xs text-[#888888]">
            ACTIVE: <span className="text-[#e8a33d] font-bold">{currentStageCfg.mod} // {currentStageCfg.label}</span>
          </div>
        </div>

        {/* 7-Stage Selector Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 font-mono text-xs">
          {STAGE_CONFIG.map((s) => {
            const isActive = activeStageId === s.id;
            return (
              <button
                key={s.id}
                onClick={() => setActiveStageId(s.id)}
                className={`p-2.5 text-left border transition-colors relative ${
                  isActive
                    ? 'bg-[#141414] border-[#e8a33d] text-[#e8a33d]'
                    : 'bg-[#0a0a0a] border-[#222222] text-[#777777] hover:text-[#cccccc] hover:border-[#333333]'
                }`}
              >
                <div className="text-[9px] text-[#555555] uppercase tracking-wider">
                  {s.mod}
                </div>
                <div className="font-bold text-[11px] truncate mt-0.5">
                  {s.tag}
                </div>
                <div className="mt-1 flex items-center justify-between">
                  <span
                    className={`text-[8px] font-bold px-1 py-0.2 border ${
                      s.status === 'VALIDATED'
                        ? 'border-emerald-800 text-emerald-400 bg-emerald-950/40'
                        : s.status === 'APPROX'
                        ? 'border-amber-800 text-amber-300 bg-amber-950/40'
                        : 'border-cyan-800 text-cyan-300 bg-cyan-950/40'
                    }`}
                  >
                    {s.status}
                  </span>
                </div>
                {isActive && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#e8a33d]" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Dynamic Stage View Component */}
      <div className="bg-[#0a0a0a]">
        {activeStageId === 1 && (
          <Stage1Ingestion
            products={data.products || []}
            stageData={stages.stage1 || {}}
          />
        )}
        {activeStageId === 2 && (
          <Stage2Orthorectification
            stageData={stages.stage2 || {}}
          />
        )}
        {activeStageId === 3 && (
          <Stage3Photometric
            stageData={stages.stage3 || {}}
          />
        )}
        {activeStageId === 4 && (
          <Stage4Matching
            stageData={stages.stage4 || {}}
          />
        )}
        {activeStageId === 5 && (
          <Stage5SamePlaceDifferentLook
            stageData={stages.stage5 || {}}
          />
        )}
        {activeStageId === 6 && (
          <Stage6Registration
            stageData={stages.stage6 || {}}
          />
        )}
        {activeStageId === 7 && (
          <Stage7ScopeHonesty
            stageData={stages.stage7 || {}}
          />
        )}
      </div>
    </div>
  );
}
