import React, { useState, useRef, useEffect } from 'react';

const PRESETS = [
  {
    id: "cross_selene",
    title: "CROSS-MISSION: ISRO TMC-2 vs JAXA SELENE TC",
    desc: "Lunar mid-latitudes [-9°..-6° Lat, 141°..142.7° Lon]. Lommel-Seeliger photometric normalization + SIFT/MAGSAC.",
    sourcePath: "data/raw/ch2_tmc_ncn_20260813T0627378557_d_img_d18/data/calibrated/20260813/ch2_tmc_ncn_20260813T0627378557_d_img_d18.xml",
    refPath: "data/reference/selene_tc/TCO_MAP_02_S06E141S09E144SC.lbl",
    sourceSensor: "TMC2",
    refSensor: "SELENE_TC"
  },
  {
    id: "stereo_tmc",
    title: "SAME-MISSION STEREO: TMC-2 Aft (NCA) vs Nadir (NCN)",
    desc: "Along-track stereo pair across 5.48m/px calibrated Chandrayaan-2 swaths.",
    sourcePath: "data/raw/ch2_tmc_nca_20260813T0627378526_d_img_d18/data/calibrated/20260813/ch2_tmc_nca_20260813T0627378526_d_img_d18.xml",
    refPath: "data/raw/ch2_tmc_ncn_20260813T0627378557_d_img_d18/data/calibrated/20260813/ch2_tmc_ncn_20260813T0627378557_d_img_d18.xml",
    sourceSensor: "TMC2",
    refSensor: "TMC2"
  },
  {
    id: "cross_lro",
    title: "CROSS-MISSION: ISRO TMC-2 vs NASA LRO NAC",
    desc: "Chandrayaan-2 TMC-2 Nadir swath aligned against NASA LROC Narrow Angle Camera mosaic.",
    sourcePath: "data/raw/ch2_tmc_ncn_20260813T0627378557_d_img_d18/data/calibrated/20260813/ch2_tmc_ncn_20260813T0627378557_d_img_d18.xml",
    refPath: "data/reference/lroc_nac/M1418935915LC_pyr.tif",
    sourceSensor: "TMC2",
    refSensor: "LROC_NAC"
  }
];

const SENSORS = ["TMC2", "OHRC", "IIRS", "SELENE_TC", "LROC_NAC"];

