import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

export default function PipelineView() {
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState('CONNECTING');
  const [metrics, setMetrics] = useState(null);
  const navigate = useNavigate();
  const wsRef = useRef(null);

  useEffect(() => {
    const jobId = localStorage.getItem('lumen_job_id');
    if (!jobId) {
      setLogs([{ message: "NO JOB ID FOUND. PLEASE START REGISTRATION FIRST.", type: "error" }]);
      setStatus("ERROR");
      return;
    }

    setLogs([{ message: `INITIATING PIPELINE: JOB ${jobId}`, type: "system" }]);

    // Connect to WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:8000/api/v1/ws/jobs/${jobId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("RUNNING");
      setLogs(prev => [...prev, { message: "CONNECTED TO PIPELINE EVENT STREAM", type: "system" }]);
    };

    let lastMessage = "";

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.error) {
          setLogs(prev => [...prev, { message: `ERROR: ${data.error}`, type: "error" }]);
          setStatus("FAILED");
          return;
        }

        // Only append log if message is different to avoid spamming the UI
        if (data.message && data.message !== lastMessage) {
          setLogs(prev => [...prev, { message: `[${data.stage}] ${data.message}`, type: "log" }]);
          lastMessage = data.message;
        }

        if (data.status === 'completed' || data.status === 'failed') {
          setStatus(data.status.toUpperCase());
          if (data.status === 'completed') {
            setLogs(prev => [...prev, { message: "PIPELINE COMPLETE.", type: "success" }]);
            // Fetch the final metrics
            fetch(`http://${window.location.hostname}:8000/api/v1/jobs/${jobId}`)
              .then(res => res.json())
              .then(jobData => {
                if (jobData.metrics) {
                  setMetrics(jobData.metrics);
                }
              });
          } else {
            setLogs(prev => [...prev, { message: "PIPELINE FAILED.", type: "error" }]);
          }
        }
      } catch (err) {
        console.error(err);
      }
    };

    ws.onerror = (err) => {
      setLogs(prev => [...prev, { message: "WEBSOCKET CONNECTION ERROR", type: "error" }]);
      setStatus("ERROR");
    };

    ws.onclose = () => {
      if (status === 'RUNNING') {
        setStatus('DISCONNECTED');
      }
    };

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <h2 className="font-telemetry-data text-[14px] tracking-widest text-primary uppercase">Pipeline Execution</h2>
        <div className={`font-telemetry-data text-[11px] px-3 py-1 border ${status === 'RUNNING' ? 'border-primary text-primary animate-pulse' : status === 'COMPLETED' ? 'border-[#4ade80] text-[#4ade80]' : 'border-outline text-on-surface'}`}>
          STATUS: {status}
        </div>
      </div>
      
      <section className="bg-surface-container-low border border-outline p-6 flex-1 relative flex flex-col font-telemetry-data text-[14px]">
        <div className="absolute top-2 right-2 font-telemetry-data text-[11px] text-outline">MOD-P1</div>
        
        <div className="flex-1 overflow-y-auto space-y-2">
          {logs.map((log, idx) => (
            <div key={idx} className={`border-b border-dashed border-outline-variant/50 py-1 ${log.type === 'error' ? 'text-red-400' : log.type === 'success' ? 'text-[#4ade80]' : 'text-on-surface'}`}>
              <span className="text-primary mr-4">{'>'}</span>{log.message}
            </div>
          ))}
          {status === 'RUNNING' && (
            <div className="animate-pulse text-primary mt-4">_</div>
          )}
        </div>
        
        {metrics && (
          <div className="mt-6 border-t border-dashed border-outline-variant pt-6">
            <h3 className="text-primary mb-4 text-[12px]">FINAL METRICS</h3>
            <div className="grid grid-cols-3 gap-4">
               <div>
                 <div className="text-[10px] text-on-surface-variant">SSIM</div>
                 <div className="text-[24px]">{metrics.ssim?.toFixed(4) || "N/A"}</div>
               </div>
               <div>
                 <div className="text-[10px] text-on-surface-variant">INLIER RATIO</div>
                 <div className="text-[24px]">{(metrics.inlier_ratio * 100)?.toFixed(1)}%</div>
               </div>
               <div>
                 <div className="text-[10px] text-on-surface-variant">INLIER COUNT</div>
                 <div className="text-[24px]">{metrics.inlier_count}</div>
               </div>
            </div>
            <button onClick={() => navigate('/evaluation')} className="mt-4 border border-primary text-primary px-4 py-2 text-[11px] hover:bg-primary hover:text-on-primary transition-colors">
              VIEW EVALUATION
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
