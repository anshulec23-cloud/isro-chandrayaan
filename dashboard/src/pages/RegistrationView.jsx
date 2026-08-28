import { useState, useRef, useEffect } from 'react';
import { Crosshair, ZoomIn, Box } from 'lucide-react';

export default function RegistrationView() {
  const [status, setStatus] = useState('idle');
  const [logs, setLogs] = useState([]);
  const [progress, setProgress] = useState(0);
  const [metrics, setMetrics] = useState(null);
  const [imageUrl, setImageUrl] = useState(null);
  
  const [sourcePath, setSourcePath] = useState("data/raw/ch2_ohr_ncp_20260130T1309574436_d_img_d18/data/calibrated/20260130/ch2_ohr_ncp_20260130T1309574436_d_img_d18.xml");
  const [refPath, setRefPath] = useState("data/raw/ch2_tmc_ncn_20260813T0627378557_d_img_d18/data/calibrated/20260813/ch2_tmc_ncn_20260813T0627378557_d_img_d18.xml");
  const [sourceSensor, setSourceSensor] = useState("OHRC");
  const [refSensor, setRefSensor] = useState("TMC2");
  
  const wsRef = useRef(null);

  const initiateAlignment = async () => {
    setStatus('running');
    setLogs(['Requesting pipeline execution...']);
    setProgress(10);
    setMetrics(null);
    setImageUrl(null);

    try {
      const res = await fetch(`http://${window.location.hostname}:8000/api/v1/register`, {
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
      if (!res.ok) throw new Error(data.detail || 'Registration failed');
      
      if (data.job_id) {
        setLogs(prev => [...prev, `Job established: ${data.job_id.split('-')[0]}...`]);
        setProgress(20);
        
        wsRef.current = new WebSocket(`ws://${window.location.hostname}:8000/api/v1/ws/jobs/${data.job_id}`);
        wsRef.current.onmessage = (event) => {
          const statusData = JSON.parse(event.data);
          setLogs(prev => [...prev, `[${statusData.stage}] ${statusData.message || 'Processing'}`]);
          if (statusData.progress) setProgress(Math.max(20, statusData.progress * 100));
          
          if (statusData.status === 'completed') {
            setProgress(100);
            setStatus('completed');
            fetch(`http://${window.location.hostname}:8000/api/v1/jobs/${data.job_id}`)
              .then(r => r.json())
              .then(jobData => {
                if (jobData.metrics) setMetrics(jobData.metrics);
                if (jobData.image_url) setImageUrl(`http://${window.location.hostname}:8000${jobData.image_url}`);
              });
            wsRef.current.close();
          } else if (statusData.status === 'failed') {
            setLogs(prev => [...prev, `FAILED: ${statusData.message}`]);
            setStatus('failed');
            wsRef.current.close();
          }
        };
      }
    } catch (err) {
      setLogs(prev => [...prev, `ERROR: ${err.message}`]);
      setStatus('failed');
    }
  };

  useEffect(() => {
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  return (
    <div className="flex-1 flex flex-col md:flex-row p-4 gap-4 h-full relative overflow-hidden">
      {/* Left Panel */}
      <div className="tech-panel w-full md:w-1/4 flex flex-col z-10 glass-hud shrink-0 h-full">
        <span className="module-id">SRC-OBS-01</span>
        <div className="p-module-padding border-b border-outline-variant flex justify-between items-center bg-surface/50">
          <h2 className="font-headline-md text-headline-md text-primary uppercase text-[20px]">Source Obs</h2>
          <span className="telemetry-chip font-telemetry-data text-telemetry-data px-2 py-1 rounded text-[10px]">
            <div className="w-2 h-2 rounded-full bg-primary animate-pulse"></div> {sourceSensor}
          </span>
        </div>
        <div className="p-4 flex-1 overflow-y-auto">
          <div className="w-full h-48 border border-outline-variant mb-6 relative overflow-hidden">
            <div className="w-full h-full bg-cover bg-center grayscale contrast-125 opacity-80" style={{backgroundImage: "url('/moon_crater.jpg')"}}></div>
            <div className="absolute inset-0 border border-primary/30"></div>
            <div className="crosshair top-1/2 left-1/2"></div>
            <div className="absolute bottom-2 left-2 font-telemetry-data text-[10px] bg-background/80 px-1 text-primary">LAT: 12.44N LON: 45.22E</div>
          </div>
          <div className="space-y-4">
            <div className="tech-divider pb-2">
              <div className="font-label-xs text-on-surface-variant mb-1">SENSOR IDENTIFIER</div>
              <div className="font-telemetry-data text-on-surface text-[14px]">{sourceSensor}-INFRA-88</div>
            </div>
            <div className="tech-divider pb-2">
              <div className="font-label-xs text-on-surface-variant mb-1">GROUND SAMPLE DIST (GSD)</div>
              <div className="font-telemetry-data text-primary text-[14px]">80.00 m/px</div>
            </div>
          </div>
          
          <div className="mt-8">
            <div className="mb-4">
                <label className="font-label-xs text-on-surface-variant block mb-1">SOURCE XML PATH</label>
                <input type="text" value={sourcePath} onChange={e => setSourcePath(e.target.value)} className="w-full bg-surface-container text-on-surface border border-outline p-2 font-telemetry-data text-[10px]" />
            </div>
            <div className="mb-4">
                <label className="font-label-xs text-on-surface-variant block mb-1">REFERENCE XML PATH</label>
                <input type="text" value={refPath} onChange={e => setRefPath(e.target.value)} className="w-full bg-surface-container text-on-surface border border-outline p-2 font-telemetry-data text-[10px]" />
            </div>
            <div className="flex gap-2 mb-4">
                <div className="flex-1">
                    <label className="font-label-xs text-on-surface-variant block mb-1">SOURCE SENSOR</label>
                    <select value={sourceSensor} onChange={e => setSourceSensor(e.target.value)} className="w-full bg-surface-container text-on-surface border border-outline p-2 font-telemetry-data text-[12px]">
                        <option value="OHRC">OHRC</option>
                        <option value="TMC2">TMC2</option>
                        <option value="IIRS">IIRS</option>
                    </select>
                </div>
                <div className="flex-1">
                    <label className="font-label-xs text-on-surface-variant block mb-1">REF SENSOR</label>
                    <select value={refSensor} onChange={e => setRefSensor(e.target.value)} className="w-full bg-surface-container text-on-surface border border-outline p-2 font-telemetry-data text-[12px]">
                        <option value="OHRC">OHRC</option>
                        <option value="TMC2">TMC2</option>
                        <option value="IIRS">IIRS</option>
                    </select>
                </div>
            </div>
            <button onClick={initiateAlignment} disabled={status === 'running'} className="w-full btn-amber py-3 font-label-xs tracking-widest flex items-center justify-center gap-2">
                <span className="material-symbols-outlined text-[16px]">compare_arrows</span> {status === 'running' ? 'ALIGNING...' : 'INITIATE ALIGNMENT'}
            </button>
          </div>
        </div>
      </div>
      
      {/* Center Panel */}
      <div className="tech-panel tech-panel-active flex-1 h-full z-0 relative overflow-hidden flex flex-col">
        <span className="module-id">GEO-VIZ-00</span>
        <div className="absolute top-4 left-4 z-20">
          <div className="font-label-xs text-primary mb-1 bg-background/80 px-2 py-1 border border-outline-variant inline-block">ACQUISITION GEOMETRY VIEW</div>
        </div>
        
        <div className="flex-1 w-full h-full relative">
          <div className={`absolute inset-0 w-full h-full bg-cover bg-center ${imageUrl ? '' : 'grayscale opacity-30'}`} style={{backgroundImage: `url('${imageUrl || '/moon_surface.jpg'}')`}}></div>
          
          {!imageUrl && (
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-3/4 h-3/4 border-2 border-primary/20 rotate-12 flex items-center justify-center transition-all duration-1000">
              <div className="w-1/2 h-full border border-primary/50 relative bg-primary/5">
                <div className="absolute -top-6 left-0 font-telemetry-data text-[10px] text-primary">{sourceSensor} FOOTPRINT</div>
              </div>
              <div className="w-1/4 h-1/2 border border-on-surface relative -ml-12 mt-20 rotate-[-15deg] bg-surface-container-highest/40 backdrop-blur-sm">
                <div className="absolute -bottom-6 right-0 font-telemetry-data text-[10px] text-on-surface">{refSensor} FOOTPRINT</div>
                <div className="crosshair top-1/2 left-1/2 scale-50"></div>
              </div>
            </div>
          )}
          
          <svg className="absolute inset-0 w-full h-full pointer-events-none" xmlns="http://www.w3.org/2000/svg">
            <line stroke="#ffc174" strokeDasharray="2 2" strokeWidth="1" x1="80%" x2="55%" y1="10%" y2="45%"></line>
            <circle cx="80%" cy="10%" fill="#ffc174" r="4"></circle>
            <text fill="#ffc174" fontFamily="JetBrains Mono" fontSize="10px" x="82%" y="10%">SUN VECTOR</text>
          </svg>
        </div>
        
        <div className="absolute bottom-4 w-full px-8 z-20 flex justify-between items-end pointer-events-none">
          <div className="bg-background/80 p-2 border border-outline-variant pointer-events-auto">
            <div className="font-telemetry-data text-[10px] text-on-surface-variant">PITCH: +2.4°</div>
            <div className="font-telemetry-data text-[10px] text-on-surface-variant">YAW: -0.8°</div>
            <div className="font-telemetry-data text-[10px] text-on-surface-variant">ROLL: 0.0°</div>
          </div>
          <div className="flex gap-2 pointer-events-auto">
            <button className="w-8 h-8 flex items-center justify-center border border-outline-variant bg-surface hover:border-primary text-on-surface hover:text-primary transition-colors">
              <ZoomIn size={16} />
            </button>
            <button className="w-8 h-8 flex items-center justify-center border border-outline-variant bg-surface hover:border-primary text-on-surface hover:text-primary transition-colors">
              <Box size={16} />
            </button>
          </div>
        </div>
      </div>
      
      {/* Right Panel */}
      <div className="tech-panel w-full md:w-1/4 flex flex-col z-10 glass-hud shrink-0 h-full">
        <span className="module-id">REF-OBS-02</span>
        <div className="p-module-padding border-b border-outline-variant flex justify-between items-center bg-surface/50">
          <h2 className="font-headline-md text-headline-md text-on-surface uppercase text-[20px]">Reference</h2>
          <span className="telemetry-chip font-telemetry-data text-telemetry-data px-2 py-1 rounded text-[10px]">
            <div className="w-2 h-2 rounded-full bg-surface-variant"></div> {refSensor}
          </span>
        </div>
        <div className="p-4 flex-1 overflow-y-auto">
          <div className="w-full h-48 border border-outline-variant mb-6 relative overflow-hidden">
            <div className="w-full h-full bg-cover bg-center grayscale contrast-150" style={{backgroundImage: "url('/moon_surface.jpg')"}}></div>
            <div className="absolute inset-0 border border-on-surface/30"></div>
            <div className="absolute top-0 right-0 p-1 bg-background/90 border-l border-b border-outline-variant">
              <Crosshair size={16} className="text-on-surface-variant" />
            </div>
          </div>
          <div className="space-y-4">
            <div className="tech-divider pb-2">
              <div className="font-label-xs text-on-surface-variant mb-1">SENSOR IDENTIFIER</div>
              <div className="font-telemetry-data text-on-surface text-[14px]">{refSensor}-HIRES-02</div>
            </div>
            <div className="tech-divider pb-2">
              <div className="font-label-xs text-on-surface-variant mb-1">GROUND SAMPLE DIST (GSD)</div>
              <div className="font-telemetry-data text-on-surface text-[14px]">0.25 m/px</div>
            </div>
          </div>
        </div>
      </div>

      {status !== 'idle' && (
        <div className="fixed inset-0 bg-background/80 z-[100] flex flex-col items-center justify-center backdrop-blur-sm">
            <div className="tech-panel p-8 max-w-md w-full">
                <h3 className="text-primary font-headline-md mb-4">{status === 'completed' ? 'ALIGNMENT COMPLETE' : 'ALIGNMENT SEQUENCE INITIATED'}</h3>
                <div className="font-telemetry-data text-on-surface-variant mb-6 text-sm h-10 overflow-hidden break-all">
                  {logs[logs.length - 1]}
                </div>
                <div className="w-full h-2 bg-surface-variant rounded overflow-hidden">
                    <div className={`h-full transition-all duration-300 ${status === 'failed' ? 'bg-error' : 'bg-primary'}`} style={{width: `${progress}%`}}></div>
                </div>
                {metrics && (
                  <div className="mt-6 grid grid-cols-2 gap-4 animate-in fade-in zoom-in duration-500">
                      <div className="tech-divider pb-2">
                          <div className="font-label-xs text-on-surface-variant mb-1">RMSE</div>
                          <div className="font-telemetry-data text-primary text-[14px]">{metrics.rmse?.toFixed(3)}</div>
                      </div>
                      <div className="tech-divider pb-2">
                          <div className="font-label-xs text-on-surface-variant mb-1">SSIM</div>
                          <div className="font-telemetry-data text-primary text-[14px]">{metrics.ssim?.toFixed(3)}</div>
                      </div>
                      <div className="tech-divider pb-2">
                          <div className="font-label-xs text-on-surface-variant mb-1">INLIERS</div>
                          <div className="font-telemetry-data text-primary text-[14px]">{metrics.inlier_count}</div>
                      </div>
                      <div className="tech-divider pb-2">
                          <div className="font-label-xs text-on-surface-variant mb-1">STATUS</div>
                          <div className="font-telemetry-data text-green-400 text-[14px]">SUCCESS</div>
                      </div>
                  </div>
                )}
                {(status === 'completed' || status === 'failed') && (
                  <button onClick={() => setStatus('idle')} className="mt-8 w-full btn-amber py-2 font-label-xs">ACKNOWLEDGE</button>
                )}
            </div>
        </div>
      )}
    </div>
  );
}
