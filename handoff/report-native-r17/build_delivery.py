"""Assemble a PRIVATE native candidate. This command never contacts Fabric."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
from uuid import UUID
from zipfile import ZipFile,ZIP_DEFLATED
from installation import render
from native_model import SQL_VIEWS
from prepare_project import create

HERE=Path(__file__).resolve().parent


def build(source,destination,zip_path,affiliate=None,cycle=None):
    project=create(source,destination,affiliate,cycle)
    ref=json.loads(next(source.glob('*.Report/definition.pbir')).read_text())
    cs=ref['datasetReference']['byConnection']['connectionString']
    model=str(UUID(re.search(r'semanticModelId=([^;]+)',cs,re.I).group(1)))
    old_setup=source.parent/'SETUP REPORTING FEED.py'
    assignments={}
    for node in ast.parse(old_setup.read_text()).body:
        if isinstance(node,ast.Assign) and isinstance(node.value,ast.Constant):
            for target in node.targets:
                if isinstance(target,ast.Name):assignments[target.id]=node.value.value
    workspace=str(UUID(assignments['WORKSPACE']));lakehouse=str(UUID(assignments['LAKEHOUSE']))
    (destination/'PROBE NATIVE MODEL.py').write_text(render(workspace,model,lakehouse))
    (destination/'NATIVE VIEWS.sql').write_text(SQL_VIEWS)
    for name in ['README.md','OPEN FIRST.txt']:
        shutil.copy2(HERE/name,destination/name)
    receipts=sorted(HERE.glob('VALIDATION-*.json'))
    for receipt in receipts:shutil.copy2(receipt,destination/receipt.name)
    metadata={'Release':'CANDIDATE - NOT APPROVED FOR PRODUCTION REPLACEMENT','ReceivingSourceMode':'UNKNOWN - RUN READ-ONLY PROBE',
              'SourceDefaults':{'Affiliate':affiliate,'Cycle':cycle,'Period':cycle[:4]+' FY' if cycle else None},
              'CompanyInstallation':False,'CompanyPublication':False,'NativeDesktopRendering':False,
              'NumericFigures':'Native DAX, numeric export values','PreservedRuntime':'R16.6 Advanced workspace',
              'NewCustomScope':'Metadata selection, sibling order and FX entry only',
              'Files':{p.relative_to(destination).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.rglob('*') if p.is_file()}}
    (destination/'DELIVERY.json').write_text(json.dumps(metadata,indent=2)+'\n')
    if zip_path.exists():raise ValueError('Do not overwrite an existing delivery ZIP.')
    with ZipFile(zip_path,'x',ZIP_DEFLATED) as z:
        for path in sorted(destination.rglob('*')):
            if path.is_file():z.write(path,path.relative_to(destination))
    print(json.dumps({'Project':str(project),'ZIP':str(zip_path),'Bytes':zip_path.stat().st_size,
                      'SHA256':hashlib.sha256(zip_path.read_bytes()).hexdigest(),'Published':False},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('destination',type=Path);p.add_argument('zip',type=Path)
    p.add_argument('--affiliate');p.add_argument('--cycle');a=p.parse_args();build(a.source,a.destination,a.zip,a.affiliate,a.cycle)
