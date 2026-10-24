"""New isolated fabricated Desktop sample; no company connection or release edit."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import cells
import strictcells
import regression
import prepared


def build(destination, archive, candidate):
    if destination.exists():
        raise ValueError('Preserve previous Desktop samples')
    bound = regression.checked(candidate)
    if bound.get('Prototype') not in ('cells', 'strictcells') or hashlib.sha256(archive.read_bytes()).hexdigest() != bound['SampleArchiveSHA256']:
        raise ValueError('Require frozen fabricated sample and cell-only candidate')
    with ZipFile(archive) as source:
        files = {name: source.read(name) for name in source.namelist() if not name.endswith('/')}
    bim = next(name for name in files if name.endswith('/model.bim'))
    before = json.loads(files[bim])
    if any(p['source']['type'] != 'calculated' for t in before['model']['tables'] for p in t.get('partitions', [])):
        raise ValueError('Fabricated calculated sample only')
    after = (strictcells if bound['Prototype'] == 'strictcells' else cells).patch(before)
    candidate_db = json.loads((candidate / 'candidate.json').read_text())
    candidate_db['model']['defaultPowerBIDataSourceVersion'] = before['model']['defaultPowerBIDataSourceVersion']
    if candidate_db != after:
        raise ValueError('Desktop model is not exact qualified candidate plus original host hint')
    files[bim] = json.dumps(after, ensure_ascii=False, indent=2).encode()
    heading = next(name for name in files if name.endswith('/visuals/heading/visual.json'))
    value = json.loads(files[heading])
    value['visual']['objects']['general'][0]['properties']['paragraphs'][0]['textRuns'][0]['value'] = 'ForecastMaster · R17.8 Performance SAMPLE · fabricated'
    files[heading] = json.dumps(value, ensure_ascii=False, indent=2).encode()
    destination.mkdir(parents=True)
    for name, raw in files.items():
        path = (destination / name).resolve()
        if not path.is_relative_to(destination.resolve()):
            raise ValueError('Unsafe archive path')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    entry = next(name for name in files if name.endswith('.pbip'))
    binding = {'Files': {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()},
        'Prototype': bound['Prototype'], 'SourceCandidateSHA256': prepared.load('perf_desktop_probe', Path(__file__).parent / 'probe.py').digest(candidate / 'candidate.json'),
        'EntryPoint': entry, 'CompanyDataOrConnection': False,
        'Changes': 'Two cell expressions; SAMPLE heading only. Original Desktop host hint retained.'}
    (destination / 'FROZEN-DESKTOP-INPUTS.json').write_text(json.dumps(binding, indent=2))
    return {'Directory': str(destination), 'EntryPoint': entry}


if __name__ == '__main__':
    import sys
    print(json.dumps(build(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])), indent=2))
