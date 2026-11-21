import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import GeometryViz from '../components/GeometryViz';

export default function MappingView() {
  const [sourcePath, setSourcePath] = useState("data/raw/ch2_ohr_ncp_20260130T1309574436_d_img_d18/data/calibrated/20260130/ch2_ohr_ncp_20260130T1309574436_d_img_d18.xml");
  const [refPath, setRefPath] = useState("data/raw/ch2_tmc_ncn_20260813T0627378557_d_img_d18/data/calibrated/20260813/ch2_tmc_ncn_20260813T0627378557_d_img_d18.xml");
  const [isStarting, setIsStarting] = useState(false);
  const [jobData, setJobData] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const jobId = localStorage.getItem('lumen_job_id');
    if (jobId) {
      fetch(`http://${window.location.hostname}:8000/api/v1/jobs/${jobId}`)
        .then(res => res.json())
        .then(data => {
          if (data.status === 'completed') {
            setJobData(data);
          }
        })
        .catch(() => {});
    }
  }, []);

  const startRegistration = async () => {
    try {
      setIsStarting(true);
      const res = await fetch(`http://${window.location.hostname}:8000/api/v1/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_path: sourcePath,
          reference_path: refPath,
          source_sensor: "OHRC",
          reference_sensor: "TMC2"
        })
      });
      const data = await res.json();
      if (data.job_id) {
        localStorage.setItem('lumen_job_id', data.job_id);
        navigate('/pipeline');
      }
    } catch (err) {
      console.error(err);
      setIsStarting(false);
    }
  };

  const srcUrl = jobData?.source_image_url ? `http://${window.location.hostname}:8000${jobData.source_image_url}` : null;
  const refUrl = jobData?.reference_image_url ? `http://${window.location.hostname}:8000${jobData.reference_image_url}` : null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.5fr_1fr] gap-6 p-6 h-full">
      {/* Source Observation Panel */}
      <section className="bg-surface-container-low border border-outline p-6 relative flex flex-col">
        <div className="absolute top-2 right-2 font-telemetry-data text-[11px] text-outline">MOD-A1</div>
        <h2 className="font-telemetry-data text-[14px] tracking-widest mb-6 text-primary uppercase">Source Observation</h2>
        
        <div className="flex-1 border border-dashed border-outline-variant relative flex items-center justify-center min-h-[200px] bg-black/50 overflow-hidden">
          {srcUrl ? (
            <img src={srcUrl} alt="Source Observation" className="w-full h-full object-cover" />
          ) : (
            <div className="text-center font-telemetry-data text-[10px] text-on-surface-variant p-4">
              [ NO SOURCE PREVIEW ]<br/>Execute pipeline to generate preview
            </div>
          )}
          <div className="w-10 h-10 border border-primary relative z-10 flex items-center justify-center pointer-events-none">
            <div className="absolute w-[1px] h-full bg-primary"></div>
            <div className="absolute h-[1px] w-full bg-primary"></div>
          </div>
        </div>
        
        <ul className="list-none mt-4">
          <DataRow label="SENSOR" value="OHRC" />
          <DataRow label="INCIDENCE" value="83.0°" />
          <DataRow label="EMISSION" value="0.0°" />
          <DataRow label="SUN AZIMUTH" value="11.2°" />
          <DataRow label="GSD" value="0.25 m/px" />
        </ul>
        
        <div className="mt-4">
          <label className="font-telemetry-data text-[11px] text-on-surface block mb-2">SOURCE PATH</label>
          <input 
            type="text" 
            value={sourcePath} 
            onChange={e => setSourcePath(e.target.value)} 
            className="w-full bg-transparent border-b border-outline text-on-surface font-telemetry-data text-[11px] py-1 outline-none focus:border-primary transition-colors" 
          />
        </div>
      </section>

      {/* 3D Geometry Panel */}
      <section className="bg-surface-container-low border border-outline p-6 relative flex flex-col">
        <div className="absolute top-2 right-2 font-telemetry-data text-[11px] text-outline">MOD-B1</div>
        <h2 className="font-telemetry-data text-[14px] tracking-widest mb-6 text-primary uppercase">Acquisition Geometry</h2>
        
        <div className="flex-1 border border-primary relative flex flex-col items-center justify-center min-h-[300px] bg-black overflow-hidden">
          <GeometryViz incidence={83.0} emission={0.0} azimuth={11.2} />
        </div>
        
        <button 
          onClick={startRegistration} 
          disabled={isStarting}
          className="bg-transparent border border-primary text-primary px-4 py-2 font-telemetry-data text-[11px] uppercase cursor-pointer mt-6 hover:bg-primary hover:text-on-primary transition-colors disabled:opacity-50"
        >
          {isStarting ? 'STARTING...' : 'START REGISTRATION PIPELINE'}
        </button>
      </section>

      {/* Reference Observation Panel */}
      <section className="bg-surface-container-low border border-outline p-6 relative flex flex-col">
        <div className="absolute top-2 right-2 font-telemetry-data text-[11px] text-outline">MOD-C1</div>
        <h2 className="font-telemetry-data text-[14px] tracking-widest mb-6 text-primary uppercase">Reference Observation</h2>
        
        <div className="flex-1 border border-dashed border-outline-variant relative flex items-center justify-center min-h-[200px] bg-black/50 overflow-hidden">
          {refUrl ? (
            <img src={refUrl} alt="Reference Observation" className="w-full h-full object-cover" />
          ) : (
            <div className="text-center font-telemetry-data text-[10px] text-on-surface-variant p-4">
              [ NO REFERENCE PREVIEW ]<br/>Execute pipeline to generate preview
            </div>
          )}
          <div className="w-10 h-10 border border-primary relative z-10 flex items-center justify-center scale-50 pointer-events-none">
            <div className="absolute w-[1px] h-full bg-primary"></div>
            <div className="absolute h-[1px] w-full bg-primary"></div>
          </div>
        </div>
        
        <ul className="list-none mt-4">
          <DataRow label="SENSOR" value="TMC-2" />
          <DataRow label="INCIDENCE" value="39.1°" />
          <DataRow label="EMISSION" value="0.0°" />
          <DataRow label="SUN AZIMUTH" value="69.6°" />
          <DataRow label="GSD" value="5.0 m/px" />
        </ul>
        
        <div className="mt-4">
          <label className="font-telemetry-data text-[11px] text-on-surface block mb-2">REFERENCE PATH</label>
          <input 
            type="text" 
            value={refPath} 
            onChange={e => setRefPath(e.target.value)} 
            className="w-full bg-transparent border-b border-outline text-on-surface font-telemetry-data text-[11px] py-1 outline-none focus:border-primary transition-colors" 
          />
        </div>
      </section>
    </div>
  );
}

function DataRow({ label, value }) {
  return (
    <li className="flex justify-between py-2 border-b border-dashed border-outline-variant font-telemetry-data text-[14px]">
      <span className="text-on-surface-variant">{label}</span>
      <span className="text-primary">{value}</span>
    </li>
  );
}
