import React, { useState, useEffect } from 'react';

export default function TerminalHeader({ memoryUsedMb = 1180, apiConnected = true }) {
  const [utcTime, setUtcTime] = useState('');

  useEffect(() => {
    const update = () => {
      setUtcTime(new Date().toISOString().replace('T', ' ').substring(0, 19) + ' UTC');
    };
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="h-12 bg-[#0a0a0a] border-b border-[#222222] px-6 flex items-center justify-between font-mono text-xs text-[#888888] shrink-0 select-none">
      {/* Left: System Status & Host */}
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${apiConnected ? 'bg-[#e8a33d] shadow-[0_0_6px_#e8a33d]' : 'bg-red-500'}`} />
          <span className="text-[#cccccc] font-semibold tracking-wider">
            {apiConnected ? 'CH-2 TELEMETRY ONLINE' : 'OFFLINE // CACHE'}
          </span>
        </span>
        <span className="text-[#444444]">|</span>
        <span className="text-[#777777]">TARGET: <span className="text-[#e8a33d]">MOON [EPSG:4326]</span></span>
      </div>

      {/* Right: Key Telemetry */}
      <div className="flex items-center gap-5">
        <div>
          <span className="text-[#555555]">HELD-OUT RMSE: </span>
          <span className="text-[#e8a33d] font-bold">1.96 px</span>
          <span className="text-[#666666]"> (~10 m)</span>
        </div>
        <span className="text-[#444444]">|</span>
        <div>
          <span className="text-[#555555]">RAM: </span>
          <span className="text-[#cccccc]">{ (memoryUsedMb / 1024).toFixed(2) } GB</span>
          <span className="text-[#555555]"> / 16.0 GB</span>
        </div>
        <span className="text-[#444444]">|</span>
        <div className="text-[#e8a33d] font-mono tracking-wider font-semibold">
          {utcTime}
        </div>
      </div>
    </header>
  );
}
