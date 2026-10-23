"""Refresh only the public, metadata-only catalog block in UNDERSTANDING.md.

Never contacts Fabric or opens a company export. Sources are the preserved,
manifest-bound fabricated SAMPLE packages; no table rows/partition data copied.
Default --check verifies freshness; --write updates the one marked block.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / 'handoff/report-native-only-r17.8/UNDERSTANDING.md'
BEGIN = '<!-- PUBLIC-CATALOG-BEGIN -->'
END = '<!-- PUBLIC-CATALOG-END -->'
SAMPLES = {
    'R17.7': 'handoff/report-native-only-r17.7/candidate/ForecastMaster Native Only R17.7 SAMPLE.zip',
    'R17.8 draft': 'handoff/report-native-only-r17.8/candidate/ForecastMaster Compact Native R17.8 SAMPLE.zip',
}


def metadata(name):
    manifest = json.loads((ROOT / 'HANDOFF-MANIFEST.json').read_text())['Files']
    path = ROOT / name; raw = path.read_bytes()
    assert name in manifest and hashlib.sha256(raw).hexdigest() == manifest[name]['SHA256']
    with ZipFile(path) as archive:
        candidates = [n for n in archive.namelist() if n.endswith('/model.bim')]
        assert len(candidates) == 1
        db = json.loads(archive.read(candidates[0]))
        visuals = [json.loads(archive.read(n)) for n in archive.namelist() if n.endswith('/visual.json')]
    return db['model'], visuals, hashlib.sha256(raw).hexdigest()


def safe_cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def render():
    old, _, old_hash = metadata(SAMPLES['R17.7'])
    draft, visuals, draft_hash = metadata(SAMPLES['R17.8 draft'])
    tables = old['tables']
    measures = {m['name']: m for t in tables for m in t.get('measures', [])}
    draft_measures = {m['name']: m for t in draft['tables'] for m in t.get('measures', [])}
    assert len(tables) == 29 and len(measures) == 51 and len(draft_measures) == 52
    assert len(visuals) == 26 and {v['visual']['visualType'] for v in visuals} <= {
        'slicer', 'pivotTable', 'lineChart', 'cardVisual', 'textbox'}
    lines = [BEGIN, '', '## Public source catalog: names, fields, relationships, DAX and visuals', '',
      '**CODE CONTRACT / FABRICATED PACKAGE METADATA — not an exported inventory of the company workspace.**',
      'The R17.7 SAMPLE supplies 29 table schemas (24 native helpers plus five simplified',
      'original-table fixtures) and 51 named native measures. The receiving TEST reports',
      '39 tables and 98 measures. Do not equate the fixture with the complete live model.',
      'Original tables may expose additional fields/measures; their complete metadata is',
      'not in the R02 JSON. Engine-generated format measures are also a separate inventory question.', '',
      'Only names/types, relationships and public formulas are reproduced. No rows,',
      'partition DATATABLE payloads, actual source IDs, financial observations or connections.', '',
      f'- R17.7 source ZIP SHA256: `{old_hash}`.', f'- R17.8 draft source ZIP SHA256: `{draft_hash}`.',
      '- Refresh this block with `python3 tools/refresh_understanding_catalog.py --write`;',
      '  verify with `python3 tools/refresh_understanding_catalog.py --check`.', '',
      '### Table and field dictionary', '']
    for table in tables:
        native = table['name'].startswith('fm_native_')
        lines += [f"#### {table['name']}", '',
                  'Native calculated/helper contract.' if native else
                  'Simplified SAMPLE schema; see the physical-source dictionary above for extra writer fields.', '',
                  '| Field | Semantic type | Sort column |', '| --- | --- | --- |']
        for column in table.get('columns', []):
            lines.append('| ' + ' | '.join(safe_cell(column.get(k, '—')) for k in ('name', 'dataType', 'sortByColumn')) + ' |')
        lines.append('')
    lines += ['### Native relationship contract', '',
      'These seven additions are the public native contract. R02 reports twelve total',
      'relationships in TEST; the remaining original relationships were preserved but',
      'are not enumerated by that JSON. No new fact-to-file relationship is invented here.', '',
      '| Relationship | From | To |', '| --- | --- | --- |']
    for rel in old.get('relationships', []):
        lines.append(f"| {rel['name']} | {rel['fromTable']}[{rel['fromColumn']}] | {rel['toTable']}[{rel['toColumn']}] |")
    lines += ['', '### Named native measures: complete R17.7 public definitions', '',
      'These are public candidate definitions, with expression fingerprints for drift',
      'checks. R03 installation/readback and R02 whole-definition preservation provide',
      'the receiving evidence chain; this is not a new company definition export.',
      'DAX identity checks cover only the tested contexts, not independent business parity.', '']
    for name, measure in measures.items():
        expression = measure['expression']
        if isinstance(expression, list): expression = '\n'.join(expression)
        fingerprint = hashlib.sha256(expression.encode()).hexdigest()
        refs = sorted(set(re.findall(r"'([^']+)'\[([^]]+)\]", expression)))
        refs_text = ', '.join(f'`{a}[{b}]`' for a, b in refs) or 'No explicit table-column references.'
        lines += [f'#### {name}', '', f"Folder: `{measure.get('displayFolder', '—')}`. Expression SHA256: `{fingerprint}`.", '',
                  'Explicit column references: ' + refs_text, '', '<details>', '<summary>Exact public DAX and format</summary>', '',
                  '```dax', expression, '```', '']
        fmt = measure.get('formatStringDefinition', {}).get('expression')
        if fmt:
            if isinstance(fmt, list): fmt = '\n'.join(fmt)
            lines += ['Dynamic format:', '', '```dax', fmt, '```', '']
        elif 'formatString' in measure:
            lines += ['Static format: `' + measure['formatString'] + '`.', '']
        lines += ['</details>', '']
    changed = [name for name, m in draft_measures.items() if name not in measures or m['expression'] != measures[name]['expression']]
    lines += ['### R17.8 draft differences — NOT INSTALLED', '',
      'Changed or added measure names: ' + ', '.join('`' + n + '`' for n in changed) + '.', '',
      'The readable FileChoiceLabel helper expression also changes. There are no new',
      'table/column names in this draft. Exact draft formulas and preservation checks:',
      '[model.py](model.py). R02 did not install them or qualify their new selection behavior.', '',
      '### R17.8 draft native visual-to-field map', '',
      'This maps the current compact fabricated layout, not the live Service report.',
      'Only built-in slicer, matrix, line-chart, card and textbox types are present.', '',
      '| Visual | Built-in type | Fields and measures |', '| --- | --- | --- |']
    for visual in sorted(visuals, key=lambda v: v['name']):
        spec = visual['visual']; bindings = []
        for role, group in spec.get('query', {}).get('queryState', {}).items():
            for projection in group.get('projections', []): bindings.append(role + ': ' + projection.get('queryRef', '—'))
        lines.append('| ' + ' | '.join(map(safe_cell, (visual['name'], spec['visualType'], '; '.join(bindings) or 'Layout/text'))) + ' |')
    # Source identities, not source amounts. Bridge catalog is already a public,
    # sanitized design contract; retain its original business names and order.
    catalog = json.loads((ROOT / 'design/currency-plan-review-r15/bridge-catalog.json').read_text())
    order = ['share', 'abbott', 'market', 'pi', 'net', 'community', 'wholesaler', 'ni', 'homecare',
             'hospital', 'hcl', 'competitor', 'nursing', 'private', 'internal', 'retail', 'unassigned', 'ads']
    by_id = {r['id']: r for r in catalog['bindings']}
    lines += ['', '### S&OP source identity/order map', '',
      'This is the retained source contract used by the design. Blank sub-channel',
      'means the parent context, not Wholesaler. No alternate business taxonomy invented.', '',
      '| Order / Row ID | Channel | Sub-channel | Calendar | Units source | Value source |',
      '| --- | --- | --- | --- | --- | --- |']
    for i, key in enumerate(order, 1):
        row = by_id[key]
        source = lambda d: d.get('section', '') + ' / ' + d.get('measure', '')
        lines.append('| ' + ' | '.join(map(safe_cell, (f'{i} / {key}', row['channel'], row.get('subChannel') or '(blank)',
                     row['basis'], source(row['units']), source(row['value'])))) + ' |')
    lines += ['', END]
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    text = DOCUMENT.read_text(); assert text.count(BEGIN) == text.count(END) == 1
    start = text.index(BEGIN); finish = text.index(END) + len(END)
    block = render()
    if args.write: DOCUMENT.write_text(text[:start] + block + text[finish:])
    else: assert text[start:finish] == block, 'Public catalog drift; review source and refresh the marked block'
    print('Public reference catalog verified: 29 SAMPLE schemas, 51 R17.7 native measures, 26 draft visuals; live inventory remains separately labelled.')


if __name__ == '__main__': main()
