import React from 'react';

const NAV_ITEMS = [
  { id: 1, label: "01. MAPPING/GEOMETRY" },
  { id: 2, label: "02. PIPELINE" },
  { id: 3, label: "03. EVALUATION" },
  { id: 4, label: "04. DATASETS" },
];

export default function NavigationSidebar({ activePage, onSelectPage }) {
  return (
    <aside className="w-64 bg-[#0a0a0a] border-r border-[#222222] flex flex-col h-full shrink-0 select-none p-5">
      {/* System Brand */}
      <div className="mb-8 pb-4 border-b border-dashed border-[#222222]">
        <div className="text-[10px] text-[#666666] tracking-widest uppercase">
          SYS // CHANDRAYAAN-2
        </div>
        <h1 className="text-sm font-bold text-[#e8a33d] tracking-wider mt-1">
          LUMEN OPS TERMINAL
        </h1>
        <div className="text-[10px] text-[#555555] mt-0.5">
          MISSION CONTROL v2.4
        </div>
      </div>

      {/* Main Nav Items */}
      <div className="space-y-4 flex-1">
        <div className="text-[10px] text-[#555555] uppercase tracking-widest mb-2 font-semibold">
          NAVIGATION
        </div>
        {NAV_ITEMS.map((item) => {
          const isActive = activePage === item.id;
          return (
            <div key={item.id} className="pb-1">
              <button
                onClick={() => onSelectPage(item.id)}
                className={`w-full text-left font-mono text-xs tracking-wider transition-colors pb-1.5 ${
                  isActive
                    ? 'text-[#e8a33d] font-bold border-b border-dashed border-[#e8a33d]'
                    : 'text-[#888888] hover:text-[#cccccc]'
                }`}
              >
                {item.label}
              </button>
            </div>
          );
        })}
      </div>

      {/* Terminal System Status Footer */}
      <div className="pt-4 border-t border-dashed border-[#222222] text-[10px] font-mono text-[#555555] space-y-1.5">
        <div className="flex justify-between">
          <span>OPERATIONAL:</span>
          <span className="text-[#e8a33d]">NOMINAL</span>
        </div>
        <div className="flex justify-between">
          <span>HOST:</span>
          <span>127.0.0.1:8000</span>
        </div>
        <div className="flex justify-between">
          <span>MEM CAP:</span>
          <span>16.0 GB DISCIPLINE</span>
        </div>
      </div>
    </aside>
  );
}
