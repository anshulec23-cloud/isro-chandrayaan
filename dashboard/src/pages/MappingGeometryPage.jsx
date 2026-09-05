import React, { useState } from 'react';
import GeometryViz from '../components/GeometryViz';
import MissionImageViewer from '../components/MissionImageViewer';

export default function MappingGeometryPage({ products = [] }) {
  const [selectedId, setSelectedId] = useState(products[0]?.id || 'tmc_nca');
  const activeProd = products.find(p => p.id === selectedId) || products[0] || {};

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Top Header & Product Selector */}
      <div className="border-b border-dashed border-[#262626] pb-5 flex items-start justify-between flex-wrap gap-4">
        <div>
          <span className="mod-tag">MOD-A0 // ACQUISITION GEOMETRY & SENSOR DYNAMICS</span>
          <h2 className="section-title text-base">
            01. MAPPING / GEOMETRY INSPECTOR
          </h2>
          <p className="text-xs text-[#777777] font-mono mt-1 max-w-2xl">
            Live telemetry and geodetic orbital parameters parsed directly from Chandrayaan-2 PDS4 archive XML labels.
          </p>
        </div>

        {/* Product Switcher */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] text-[#666666] uppercase font-mono">PRODUCT:</span>
          <div className="flex gap-1 bg-[#111111] p-1 border border-[#262626]">
            {products.map(p => (
              <button
                key={p.id}
                onClick={() => setSelectedId(p.id)}
                className={`px-3 py-1 text-xs font-mono transition-colors ${
                  selectedId === p.id
                    ? 'bg-[#e8a33d] text-[#0a0a0a] font-bold'
                    : 'text-[#888888] hover:text-[#cccccc]'
                }`}
              >
                {p.sensor} ({p.id.includes('nca') ? 'NCA' : p.id.includes('ncn') ? 'NCN' : p.id.includes('ohr') ? 'NCP' : 'NDI'})
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Grid: Left = MOD-A1 Table, Right = MOD-A2 3D Geometry */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: MOD-A1 Telemetry Table */}
        <div className="lg:col-span-5 bg-[#0e0e0e] border border-[#262626] p-5">
          <span className="mod-tag">MOD-A1</span>
          <h3 className="section-title mb-4">SENSOR READOUT TABLE</h3>

          <div className="space-y-0 text-xs">
            <div className="telemetry-row">
              <span className="telemetry-label">PRODUCT ID</span>
              <span className="telemetry-value text-[10px] truncate max-w-[240px] text-[#e8a33d]">
                {activeProd.product_id}
              </span>
            </div>
            <div className="telemetry-row">
              <span className="telemetry-label">SENSOR / INSTRUMENT</span>
              <span className="telemetry-value">{activeProd.sensor}</span>
            </div>
            <div className="telemetry-row">
              <span className="telemetry-label">PROCESSING LEVEL</span>
              <span className="telemetry-value">{activeProd.level}</span>
            </div>
            <div className="telemetry-row">
              <span className="telemetry-label">INCIDENCE ANGLE (i)</span>
              <span className="telemetry-value">{Number(activeProd.incidence_angle).toFixed(2)}°</span>
            </div>
            <div className="telemetry-row">
              <span className="telemetry-label">EMISSION ANGLE (e)</span>
              <span className="telemetry-value">{Number(activeProd.emission_angle || 0.0).toFixed(2)}°</span>
            </div>
            <div className="telemetry-row">
              <span className="telemetry-label">PHASE ANGLE (α)</span>
              <span className="telemetry-value">{Number(activeProd.phase_angle || activeProd.incidence_angle).toFixed(2)}°</span>
            </div>
            <div className="telemetry-row">
              <span className="telemetry-label">SOLAR ELEVATION</span>
              <span className="telemetry-value">{Number(activeProd.solar_elevation).toFixed(2)}°</span>
            </div>
            <div className="telemetry-row">
              <span className="telemetry-label">SOLAR AZIMUTH</span>
              <span className="telemetry-value">{Number(activeProd.solar_azimuth).toFixed(2)}°</span>
            </div>
            <div className="telemetry-row">
              <span className="telemetry-label">PIXEL RESOLUTION (GSD)</span>
              <span className="telemetry-value text-[#ffffff] font-extrabold">{activeProd.resolution_m} m/px</span>
            </div>
            <div className="telemetry-row">
              <span className="telemetry-label">LATITUDE BOUNDS</span>
              <span className="telemetry-value">
                [{activeProd.lat_bounds?.[0]}°, {activeProd.lat_bounds?.[1]}°]
              </span>
            </div>
            <div className="telemetry-row">
              <span className="telemetry-label">LONGITUDE BOUNDS</span>
              <span className="telemetry-value">
                [{activeProd.lon_bounds?.[0]}°, {activeProd.lon_bounds?.[1]}°]
              </span>
            </div>
            <div className="telemetry-row">
              <span className="telemetry-label">PHYSICAL REGION</span>
              <span className="telemetry-value">{activeProd.location}</span>
            </div>
            <div className="telemetry-row">
              <span className="telemetry-label">FILE SIZE</span>
              <span className="telemetry-value">{activeProd.file_size_mb ? `${activeProd.file_size_mb.toFixed(1)} MB` : 'N/A'}</span>
            </div>
            <div className="telemetry-row border-none pt-3 flex-col items-start gap-1">
              <span className="telemetry-label">SOURCE FILE PATH (LITERAL DISK)</span>
              <code className="text-[10px] text-[#888888] break-all bg-[#050505] p-2 border border-[#222222] w-full block">
                {activeProd.source_path || 'data/raw/...'}
              </code>
            </div>
          </div>
        </div>

        {/* Right Column: MOD-A2 3D Acquisition Geometry Scene */}
        <div className="lg:col-span-7 bg-[#0e0e0e] border border-[#262626] p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <div>
                <span className="mod-tag">MOD-A2</span>
                <h3 className="section-title">3D ACQUISITION GEOMETRY // WIREFRAME SENSOR MODEL</h3>
              </div>
              <span className="text-[10px] font-mono text-[#e8a33d] border border-[#e8a33d]/40 px-2 py-0.5">
                REAL DATA DRIVEN
              </span>
            </div>
            <p className="text-xs text-[#777777] font-mono mt-1 mb-3">
              Orbital altitude (~100 km), solar vector ({Number(activeProd.incidence_angle).toFixed(1)}° inc), and sensor footprint cone rendered in true geodetic relation.
            </p>
          </div>

          <GeometryViz
            incidence={activeProd.incidence_angle}
            emission={activeProd.emission_angle || 0.0}
            azimuth={activeProd.solar_azimuth}
            gsd={activeProd.resolution_m}
            sensor={activeProd.sensor}
          />
        </div>
      </div>

      {/* MOD-A3: Full-Bleed Product Swath Preview with Pan/Zoom */}
      <div className="bg-[#0e0e0e] border border-[#262626] p-5 space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <span className="mod-tag">MOD-A3</span>
            <h3 className="section-title">FULL-WIDTH PRODUCT SWATH // ZOOM & PAN VIEWER</h3>
          </div>
          <span className="text-xs font-mono text-[#777777]">
            DIMENSIONS: <span className="text-[#e8a33d]">{activeProd.raw_dims || 'N/A'}</span>
          </span>
        </div>

        <MissionImageViewer
          src={activeProd.url}
          alt={activeProd.title}
          title={`${activeProd.title} // Orthorectified North-Up Swath`}
          subtitle={`Native GSD: ${activeProd.resolution_m} m/px | Bounds: [${activeProd.lat_bounds?.[0]}°, ${activeProd.lat_bounds?.[1]}°]`}
          badge={activeProd.sensor}
          height="h-[520px]"
          footerInfo="FIT-TO-CONTAINER PREVENTS STRIP BUG • SCROLL TO ZOOM IN • DRAG TO PAN"
        />
      </div>
    </div>
  );
}
