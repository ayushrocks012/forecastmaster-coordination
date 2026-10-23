"""Build a fabricated native SAMPLE; keep TEST preparation temporary and held."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('r178_build_project',HERE/'prepare_project.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

def build():
    out=HERE/'candidate';out.mkdir(exist_ok=True)
    outputs=[out/(p.NAME+'.zip'),out/(p.SAMPLE_NAME+'.zip')]
    if any(path.exists() for path in outputs):raise ValueError('Preserve existing candidate bytes; use a new version')
    with TemporaryDirectory(prefix='fm-r178-native-') as temp:
        test=Path(temp)/'test';sample=Path(temp)/'sample'
        p.create(HERE.parents[1]/'report-native-only-r17.7/candidate/ForecastMaster Native Only R17.7 TEST.zip',test)
        p.create_sample(test,sample)
        p.zip_project(test,outputs[0]);p.zip_project(sample,outputs[1])
    return [path.name for path in outputs]

if __name__=='__main__':print(json.dumps({'Prepared':build(),'CompanyInstallation':'PENDING; use matching R01 adapter first'}))
