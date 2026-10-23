"""Microsoft JSON schemas for PBIP/PBIR only. Does not execute DAX or Desktop."""
import json
from pathlib import Path
import sys
from urllib.request import urlopen
from zipfile import ZipFile
import jsonschema
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

def check(path):
    cache={}
    def fetch(uri):
        if not uri.startswith('https://developer.microsoft.com/json-schemas/'):
            raise ValueError('Unexpected schema host')
        if uri not in cache:
            with urlopen(uri,timeout=20) as response:cache[uri]=json.load(response)
            # Microsoft's embedded URL uses schema-embedded.json while some
            # returned documents declare schema.embedded.json as their $id.
            # Register that exact document under its own declared identity.
            declared=cache[uri].get('$id')
            if declared:cache[declared]=cache[uri]
        return cache[uri]
    registry=Registry(retrieve=lambda uri:Resource.from_contents(fetch(uri),default_specification=DRAFT7))
    checked=0
    with ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.endswith(('.json','.pbir','.pbip')):continue
            value=json.loads(archive.read(name))
            if '$schema' not in value:continue
            schema=fetch(value['$schema'])
            cls=jsonschema.validators.validator_for(schema)
            cls(schema,registry=registry.with_resource(value['$schema'],Resource.from_contents(schema,default_specification=DRAFT7))).validate(value)
            checked+=1
    return {'File':Path(path).name,'SchemaDocumentsValidated':checked,'Failures':0,'DaxAndDesktopExecuted':False}

if __name__=='__main__':print(json.dumps(check(Path(sys.argv[1])),indent=2))
