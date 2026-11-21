import { useState, useEffect } from 'react';

export default function EvaluationView() {
  const [blend, setBlend] = useState(50);
  const [viewMode, setViewMode] = useState('blend'); // blend, checkerboard
  const [jobData, setJobData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const jobId = localStorage.getItem('lumen_job_id');
    if (!jobId) {
      setError("NO COMPLETED JOB FOUND. Run alignment in Registration View first.");
      return;
    }

    setLoading(true);
    fetch(`http://${window.location.hostname}:8000/api/v1/jobs/${jobId}`)
      .then(res => {
        if (!res.ok) throw new Error("Job not found on backend");
        return res.json();
      })
      .then(data => {
        if (data.status === 'completed') {
          setJobData(data);
          setError(null);
        } else {
          setError(`Job status is '${data.status}'. Complete processing to view evaluation.`);
        }
      })
      .catch(err => {
        setError(`Failed to load evaluation metrics: ${err.message}`);
      })
      .finally(() => setLoading(false));
  }, []);

  const metrics = jobData?.metrics;
  const warpedUrl = jobData?.image_url ? `http://${window.location.hostname}:8000${jobData.image_url}` : null;
  const refUrl = jobData?.reference_image_url ? `http://${window.location.hostname}:8000${jobData.reference_image_url}` : null;
  const sourceUrl = jobData?.source_image_url ? `http://${window.location.hostname}:8000${jobData.source_image_url}` : null;
  const checkerUrl = jobData?.checkerboard_image_url ? `http://${window.location.hostname}:8000${jobData.checkerboard_image_url}` : null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6 p-6 h-full">
      {/* Visual Evaluation Panel */}
      <section className="bg-surface-container-low border border-outline p-6 relative flex flex-col">
        <div className="absolute top-2 right-2 font-telemetry-data text-[11px] text-outline">MOD-E1</div>
        <div className="flex justify-between items-center mb-6">
          <h2 className="font-telemetry-data text-[14px] tracking-widest text-primary uppercase">Visual Evaluation</h2>
          <div className="flex gap-4">
            <button 
              onClick={() => setViewMode('blend')} 
              className={`font-telemetry-data text-[11px] uppercase px-3 py-1 border ${viewMode === 'blend' ? 'border-primary text-on-primary bg-primary' : 'border-outline text-on-surface'}`}
            >
              Alpha Blend
            </button>
            <button 
              onClick={() => setViewMode('checkerboard')}
              className={`font-telemetry-data text-[11px] uppercase px-3 py-1 border ${viewMode === 'checkerboard' ? 'border-primary text-on-primary bg-primary' : 'border-outline text-on-surface'}`}
            >
              Checkerboard
            </button>
          </div>
        </div>
        
        <div className="flex-1 border border-primary relative flex flex-col min-h-[400px] bg-black overflow-y-auto">
          {error ? (
            <div className="text-center font-telemetry-data text-[12px] text-on-surface-variant p-6 max-w-md m-auto">
              <div className="text-primary mb-2">[ EVALUATION AWAITING DATA ]</div>
              <div>{error}</div>
            </div>
          ) : viewMode === 'blend' ? (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              {refUrl && (
                <img src={refUrl} alt="Reference Base" className="absolute inset-0 w-full h-full object-contain pointer-events-none" />
              )}
              {warpedUrl && (
                <img 
                  src={warpedUrl} 
                  alt="Warped Overlay" 
                  className="absolute inset-0 w-full h-full object-contain pointer-events-none" 
                  style={{ opacity: blend / 100 }} 
                />
              )}
            </div>
          ) : (
             <div className="w-full flex-1 flex justify-center pointer-events-none">
                {checkerUrl ? (
                  <img src={checkerUrl} alt="Checkerboard Visualization" className="max-w-full h-auto object-contain mx-auto" />
                ) : (
                  <div className="flex w-full h-full">
                    {refUrl && <img src={refUrl} alt="Reference" className="w-1/2 h-full object-contain border-r border-primary" />}
                    {warpedUrl && <img src={warpedUrl} alt="Warped" className="w-1/2 h-full object-contain" />}
                  </div>
                )}
             </div>
          )}
        </div>
        
        {viewMode === 'blend' && !error && (
          <div className="mt-6">
            <label className="font-telemetry-data text-[11px] text-on-surface block mb-2 flex justify-between">
              <span>ALPHA BLEND RATIO</span>
              <span className="text-primary">{blend}%</span>
            </label>
            <input 
              type="range" 
              min="0" 
              max="100" 
              value={blend} 
              onChange={(e) => setBlend(e.target.value)} 
              className="w-full accent-primary h-1 bg-outline-variant appearance-none"
            />
          </div>
        )}
      </section>

      {/* Metrics Panel */}
      <section className="bg-surface-container-low border border-outline p-6 relative flex flex-col">
        <div className="absolute top-2 right-2 font-telemetry-data text-[11px] text-outline">MOD-E2</div>
        <h2 className="font-telemetry-data text-[14px] tracking-widest mb-6 text-primary uppercase">Quantitative Metrics</h2>
        
        {metrics ? (
          <div className="space-y-6">
            <div className="border border-outline p-4">
              <div className="font-telemetry-data text-[11px] text-on-surface-variant mb-2">ROOT MEAN SQUARE ERROR (RMSE)</div>
              <div className="font-display-lg text-[48px] text-primary leading-none">
                {metrics.rmse !== undefined ? metrics.rmse.toFixed(3) : "N/A"} <span className="text-[16px]">px</span>
              </div>
            </div>
            
            <div className="border border-outline p-4">
              <div className="font-telemetry-data text-[11px] text-on-surface-variant mb-2">STRUCTURAL SIMILARITY (SSIM)</div>
              <div className="font-display-lg text-[48px] text-on-surface leading-none">
                {metrics.ssim !== undefined ? metrics.ssim.toFixed(4) : "N/A"}
              </div>
            </div>

            <div className="border border-outline p-4">
              <div className="font-telemetry-data text-[11px] text-on-surface-variant mb-2">INLIER RATIO</div>
              <div className="font-display-lg text-[48px] text-on-surface leading-none">
                {metrics.inlier_ratio !== undefined ? `${(metrics.inlier_ratio * 100).toFixed(1)}%` : "N/A"}
              </div>
              <div className="font-telemetry-data text-[11px] text-primary mt-2">
                {metrics.inlier_count ?? 0} INLIERS / {metrics.total_matches ?? 0} TOTAL
              </div>
            </div>
            
            <div className="border border-outline p-4 bg-primary/10 border-primary">
              <div className="font-telemetry-data text-[11px] text-primary mb-2">REGISTRATION STATUS</div>
              <div className="font-telemetry-data text-[16px] text-primary font-bold">
                {metrics.rmse !== undefined && metrics.rmse < 0.5 ? "FIT RESIDUAL BELOW 0.5 PX" : "REGISTRATION COMPLETE"}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center font-telemetry-data text-[11px] text-on-surface-variant p-6 border border-dashed border-outline">
            No pipeline metrics loaded.<br/>Execute a registration task in Registration View to populate.
          </div>
        )}
      </section>
    </div>
  );
}
