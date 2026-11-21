import time
from pathlib import Path
from lumen.pipeline.orchestrator import RegistrationPipeline, PipelineStage
from lumen.config import get_settings

src_xml = Path('data/raw/ch2_tmc_ncn_20260813T0627378557_d_img_d18/data/calibrated/20260813/ch2_tmc_ncn_20260813T0627378557_d_img_d18.xml')
ref_lbl = Path('data/reference/selene_tc/TCO_MAP_02_S06E141S09E144SC.lbl')

print('Source exists:', src_xml.exists())
print('Reference exists:', ref_lbl.exists())

class Callback:
    def on_stage_start(self, stage, msg):
        print(f'>>> START {stage.name}: {msg}')
    def on_stage_complete(self, stage, metrics=None):
        print(f'<<< COMPLETE {stage.name}')
    def on_progress(self, stage, pct, msg):
        pass

pipeline = RegistrationPipeline(config=get_settings(), callback=Callback())
options = {
    'debug_dir': 'data/processed/cross_mission_debug',
    'max_ortho_dim': 2048
}

t0 = time.time()
try:
    res = pipeline.run(
        source_path=src_xml,
        reference_path=ref_lbl,
        source_sensor='TMC2',
        ref_sensor='SELENE_TC',
        options=options
    )
    t1 = time.time()
    print('SUCCESS! Elapsed:', t1 - t0)
    print('Metrics:', res.metrics)
    print('Inliers count:', len([p for p in res.match_points if p.get('inlier')]))
    print('Total matches:', len(res.match_points))
except Exception as e:
    import traceback
    traceback.print_exc()
