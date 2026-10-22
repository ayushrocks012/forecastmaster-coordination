"""Validate generated PBIR against published Microsoft schemas, not rendering."""
import hashlib,json,sys,urllib.request
from pathlib import Path
from jsonschema import validators
from referencing import Registry,Resource

project=Path(sys.argv[1]);cache=Path(sys.argv[2]);out=Path(sys.argv[3]);cache.mkdir(parents=True,exist_ok=True)
resources={}
for p in cache.glob('*.json'):
    d=json.loads(p.read_text())
    if '$id' in d:resources[d['$id']]=d

def retrieve(uri):
    if uri not in resources:
        if not uri.startswith('https://developer.microsoft.com/json-schemas/'):
            raise ValueError('Unexpected schema host: '+uri)
        data=json.loads(urllib.request.urlopen(uri,timeout=25).read())
        resources[uri]=data
        (cache/(hashlib.sha256(uri.encode()).hexdigest()+'.json')).write_text(json.dumps(data))
    return Resource.from_contents(resources[uri])

registry=Registry(retrieve=retrieve);checked=0;errors=[];unavailable=[]
for path in sorted(project.rglob('*.json')):
    if 'CustomVisuals' in path.parts or 'StaticResources' in path.parts:continue
    doc=json.loads(path.read_text());uri=doc.get('$schema')
    if not uri:continue
    try:
        schema=retrieve(uri).contents
        validator=validators.validator_for(schema)(schema,registry=registry)
        issues=list(validator.iter_errors(doc))
        for e in issues:errors.append({'File':path.relative_to(project).as_posix(),'At':list(e.absolute_path),'Reason':e.message})
        checked+=1
    except Exception as e:
        item={'File':path.relative_to(project).as_posix(),'Schema':uri,'Error':str(e)}
        if any(x in path.parts for x in ('advancedreview','refreshdemand')) and '/visualContainer/2.14.0/' in uri:
            unavailable.append(item)
        else:errors.append(item)
result={'Checked':checked,'Failures':errors,'UnavailableOriginalSchemas':unavailable,
 'Evidence':'PBIR JSON schema validation only. Original R16.6 visual schemas may be unavailable. Desktop roles/rendering remain unverified.'}
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));sys.exit(bool(errors))
