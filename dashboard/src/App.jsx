import React, { useState, useEffect, useRef } from 'react';
import NavigationSidebar from './components/NavigationSidebar';
import TerminalHeader from './components/TerminalHeader';
import MappingGeometryPage from './pages/MappingGeometryPage';
import PipelinePage from './pages/PipelinePage';
import EvaluationPage from './pages/EvaluationPage';
import DatasetsPage from './pages/DatasetsPage';

const DEFAULT_DATA = {
  mission: {
    name: "ISRO Chandrayaan-2 / Chandrayaan-3",
    system: "LUMEN Multi-Sensor Autonomous Registration Engine",
    status: "OPERATIONAL",
    memory_cap_gb: 16.0,
    memory_used_mb: 1180,
    validation_timestamp: "2026-09-06T00:10:00Z",
    target_body: "Moon (IAU 2000 Moon CRS / EPSG:4326)"
  },
  products: [
    {
      id: "tmc_nca",
      product_id: "ch2_tmc_nca_20260813T0627378526_d_img_d18",
      title: "TMC-2 Aft-Looking (NCA)",
      sensor: "TMC-2",
      level: "Calibrated Level-2",
      resolution_m: 5.48,
      lat_bounds: [-29.51, -5.36],
      lon_bounds: [140.78, 142.69],
      location: "Equatorial / Mid-Lat (5°-29°S)",
      solar_elevation: 50.94,
      solar_azimuth: 69.56,
      incidence_angle: 39.06,
      emission_angle: 0.0,
      phase_angle: 39.06,
      start_time: "2026-08-13T06:27:37.8526Z",
      stop_time: "2026-08-13T06:35:37.1364Z",
      raw_dims: "10,301 x 133,368 px",
      file_size_bytes: 1184880000,
      file_size_mb: 1130.0,
      source_path: "data/raw/ch2_tmc_nca_20260813T0627378526_d_img_d18/data/calibrated/20260813/ch2_tmc_nca_20260813T0627378526_d_img_d18.xml",
      url: "/previews/tmc_nca_ortho.png",
      thumb_url: "/previews/tmc_nca_ortho_thumb.png"
    },
    {
      id: "tmc_ncn",
      product_id: "ch2_tmc_ncn_20260813T0627378557_d_img_d18",
      title: "TMC-2 Nadir-Looking (NCN)",
      sensor: "TMC-2",
      level: "Calibrated Level-2",
      resolution_m: 5.48,
      lat_bounds: [-27.87, -3.62],
      lon_bounds: [140.91, 142.71],
      location: "Equatorial / Mid-Lat (4°-28°S)",
      solar_elevation: 50.94,
      solar_azimuth: 69.56,
      incidence_angle: 39.06,
      emission_angle: 0.0,
      phase_angle: 39.06,
      start_time: "2026-08-13T06:27:37.8557Z",
      stop_time: "2026-08-13T06:35:37.1331Z",
      raw_dims: "10,301 x 133,368 px",
      file_size_bytes: 1184864000,
      file_size_mb: 1130.0,
      source_path: "data/raw/ch2_tmc_ncn_20260813T0627378557_d_img_d18/data/calibrated/20260813/ch2_tmc_ncn_20260813T0627378557_d_img_d18.xml",
      url: "/previews/tmc_ncn_ortho.png",
      thumb_url: "/previews/tmc_ncn_ortho_thumb.png"
    },
    {
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
      phase_angle: 83.03,
      start_time: "2026-01-30T13:09:57.4436Z",
      stop_time: "2026-01-30T13:10:13.4276Z",
      raw_dims: "12,000 x 44,000 px",
      file_size_bytes: 957528000,
      file_size_mb: 913.2,
      source_path: "data/raw/ch2_ohr_ncp_20260130T1309574436_d_img_d18/data/calibrated/20260130/ch2_ohr_ncp_20260130T1309574436_d_img_d18.xml",
      url: "/previews/ohrc_calibrated_ortho.png",
      thumb_url: "/previews/ohrc_calibrated_ortho_thumb.png"
    },
    {
      id: "iirs",
      product_id: "ch2_iir_ndi_20250729T0936115604_d_rfl_d18_srd",
      title: "IIRS Derived Reflectance (NDI)",
      sensor: "IIRS",
      level: "Derived Reflectance Level-2/3",
      resolution_m: 85.18,
      lat_bounds: [-3.87, 31.39],
      lon_bounds: [99.99, 101.43],
      location: "Equatorial / Mid-Lat (4°S-31°N)",
      solar_elevation: 58.28,
      solar_azimuth: 110.14,
      incidence_angle: 31.72,
      emission_angle: 0.0,
      phase_angle: 31.72,
      start_time: "2025-07-29T09:36:11.5604Z",
      stop_time: "2025-07-29T09:47:44.7963Z",
      raw_dims: "256 spectral bands",
      file_size_bytes: 3345152000,
      file_size_mb: 3190.2,
      source_path: "data/raw/ch2_iir_ndi_20250729T0936115604_d_rfl_d18_srd/data/derived/20250729/ch2_iir_ndi_20250729T0936115604_d_rfl_d18_srd.xml",
      url: "/previews/iirs_ortho.png",
      thumb_url: "/previews/iirs_ortho_thumb.png"
    }
  ],
  stages: {
    stage2: {
      geo_telemetry: {
        model: "ISRO GCP Grid Polynomial Warp",
        gcp_file: "ch2_tmc_nca_20260813T0627378526_g_grd_d18.csv",
        gcp_count: 60803,
        datum: "Lunar Reference Sphere R=1737.4 km (EPSG:4326)",
        elevation_source: "None on disk (z=0.0m datum fallback)",
        elevation_note: "No SLDEM/GLD100 file bundled; topographic parallax uncorrected",
        gsd_m: 5.48,
        aspect_ratio: "13.2 : 1 pushbroom strip"
      }
    },
    stage3: {
      status: "ILLUSTRATIVE APPROXIMATION",
      solar_elevation_deg: 50.94,
      solar_azimuth_deg: 69.56,
      mean_incidence_deg: 46.92,
      flat_plate_incidence_deg: 39.06
    },
    stage4: {
      total_candidates: 108,
      inliers_count: 71,
      inlier_ratio: 0.657
    },
    stage5: {
      source_time: "2026-08-13T06:27:37.8526Z",
      ref_time: "2026-08-13T06:27:37.8557Z",
      overlap_pct: 92.34
    },
    stage6: {
      independent_rmse_px: 1.932,
      independent_rmse_m: 10.59,
      matcher_rmse_px: 1.447,
      matcher_rmse_m: 7.93
    }
  }
};