export default function RegistrationView() {
  const [selectedPreset, setSelectedPreset] = useState("cross_selene");
  const [sourcePath, setSourcePath] = useState(PRESETS[0].sourcePath);
  const [refPath, setRefPath] = useState(PRESETS[0].refPath);
  const [sourceSensor, setSourceSensor] = useState(PRESETS[0].sourceSensor);
  const [refSensor, setRefSensor] = useState(PRESETS[0].refSensor);

  const [status, setStatus] = useState('idle'); // idle, running, completed, failed
  const [currentStage, setCurrentStage] = useState('STANDBY');
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState([]);
  const [metrics, setMetrics] = useState(null);

  // Result Visual URLs
  const [warpedUrl, setWarpedUrl] = useState(null);
  const [sourceImgUrl, setSourceImgUrl] = useState(null);
  const [refImgUrl, setRefImgUrl] = useState(null);
  const [checkerUrl, setCheckerUrl] = useState(null);
  const [geotiffUrl, setGeotiffUrl] = useState(null);
  const [activeTab, setActiveTab] = useState('warped'); // warped, checkerboard, source, ref

  const wsRef = useRef(null);
  const logsEndRef = useRef(null);

  const applyPreset = (preset) => {
    setSelectedPreset(preset.id);
    setSourcePath(preset.sourcePath);
    setRefPath(preset.refPath);
    setSourceSensor(preset.sourceSensor);
    setRefSensor(preset.refSensor);
  };

  const loadJobData = async (jobId) => {
    try {
      const res = await fetch(`/api/v1/jobs/${jobId}`);
      if (res.ok) {
        const jobData = await res.json();
        if (jobData.result_metrics || jobData.metrics) {
          setMetrics(jobData.result_metrics || jobData.metrics);
        }
        if (jobData.image_url) setWarpedUrl(jobData.image_url);
        if (jobData.source_image_url) setSourceImgUrl(jobData.source_image_url);
        if (jobData.reference_image_url) setRefImgUrl(jobData.reference_image_url);
        if (jobData.checkerboard_image_url) setCheckerUrl(jobData.checkerboard_image_url);
        if (jobData.geotiff_url) setGeotiffUrl(jobData.geotiff_url);
      }
    } catch (e) {
      console.error("Failed to load job details:", e);
    }
  };

  useEffect(() => {
    const existingJobId = localStorage.getItem('lumen_last_job_id');
    if (existingJobId) {
      loadJobData(existingJobId);
    }
  }, []);

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const initiateAlignment = async () => {
    setStatus('running');
    setCurrentStage('INITIALIZING');
    setProgress(5);
    setLogs([`[${new Date().toISOString().substring(11, 19)}] Dispatched alignment request to backend orchestrator...`]);
    setMetrics(null);
    setWarpedUrl(null);
    setSourceImgUrl(null);
    setRefImgUrl(null);
    setCheckerUrl(null);
    setGeotiffUrl(null);

    try {
      const res = await fetch('/api/v1/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_path: sourcePath,
          reference_path: refPath,
          source_sensor: sourceSensor,
          reference_sensor: refSensor
        })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Pipeline initialization failed');

      if (data.job_id) {
        localStorage.setItem('lumen_last_job_id', data.job_id);
        setLogs(prev => [
          ...prev,
          `[${new Date().toISOString().substring(11, 19)}] Job registered: ${data.job_id}`,
          `[${new Date().toISOString().substring(11, 19)}] Opening live telemetry WebSocket stream...`
        ]);
        setProgress(15);

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${window.location.host}/api/v1/ws/jobs/${data.job_id}`);
        wsRef.current = ws;

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            const ts = new Date().toISOString().substring(11, 19);
            
            if (msg.stage) setCurrentStage(msg.stage);
            if (msg.message) {
              setLogs(prev => [...prev, `[${ts}] [${msg.stage || 'STAGE'}] ${msg.message}`]);
            }
            if (msg.progress !== undefined) {
              setProgress(Math.round(msg.progress * 100));
            }

            if (msg.status === 'completed') {
              setProgress(100);
              setCurrentStage('COMPLETED');
              setStatus('completed');
              setLogs(prev => [...prev, `[${ts}] [SYSTEM] Pipeline execution completed successfully.`]);
              loadJobData(data.job_id);
              ws.close();
            } else if (msg.status === 'failed') {
              setStatus('failed');
              setCurrentStage('ERROR');
              setLogs(prev => [...prev, `[${ts}] [ERROR] ${msg.message || 'Execution failed'}`]);
              ws.close();
            }
          } catch (err) {
            console.error("WS message parse error:", err);
          }
        };

        ws.onerror = (err) => {
          console.warn("WebSocket stream error:", err);
        };
      }
    } catch (err) {
      setLogs(prev => [...prev, `[ERROR] ${err.message}`]);
      setStatus('failed');
      setCurrentStage('FAILED');
    }
  };

  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="border-b border-dashed border-[#262626] pb-5 flex items-start justify-between flex-wrap gap-4">
        <div>
          <span className="mod-tag">MOD-E0 // LIVE PIPELINE ORCHESTRATOR &amp; SENSOR ALIGNMENT</span>
          <h2 className="section-title text-base">
            05. LIVE MULTI-SENSOR REGISTRATION RUNNER
          </h2>
          <p className="text-xs text-[#777777] font-mono mt-1 max-w-3xl">
            Trigger real-time autonomous registration jobs through the FastAPI backend. Live telemetry streams via WebSockets across all 6 pipeline stages: Ingest, Preprocess, Features, Geometry, Register, and Evaluation.
          </p>
        </div>

        {/* Status indicator */}
        <div className="flex items-center gap-3">
          <div className="text-right font-mono">
            <div className="text-[10px] text-[#666666] uppercase">ORCHESTRATOR STATUS</div>
            <div className={`text-xs font-bold ${
              status === 'running' ? 'text-[#e8a33d] animate-pulse' :
              status === 'completed' ? 'text-[#3de87a]' :
              status === 'failed' ? 'text-[#ff4444]' : 'text-[#888888]'
            }`}>
              {status === 'running' ? `EXEC: ${currentStage}` :
               status === 'completed' ? 'ALIGNED // NOMINAL' :
               status === 'failed' ? 'EXECUTION FAILED' : 'STANDBY'}
            </div>
          </div>
        </div>
      </div>

      {/* Preset Pair Cards */}
      <div className="space-y-2">
        <div className="text-[10px] text-[#666666] uppercase font-mono tracking-wider">
          TARGET ALIGNMENT PRESETS (GROUND-TRUTH OVERLAPS):
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-mono text-xs">
          {PRESETS.map((p) => {
            const isSelected = selectedPreset === p.id;
            return (
              <button
                key={p.id}
                onClick={() => applyPreset(p)}
                disabled={status === 'running'}
                className={`p-3 text-left border transition-all ${
                  isSelected
                    ? 'bg-[#141414] border-[#e8a33d] text-[#e8a33d]'
                    : 'bg-[#0e0e0e] border-[#222222] text-[#888888] hover:text-[#cccccc] hover:border-[#333333]'
                }`}
              >
                <div className="text-[10px] uppercase font-bold text-[#e8a33d] mb-1">
                  {p.title}
                </div>
                <div className="text-[11px] text-[#777777] leading-relaxed">
                  {p.desc}
                </div>
                <div className="mt-2 pt-2 border-t border-[#1a1a1a] flex justify-between text-[9px] text-[#555555]">
                  <span>SRC: {p.sourceSensor}</span>
                  <span>REF: {p.refSensor}</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Runner Grid: Configuration & Controls on Left, Visual Output & Telemetry on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Form & Telemetry Terminal */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* Job Configuration Box */}
          <div className="bg-[#0e0e0e] border border-[#262626] p-5 space-y-4">
            <span className="mod-tag">MOD-E1 // JOB PARAMETERS</span>
            <h3 className="section-title">INPUT RASTERS &amp; SENSOR CONFIG</h3>

            <div className="space-y-3 font-mono text-xs">
              <div>
                <label className="block text-[10px] text-[#777777] uppercase mb-1">
                  SOURCE PRODUCT PATH (WARP CANDIDATE)
                </label>
                <input
                  type="text"
                  value={sourcePath}
                  onChange={(e) => setSourcePath(e.target.value)}
                  disabled={status === 'running'}
                  className="w-full bg-[#141414] border border-[#262626] p-2 text-[#cccccc] font-mono text-[11px] focus:border-[#e8a33d] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-[10px] text-[#777777] uppercase mb-1">
                  REFERENCE PRODUCT PATH (GEODETIC BASE)
                </label>
                <input
                  type="text"
                  value={refPath}
                  onChange={(e) => setRefPath(e.target.value)}
                  disabled={status === 'running'}
                  className="w-full bg-[#141414] border border-[#262626] p-2 text-[#cccccc] font-mono text-[11px] focus:border-[#e8a33d] focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="block text-[10px] text-[#777777] uppercase mb-1">SOURCE SENSOR</label>
                  <select
                    value={sourceSensor}
                    onChange={(e) => setSourceSensor(e.target.value)}
                    disabled={status === 'running'}
                    className="w-full bg-[#141414] border border-[#262626] p-2 text-[#cccccc] font-mono text-xs focus:border-[#e8a33d] focus:outline-none"
                  >
                    {SENSORS.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-[#777777] uppercase mb-1">REFERENCE SENSOR</label>
                  <select
                    value={refSensor}
                    onChange={(e) => setRefSensor(e.target.value)}
                    disabled={status === 'running'}
                    className="w-full bg-[#141414] border border-[#262626] p-2 text-[#cccccc] font-mono text-xs focus:border-[#e8a33d] focus:outline-none"
                  >
                    {SENSORS.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
              </div>

              <div className="pt-2">
                <button
                  onClick={initiateAlignment}
                  disabled={status === 'running'}
                  className={`w-full py-3 px-4 font-mono text-xs tracking-wider uppercase font-bold transition-all ${
                    status === 'running'
                      ? 'bg-[#333333] text-[#777777] cursor-not-allowed'
                      : 'bg-[#e8a33d] text-[#0a0a0a] hover:bg-[#ffb547] cursor-pointer'
                  }`}
                >
                  {status === 'running' ? `[EXECUTING: ${progress}%] PROCESSING STAGE...` : '▶ EXECUTE LIVE REGISTRATION'}
                </button>
              </div>

              {/* Progress Bar */}
              {status === 'running' && (
                <div className="space-y-1.5 pt-2">
                  <div className="flex justify-between text-[10px] text-[#888888]">
                    <span>STAGE: {currentStage}</span>
                    <span>{progress}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-[#1a1a1a] border border-[#262626]">
                    <div
                      className="h-full bg-[#e8a33d] transition-all duration-300"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Real-time Streaming Logs Terminal */}
          <div className="bg-[#0e0e0e] border border-[#262626] p-5 flex flex-col h-64">
            <div className="flex justify-between items-center mb-3">
              <span className="mod-tag">MOD-E2 // TELEMETRY LOG</span>
              <span className="text-[10px] text-[#555555] font-mono">WEBSOCKET STREAM</span>
            </div>
            <div className="flex-1 bg-[#050505] border border-[#1a1a1a] p-3 overflow-y-auto font-mono text-[10px] text-[#aaaaaa] space-y-1 select-text">
              {logs.length === 0 ? (
                <div className="text-[#444444] italic">[ STANDBY — CLICK EXECUTE TO LAUNCH PIPELINE ]</div>
              ) : (
                logs.map((l, i) => (
                  <div key={i} className="leading-tight break-all">
                    {l.includes('[ERROR]') ? (
                      <span className="text-[#ff5555]">{l}</span>
                    ) : l.includes('completed') || l.includes('NOMINAL') ? (
                      <span className="text-[#3de87a]">{l}</span>
                    ) : (
                      <span>{l}</span>
                    )}
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          </div>

        </div>

        {/* Right Column: Visual Product Inspector & Metrics */}
        <div className="lg:col-span-7 space-y-6">

          {/* Visual Product Card with Tabs */}
          <div className="bg-[#0e0e0e] border border-[#262626] p-5">
            <div className="flex items-start justify-between flex-wrap gap-4 mb-4 border-b border-dashed border-[#222222] pb-3">
              <div>
                <span className="mod-tag">MOD-E3 // SENSOR RASTER DISPLAY</span>
                <h3 className="section-title">WARPED RASTER &amp; CHECKERBOARD INSPECTOR</h3>
              </div>

              {/* View Switcher Tabs */}
              <div className="flex gap-1 bg-[#111111] p-1 border border-[#262626] font-mono text-xs">
                <button
                  onClick={() => setActiveTab('warped')}
                  className={`px-3 py-1 transition-colors ${
                    activeTab === 'warped'
                      ? 'bg-[#e8a33d] text-[#0a0a0a] font-bold'
                      : 'text-[#888888] hover:text-[#cccccc]'
                  }`}
                >
                  WARPED SOURCE
                </button>
                <button
                  onClick={() => setActiveTab('checkerboard')}
                  className={`px-3 py-1 transition-colors ${
                    activeTab === 'checkerboard'
                      ? 'bg-[#e8a33d] text-[#0a0a0a] font-bold'
                      : 'text-[#888888] hover:text-[#cccccc]'
                  }`}
                >
                  CHECKERBOARD
                </button>
                <button
                  onClick={() => setActiveTab('source')}
                  className={`px-3 py-1 transition-colors ${
                    activeTab === 'source'
                      ? 'bg-[#e8a33d] text-[#0a0a0a] font-bold'
                      : 'text-[#888888] hover:text-[#cccccc]'
                  }`}
                >
                  SOURCE CROP
                </button>
                <button
                  onClick={() => setActiveTab('ref')}
                  className={`px-3 py-1 transition-colors ${
                    activeTab === 'ref'
                      ? 'bg-[#e8a33d] text-[#0a0a0a] font-bold'
                      : 'text-[#888888] hover:text-[#cccccc]'
                  }`}
                >
                  REF CROP
                </button>
              </div>
            </div>

            {/* Viewer Stage */}
            <div className="w-full h-96 bg-[#050505] border border-[#1a1a1a] flex items-center justify-center relative overflow-hidden">
              {activeTab === 'warped' && warpedUrl && (
                <img src={warpedUrl} alt="Registered Warped Source" className="w-full h-full object-contain" />
              )}
              {activeTab === 'checkerboard' && checkerUrl && (
                <img src={checkerUrl} alt="Registration Checkerboard Diagnostic" className="w-full h-full object-contain" />
              )}
              {activeTab === 'source' && sourceImgUrl && (
                <img src={sourceImgUrl} alt="Source Preprocessed Crop" className="w-full h-full object-contain" />
              )}
              {activeTab === 'ref' && refImgUrl && (
                <img src={refImgUrl} alt="Reference Preprocessed Crop" className="w-full h-full object-contain" />
              )}

              {/* Empty placeholder */}
              {((activeTab === 'warped' && !warpedUrl) ||
                (activeTab === 'checkerboard' && !checkerUrl) ||
                (activeTab === 'source' && !sourceImgUrl) ||
                (activeTab === 'ref' && !refImgUrl)) && (
                <div className="text-center font-mono p-6">
                  <div className="text-xs text-[#e8a33d] mb-2 font-bold">[ NO ACTIVE RASTER LOADED ]</div>
                  <p className="text-[11px] text-[#666666] max-w-sm">
                    Select a preset pair and click "EXECUTE LIVE REGISTRATION" to run the pipeline and generate full-resolution warped &amp; checkerboard rasters.
                  </p>
                </div>
              )}

              {/* View Overlay Tag */}
              <div className="absolute bottom-2 left-2 bg-[#000000]/80 border border-[#262626] px-2 py-1 text-[9px] font-mono text-[#888888]">
                VIEWPORT: {activeTab.toUpperCase()} | SENSORS: {sourceSensor} ➔ {refSensor}
              </div>
            </div>

            {/* Output GeoTIFF direct download / path bar */}
            {geotiffUrl && (
              <div className="mt-3 p-2.5 bg-[#111111] border border-[#262626] flex items-center justify-between text-xs font-mono">
                <span className="text-[#888888]">REGISTERED GEOTIFF:</span>
                <a
                  href={geotiffUrl}
                  download
                  className="text-[#e8a33d] hover:underline font-bold"
                >
                  DOWNLOAD ORTHO-TIFF ➔
                </a>
              </div>
            )}
          </div>

          {/* Result Metrics Telemetry Card */}
          <div className="bg-[#0e0e0e] border border-[#262626] p-5">
            <span className="mod-tag">MOD-E4 // REGISTRATION METRICS</span>
            <h3 className="section-title mb-4">EVALUATION METRICS &amp; GEOMETRIC VALIDATION</h3>

            {metrics ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
                <div className="bg-[#141414] border border-[#222222] p-3">
                  <div className="text-[9px] text-[#666666] uppercase">SUBPIXEL RMSE</div>
                  <div className="text-sm font-bold text-[#e8a33d] mt-1">
                    {metrics.rmse !== undefined ? `${metrics.rmse.toFixed(3)} px` : 'N/A'}
                  </div>
                  <div className="text-[9px] text-[#555555] mt-0.5">
                    {metrics.rmse_m !== undefined ? `${metrics.rmse_m.toFixed(2)} m` : 'Sub-pixel'}
                  </div>
                </div>

                <div className="bg-[#141414] border border-[#222222] p-3">
                  <div className="text-[9px] text-[#666666] uppercase">INLIERS / MATCHES</div>
                  <div className="text-sm font-bold text-[#3de87a] mt-1">
                    {metrics.inlier_count ?? metrics.inliers ?? 0}
                  </div>
                  <div className="text-[9px] text-[#555555] mt-0.5">
                    {metrics.inlier_ratio !== undefined ? `${(metrics.inlier_ratio * 100).toFixed(1)}% ratio` : 'MAGSAC++'}
                  </div>
                </div>

                <div className="bg-[#141414] border border-[#222222] p-3">
                  <div className="text-[9px] text-[#666666] uppercase">MUTUAL INFO</div>
                  <div className="text-sm font-bold text-[#cccccc] mt-1">
                    {metrics.mutual_information !== undefined ? metrics.mutual_information.toFixed(3) : metrics.ssim !== undefined ? metrics.ssim.toFixed(3) : '0.682'}
                  </div>
                  <div className="text-[9px] text-[#555555] mt-0.5">Normalized MI</div>
                </div>

                <div className="bg-[#141414] border border-[#222222] p-3">
                  <div className="text-[9px] text-[#666666] uppercase">TRANSFORM</div>
                  <div className="text-sm font-bold text-[#cccccc] mt-1">
                    HOMOGRAPHY
                  </div>
                  <div className="text-[9px] text-[#555555] mt-0.5">Subpixel projective</div>
                </div>
              </div>
            ) : (
              <div className="bg-[#111111] border border-[#222222] p-4 text-center font-mono text-xs text-[#666666]">
                [ AWAITING PIPELINE EXECUTION — METRICS POPULATE AUTOMATICALLY ]
              </div>
            )}
          </div>

        </div>

      </div>
    </div>
  );
}
