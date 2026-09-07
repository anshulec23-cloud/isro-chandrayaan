import React, { useState, useEffect } from 'react';
import { Activity, ShieldCheck, Database, HardDrive, Cpu, Compass } from 'lucide-react';

export default function TelemetryHeader({ missionData }) {
  const [timeStr, setTimeStr] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="bg-[#0b101d] border-b border-slate-800/80 px-6 py-3 shrink-0 select-none">
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-3">
        {/* Left: Mission Brand */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400 font-black tracking-tighter font-mono text-base shadow-[0_0_15px_rgba(6,182,212,0.15)]">
              LU
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-black text-white tracking-widest font-mono">
                  LUMEN
                </h1>
                <span className="text-[10px] px-2 py-0.5 rounded bg-blue-950 text-blue-300 font-mono font-bold border border-blue-800/60">
                  SIH1666 // ISRO
                </span>
                <span className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-mono font-semibold">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping inline-block" />
                  OPS NOMINAL
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-mono">
                CHANDRAYAAN-2 MULTI-SENSOR REGISTRATION PIPELINE
              </p>
            </div>
          </div>
        </div>

        {/* Right: Telemetry Chips */}
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          {/* Target */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300">
            <Compass size={13} className="text-cyan-400" />
            <span className="text-[10px] text-slate-400">TARGET:</span>
            <span className="text-slate-200 font-bold">MOON (EPSG:4326)</span>
          </div>

          {/* Memory Cap */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300">
            <HardDrive size={13} className="text-emerald-400" />
            <span className="text-[10px] text-slate-400">RAM:</span>
            <span className="text-emerald-300 font-bold">1.18 GB</span>
            <span className="text-[10px] text-slate-500">/ 16.0 GB CAP</span>
          </div>

          {/* Sub-Pixel Metric */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300">
            <ShieldCheck size={13} className="text-cyan-400" />
            <span className="text-[10px] text-slate-400">ACCURACY:</span>
            <span className="text-cyan-300 font-bold">1.932 px</span>
            <span className="text-[10px] text-slate-400">(~10.59 m)</span>
          </div>

          {/* Clock */}
          <div className="hidden xl:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-400 text-[11px]">
            <Activity size={13} className="text-slate-500" />
            <span>{timeStr || 'TELEMETRY LIVE'}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
