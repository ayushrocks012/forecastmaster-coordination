"""Reuse the unchanged independent mixed-matrix population for full kernels."""
import hashlib
import json
from pathlib import Path
import shutil

import prepared
import regression


def build(destination,candidate,population):
    if destination.exists():
        raise ValueError('Preserve previous regression')
    cb,pb=regression.checked(candidate),regression.checked(population)
    if cb.get('Prototype') not in {'split-bulk-training','exact-bulk-kernels'} or pb.get('IndependentValueColorCells')!=11592:
        raise ValueError('Unknown candidate or independent population')
    queries=json.loads((population/'queries.json').read_text())
    expected=json.loads((population/'expected.json').read_text())
    if len(queries)!=75 or sum(map(len,expected.values()))!=11592:
        raise ValueError('Changed independent coverage')
    destination.mkdir(parents=True)
    shutil.copy2(candidate/'candidate.json',destination/'candidate.json')
    for name in ('queries.json','expected.json','run_profile.ps1','launch_synthetic_engine.ps1','matrix_cases.py'):
        shutil.copy2(population/name,destination/name)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,'Prototype':cb['Prototype'],
        'CandidateSourceSHA256':hashlib.sha256((candidate/'FROZEN-INPUTS.json').read_bytes()).hexdigest(),
        'ExpectedQueries':75,'IndependentValueColorCells':11592,'CompanyAcceptance':False,
        'OracleQueryBytesUnchanged':True},indent=2))
    return {'Directory':str(destination),'Queries':75,'IndependentValueColorCells':11592}


def verify(directory):
    bound=regression.checked(directory)
    # The copied verifier loads neighbouring code, so use the canonical module
    # only after proving its exact equality to the bound historical oracle.
    canonical=prepared.R02/'matrix_cases.py'
    if hashlib.sha256(canonical.read_bytes()).hexdigest()!=bound['Files']['matrix_cases.py']:
        raise ValueError('Changed canonical oracle')
    oracle=prepared.load('full_matrix_verified_oracle',canonical)
    receipt=oracle.verify(directory)
    receipt.update(Stage='LOCAL_COMPLETE_BULK_MIXED_MATRICES',FrozenInputsMatch=True,
        TaskOwnedEngineClosed=True,CompanyAcceptance=False,OracleQueryBytesUnchanged=True)
    return receipt


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:5])),indent=2))
