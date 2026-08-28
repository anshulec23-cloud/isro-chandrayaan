import { useState, useEffect } from 'react';

export default function DatasetsView() {
  const [datasets, setDatasets] = useState([]);

  useEffect(() => {
    fetch(`http://${window.location.hostname}:8000/api/v1/datasets`)
      .then(res => res.json())
      .then(data => setDatasets(data.datasets))
      .catch(err => console.error(err));
  }, []);

  return (
    <div className="p-6 h-full flex flex-col">
      <h2 className="font-telemetry-data text-[14px] tracking-widest mb-6 text-primary uppercase">PRADAN Datasets (data/raw)</h2>
      
      <section className="bg-surface-container-low border border-outline p-6 flex-1 relative flex flex-col">
        <div className="absolute top-2 right-2 font-telemetry-data text-[11px] text-outline">MOD-D1</div>
        
        <div className="flex-1 overflow-y-auto">
          <div className="grid grid-cols-12 font-telemetry-data text-[11px] text-on-surface-variant border-b border-outline-variant pb-4 mb-4 uppercase">
            <div className="col-span-6">IDENTIFIER</div>
            <div className="col-span-2">SENSOR</div>
            <div className="col-span-2">SIZE</div>
            <div className="col-span-2 text-right">ACTION</div>
          </div>
          
          {datasets.length === 0 ? (
            <div className="text-center py-10 text-on-surface-variant font-telemetry-data text-[11px]">NO DATASETS FOUND</div>
          ) : datasets.map(ds => (
            <div key={ds.id} className="grid grid-cols-12 items-center py-3 border-b border-dashed border-outline-variant/30 hover:bg-surface-container transition-colors">
              <div className="col-span-6 font-telemetry-data text-on-surface text-[12px] truncate pr-4">
                {ds.name}
              </div>
              <div className="col-span-2 font-telemetry-data text-[11px] text-primary">
                {ds.sensor}
              </div>
              <div className="col-span-2 font-telemetry-data text-[11px] text-on-surface-variant">
                {ds.size_mb} MB
              </div>
              <div className="col-span-2 text-right">
                <button className="bg-transparent border border-outline hover:border-primary text-on-surface hover:text-primary px-3 py-1 font-telemetry-data text-[11px] transition-colors">
                  SELECT
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
