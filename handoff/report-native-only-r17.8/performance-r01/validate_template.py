"""Validate the separate public thin template against official versioned schemas."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile

import jsonschema
import requests
from referencing import Registry, Resource


def validate(path):
    downloaded = {}
    def contents(url):
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.netloc != 'developer.microsoft.com' or not parsed.path.startswith('/json-schemas/fabric/'):
            raise ValueError('Refuse non-official schema URL')
        if url not in downloaded:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            downloaded[url] = response.content
        return json.loads(downloaded[url])
    registry = Registry(retrieve=lambda uri: Resource.from_contents(contents(uri)))
    count, failures = 0, []
    with ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.endswith(('.json', '.pbip', '.pbir')):
                continue
            value = json.loads(archive.read(name))
            if not isinstance(value, dict) or '$schema' not in value:
                continue
            schema = contents(value['$schema'])
            validator = jsonschema.validators.validator_for(schema)(schema, registry=registry)
            errors = list(validator.iter_errors(value))
            failures.extend({'File': name, 'Path': list(e.absolute_path), 'Validator': e.validator} for e in errors)
            count += 1
    if failures:
        raise AssertionError(json.dumps(failures))
    return {'SchemaDocumentsValidated': count, 'SchemaFailures': 0,
        'TemplateSHA256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'OfficialSchemaSHA256': {url: hashlib.sha256(raw).hexdigest() for url, raw in downloaded.items()}}


if __name__ == '__main__':
    import sys
    print(json.dumps(validate(Path(sys.argv[1])), indent=2))
