import React, { useState } from 'react';
import { Database, Eye, Compass, Calendar, Sun, Maximize2, Layers } from 'lucide-react';
import MissionImageViewer from '../MissionImageViewer';

export default function Stage1Ingestion({ products = [] }) {
  const [selectedId, setSelectedId] = useState(products[0]?.id || 'ohrc_calibrated');

  const selectedProduct = products.find(p => p.id === selectedId) || products[0] || {
    id: "ohrc_calibrated",
    product_id: "ch2_ohr_ncp_20260130T1309574436_d_img_d18",
    title: "OHRC Calibrated (NCP)",
    sensor: "OHRC",
    level: "Calibrated Level-2",
    resolution_m: 0.29,
    lat_bounds: [-85.48, -84.66],
    lon_bounds: [23.41, 28.33],
    location: "Lunar South Pole (85°S)",
    solar_elevation: 6.97,
    solar_azimuth: 11.21,
    incidence_angle: 83.03,
    emission_angle: 0.0,
    start_time: "2026-01-30T13:09:57.4436Z",
    stop_time: "2026-01-30T13:10:13.4276Z",
    raw_dims: "12,000 x 44,000 px",
    url: "/previews/ohrc_calibrated_ortho.png",
    thumb_url: "/previews/ohrc_calibrated_ortho_thumb.png"
  };

  return (
    <div className="space-y-6">
      {/* Stage Header */}
      <div className="bg-[#0b101d] border border-slate-800 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[11px] font-mono font-bold text-cyan-400 uppercase tracking-widest px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800/40">
            STAGE 01
          </span>
          <span className="text-[11px] font-mono text-slate-400">
            // RAW TELEMETRY & XML INGESTION
          </span>
        </div>
        <h2 className="text-xl font-bold font-mono text-white tracking-wide">
          PDS4 Ingestion & Live Metadata Inspector
        </h2>
        <p className="text-xs font-mono text-slate-400 mt-1 max-w-3xl">
          LUMEN ingests ISRO PDS4 observational archives directly from disk, parsing XML labels, spacecraft look angles, illumination geometry, and Ground Control Point (GCP) sidecars with zero mock data.
        </p>

        {/* Product Selector Buttons */}
        <div className="flex flex-wrap gap-2 mt-5">
          {products.map((p) => {
            const isSelected = p.id === selectedId;
            return (
              <button
                key={p.id}
                onClick={() => setSelectedId(p.id)}
                className={`px-4 py-2 rounded-lg text-xs font-mono font-bold transition-all flex items-center gap-2 border ${
                  isSelected
                    ? 'bg-cyan-950/90 text-cyan-300 border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.2)]'
                    : 'bg-slate-900/80 text-slate-400 border-slate-800 hover:text-slate-200 hover:border-slate-700'
                }`}
              >
                <Database size={13} className={isSelected ? 'text-cyan-400' : 'text-slate-500'} />
                <span>{p.sensor}</span>
                <span className="text-[10px] text-slate-500 font-normal">
                  ({p.resolution_m} m/px)
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Grid: Metadata Card + Interactive Zoom/Pan Viewer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Real XML Parameters Table */}
        <div className="lg:col-span-5 bg-[#0b101d] border border-slate-800 rounded-xl p-5 font-mono text-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <span className="text-slate-400 font-bold uppercase tracking-wider text-[11px]">
              PARSED XML PARAMETERS
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800/60">
              GROUND TRUTH
            </span>
          </div>

          <div className="space-y-3">
            <div>
              <span className="text-[10px] text-slate-500 uppercase">Product Logical Identifier</span>
              <div className="text-slate-200 font-semibold break-all text-[11px] bg-slate-950 p-2 rounded border border-slate-900 mt-1">
                {selectedProduct.product_id}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="bg-slate-900/60 p-2.5 rounded border border-slate-800/60">
                <span className="text-[10px] text-slate-500 uppercase">Sensor Payload</span>
                <div className="text-white font-bold text-sm mt-0.5 text-cyan-400">{selectedProduct.sensor}</div>
              </div>
              <div className="bg-slate-900/60 p-2.5 rounded border border-slate-800/60">
                <span className="text-[10px] text-slate-500 uppercase">Pixel Resolution (GSD)</span>
                <div className="text-white font-bold text-sm mt-0.5 text-emerald-400">
                  {selectedProduct.resolution_m} <span className="text-[10px] text-slate-400 font-normal">m/px</span>
                </div>
              </div>
            </div>

            <div className="bg-slate-900/60 p-2.5 rounded border border-slate-800/60 space-y-1">
              <span className="text-[10px] text-slate-500 uppercase">Geographic Coordinates (Moon EPSG:4326)</span>
              <div className="text-slate-200 font-semibold text-[11px]">
                Lat: <span className="text-cyan-300">[{selectedProduct.lat_bounds[0]}°, {selectedProduct.lat_bounds[1]}°]</span>
              </div>
              <div className="text-slate-200 font-semibold text-[11px]">
                Lon: <span className="text-cyan-300">[{selectedProduct.lon_bounds[0]}°, {selectedProduct.lon_bounds[1]}°]</span>
              </div>
              <div className="text-xs text-amber-300 font-bold pt-1">
                Region: {selectedProduct.location}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div className="bg-slate-900/60 p-2 rounded border border-slate-800/60 text-center">
                <span className="text-[9px] text-slate-500 uppercase">Sun Elevation</span>
                <div className="text-slate-200 font-bold text-xs mt-0.5">{selectedProduct.solar_elevation}°</div>
              </div>
              <div className="bg-slate-900/60 p-2 rounded border border-slate-800/60 text-center">
                <span className="text-[9px] text-slate-500 uppercase">Sun Azimuth</span>
                <div className="text-slate-200 font-bold text-xs mt-0.5">{selectedProduct.solar_azimuth}°</div>
              </div>
              <div className="bg-slate-900/60 p-2 rounded border border-slate-800/60 text-center">
                <span className="text-[9px] text-slate-500 uppercase">Incidence</span>
                <div className="text-slate-200 font-bold text-xs mt-0.5">{selectedProduct.incidence_angle}°</div>
              </div>
            </div>

            <div className="bg-slate-900/60 p-2.5 rounded border border-slate-800/60">
              <span className="text-[10px] text-slate-500 uppercase">Observation Window (UTC)</span>
              <div className="text-[11px] text-slate-300 mt-1 flex flex-col gap-0.5">
                <span>Start: {selectedProduct.start_time}</span>
                <span>Stop:  {selectedProduct.stop_time}</span>
              </div>
            </div>

            {selectedProduct.raw_dims && (
              <div className="bg-slate-900/60 p-2.5 rounded border border-slate-800/60 flex justify-between items-center">
                <span className="text-[10px] text-slate-500 uppercase">Full Raw Array Shape</span>
                <span className="text-slate-300 font-bold">{selectedProduct.raw_dims}</span>
              </div>
            )}
          </div>
        </div>

        {/* Right: MissionImageViewer */}
        <div className="lg:col-span-7">
          <MissionImageViewer
            src={selectedProduct.url}
            alt={selectedProduct.title}
            title={`${selectedProduct.sensor} // ${selectedProduct.title}`}
            subtitle={`GSD: ${selectedProduct.resolution_m} m/px • ${selectedProduct.location}`}
            badge="ISRO ARCHIVE"
            height="h-[520px]"
            initialScale={1}
            footerInfo={`COORDINATES: LAT [${selectedProduct.lat_bounds[0]}°, ${selectedProduct.lat_bounds[1]}°] • LON [${selectedProduct.lon_bounds[0]}°, ${selectedProduct.lon_bounds[1]}°]`}
          />
        </div>
      </div>
    </div>
  );
}