export default function App() {
  const [data, setData] = useState(DEFAULT_DATA);
  const [activePage, setActivePage] = useState(1);
  const [apiConnected, setApiConnected] = useState(false);
  const mainRef = useRef(null);

  useEffect(() => {
    fetch('/api/v1/demo-data')
      .then(res => {
        if (!res.ok) throw new Error('API unavailable');
        return res.json();
      })
      .then(json => {
        setData(json);
        setApiConnected(true);
      })
      .catch(() => {
        setApiConnected(false);
      });
  }, []);

  const handleSelectPage = (pageId) => {
    setActivePage(pageId);
    if (mainRef.current) {
      mainRef.current.scrollTop = 0;
    }
  };

  const handleSelectProductForGeometry = (productId) => {
    setActivePage(1);
    if (mainRef.current) {
      mainRef.current.scrollTop = 0;
    }
  };

  return (
    <div className="flex h-screen w-screen bg-[#0a0a0a] text-[#e5e5e5] font-mono overflow-hidden">
      {/* 4-Item Minimal Retro Navigation Sidebar */}
      <NavigationSidebar
        activePage={activePage}
        onSelectPage={handleSelectPage}
      />

      {/* Main Terminal Viewport */}
      <div className="flex-1 flex flex-col h-full overflow-hidden bg-[#0a0a0a]">
        {/* Top Telemetry Header */}
        <TerminalHeader
          memoryUsedMb={data.mission?.memory_used_mb || 1180}
          apiConnected={apiConnected}
        />

        {/* Scrollable Page Content Area */}
        <main
          ref={mainRef}
          className="flex-1 overflow-y-auto p-6 space-y-6 crt-grid"
        >
          {activePage === 1 && (
            <MappingGeometryPage products={data.products || []} />
          )}
          {activePage === 2 && (
            <PipelinePage data={data} />
          )}
          {activePage === 3 && (
            <EvaluationPage stageData={data.stages?.stage6 || {}} />
          )}
          {activePage === 4 && (
            <DatasetsPage
              rawInventory={data.raw_inventory || []}
              onSelectProductForGeometry={handleSelectProductForGeometry}
            />
          )}
        </main>
      </div>
    </div>
  );
}
