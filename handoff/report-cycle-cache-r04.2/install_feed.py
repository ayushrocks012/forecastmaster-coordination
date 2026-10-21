"""Update only the existing report feed measures, using the operator's Fabric session."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
import time
from datetime import datetime, timezone

WORKSPACE = 'f5cb5742-9a7c-4337-a4c0-952706dddf0b'
MODEL = 'e7af2967-7725-4108-a170-9e490d4e35bb'
LAKEHOUSE = 'd6e33ebd-67b1-420a-8d84-c3a0d04d8b21'
ROOT = f'https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE}/semanticModels/{MODEL}'


def normalized(expression):
    if isinstance(expression, list):
        expression = '\n'.join(expression)
    # Ignore formatting only outside DAX quoted strings and table identifiers.
    return re.sub(r'"(?:""|[^"])*"|\'(?:\'\'|[^\'])*\'|\s+', lambda m: '' if m[0].isspace() else m[0], expression)


def unpack(definition):
    parts = definition['parts']
    if len({p['path'] for p in parts}) != len(parts):
        raise RuntimeError('Duplicate definition part paths; no update prepared.')
    found = [p for p in parts if p['path'] == 'model.bim']
    if len(found) != 1 or found[0].get('payloadType') != 'InlineBase64':
        raise RuntimeError('Expected the existing TMSL model.bim; no update prepared.')
    return found[0], json.loads(base64.b64decode(found[0]['payload'], validate=True))


def measures(model):
    tables = [t for t in model['model']['tables'] if t['name'] == 'fm_review_measures']
    if len(tables) != 1:
        raise RuntimeError('Expected the existing fm_review_measures table.')
    return {m['name']: m for m in tables[0]['measures']}


def prepare(definition, expected, updates):
    result = copy.deepcopy(definition)
    part, model = unpack(result)
    existing = measures(model)
    changed = []
    for name, update in updates.items():
        if name not in existing:
            raise RuntimeError(f'Missing existing measure {name}; no update prepared.')
        actual = normalized(existing[name]['expression'])
        if actual not in {normalized(expected[name]['expression']), normalized(update['expression'])}:
            raise RuntimeError(f'{name} differs from the qualified R04 feed. No update prepared.')
        if actual != normalized(update['expression']):
            existing[name]['expression'] = update['expression']
            changed.append(name)
    part['payload'] = base64.b64encode(json.dumps(model, ensure_ascii=False).encode()).decode()
    return result, changed


def unchanged_except_feed(before, after, updates):
    _, a = unpack(before)
    _, b = unpack(after)
    for value in [a, b]:
        for name in updates:
            measures(value)[name]['expression'] = '<qualified feed expression>'
    if a != b:
        raise RuntimeError('Model properties outside the feed measures differ.')
    def other(d):
        return {p['path']: p for p in d['parts'] if p['path'] != 'model.bim'}
    if other(before) != other(after):
        raise RuntimeError('Definition parts outside model.bim differ.')


class Fabric:
    def __init__(self, token, http, sleep=time.sleep, now=time.monotonic):
        self.http, self.sleep, self.now = http, sleep, now
        self.headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}

    def call(self, method, url, body=None):
        # Never replay an ambiguous write after a timeout or transient response.
        response = self.http.request(method, url, headers=self.headers, json=body, timeout=90)
        response.raise_for_status()
        if response.status_code != 202:
            return response.json() if response.content else {}
        operation = response.headers.get('Location')
        if not operation or not operation.startswith('https://api.fabric.microsoft.com/v1/operations/'):
            raise RuntimeError('Missing Fabric operation URL; outcome requires inspection.')
        deadline = self.now() + 600
        while self.now() < deadline:
            self.sleep(min(max(int(response.headers.get('Retry-After', '3')), 1), 30))
            response = self.http.get(operation, headers=self.headers, timeout=90)
            response.raise_for_status()
            status = response.json().get('status')
            if status in ['Failed', 'Canceled', 'Cancelled']:
                raise RuntimeError('Fabric definition operation ' + str(response.json()))
            if status == 'Succeeded':
                result = self.http.get(operation.rstrip('/') + '/result', headers=self.headers, timeout=90)
                if result.status_code in [204, 404]:
                    return {}
                result.raise_for_status()
                return result.json() if result.content else {}
            print('Waiting for report feed update:', status)
        raise RuntimeError('Definition operation is still unconfirmed after 10 minutes. Do not repeat the write.')

    def read(self):
        return self.call('POST', ROOT + '/getDefinition?format=TMSL')['definition']


def install(api, fs, expected, updates):
    old = api.read()
    new, changed = prepare(old, expected, updates)
    unchanged_except_feed(old, new, updates)
    if not changed:
        return {'Status': 'ALREADY_INSTALLED', 'Release': 'R04.2', 'ChangedMeasures': []}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = f'abfss://{WORKSPACE}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE}/Files/ForecastMasterRefreshState/report-upgrades/R04.2/{stamp}'
    fs.mkdirs(folder)
    backup = json.dumps(old, ensure_ascii=False)
    fs.put(folder + '/model-before.json', backup, False)
    saved = fs.head(folder + '/model-before.json', len(backup.encode()) + 1024)
    if saved != backup:
        raise RuntimeError('Could not verify the readable model backup; no update submitted.')
    print('Backup:', folder + '/model-before.json')
    current = api.read()
    if unpack(current)[1] != unpack(old)[1] or {p['path']: p for p in current['parts'] if p['path'] != 'model.bim'} != {p['path']: p for p in old['parts'] if p['path'] != 'model.bim'}:
        raise RuntimeError('The model changed during preparation; no update submitted.')
    print('Updating only:', ', '.join(changed))
    api.call('POST', ROOT + '/updateDefinition', {'definition': new, 'options': {'allowPurgeData': False}})
    actual = api.read()
    unchanged_except_feed(old, actual, updates)
    for name, update in updates.items():
        if normalized(measures(unpack(actual)[1])[name]['expression']) != normalized(update['expression']):
            raise RuntimeError('The installed expression is unconfirmed: ' + name + '. Retain the backup and output.')
    receipt = {'Status': 'INSTALLED', 'Release': 'R04.2', 'ChangedMeasures': changed, 'Backup': folder + '/model-before.json', 'DataPurgeAllowed': False, 'ReportPagesAndButtons': 'Not modified by this installer', 'CompanyInteractionSpeed': 'NOT_YET_MEASURED', 'InstalledDefinitionSHA256': hashlib.sha256(json.dumps(actual, sort_keys=True).encode()).hexdigest()}
    fs.put(folder + '/receipt.json', json.dumps(receipt, indent=2), False)
    return receipt


def main(expected, updates):
    import requests
    import notebookutils
    api = Fabric(notebookutils.credentials.getToken('pbi'), requests)
    result = install(api, notebookutils.fs, expected, updates)
    print(json.dumps(result, indent=2))
    print('READY: R04.2 cycle feed verified. Reload the report with the R04.2 visual, select a demand cycle, then test the other filters.')
    return result
