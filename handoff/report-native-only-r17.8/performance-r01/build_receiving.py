"""Compose a separate R03 TEST cell without changing the released R02 handoff.

Reuse its guarded one-write/private-backup workflow. Only the two cell
expressions and two extra percentage comparisons differ from that workflow.
"""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import ast
import json

import prepared
import strictcells

HERE = Path(__file__).resolve().parent
OLD = prepared.R02 / 'receiving-r01'
DESTINATION = HERE / 'receiving-r03'


def write_native_cases():
    source = (OLD / 'native_cases.py').read_text().replace('R02', 'R03')
    source = source.replace('HERE = Path(__file__).resolve().parent',
        "HERE = Path(__file__).resolve().parent\nR02ROOT = HERE.parents[1] / 'ui-correction-r02'")
    source = source.replace('HERE.parent /', 'R02ROOT /')
    source = source.replace("elif measure == 'N Variance %':", "elif measure == 'N Variance %' or 'pct' in check['Variant']:")
    source = source.replace("'PairedComparisons': 24", "'PairedComparisons': 30")
    ast.parse(source, feature_version=(3, 10))
    (DESTINATION / 'native_cases.py').write_text(source)


def compose(database):
    candidate, names = prepared.adapter.patch_database(database)
    return strictcells.patch(candidate), names


def build(archive):
    if DESTINATION.exists():
        raise ValueError('Preserve previous receiving build')
    base = prepared.load('perf_receiving_builder', OLD / 'build_cell.py')
    fragment = (OLD / 'receiving.pyfrag').read_text().replace('R02', 'R03')
    for old, new in [
        ("('N Headline Cell', [filt('fm_native_headline', 'Key', 'variance')]),", "('N Headline Cell', [filt('fm_native_headline', 'Key', 'variance')]),\n            ('N Headline Cell', [filt('fm_native_headline', 'Key', 'pct')]),"),
        ("('N Summary Cell', [filt('fm_native_columns', 'ColumnKey', '12:abs')])", "('N Summary Cell', [filt('fm_native_columns', 'ColumnKey', '12:abs')]),\n            ('N Summary Cell', [filt('fm_native_columns', 'ColumnKey', '12:pct')])")]:
        if fragment.count(old) != 1:
            raise ValueError('Receiving query shape changed')
        fragment = fragment.replace(old, new)
    original_load, original_template = base.load, base.template
    def load(name, path):
        if name == 'r178_receiving_adapter':
            return SimpleNamespace(selection=prepared.adapter.selection, planning=prepared.adapter.planning,
                formats=prepared.adapter.formats, patch_database=compose)
        return original_load(name, path)
    def template(sample):
        with ZipFile(BytesIO(original_template(sample))) as source:
            files = {n: source.read(n) for n in source.namelist()}
        pbip = 'ForecastMaster R17.8 R02 TEST.pbip'
        files['ForecastMaster R17.8 R03 TEST.pbip'] = files.pop(pbip)
        heading = base.REPORT_FOLDER + '/definition/pages/native_demand/visuals/heading/visual.json'
        value = json.loads(files[heading])
        value['visual']['objects']['general'][0]['properties']['paragraphs'][0]['textRuns'][0]['value'] = 'ForecastMaster · Demand review · R17.8 R03 TEST'
        files[heading] = json.dumps(value, ensure_ascii=False, indent=2).encode()
        files['OPEN FIRST.txt'] = files['OPEN FIRST.txt'].replace(b'R02', b'R03')
        output = BytesIO()
        with ZipFile(output, 'w', compression=ZIP_DEFLATED) as target:
            for name, raw in sorted(files.items()):
                info = ZipInfo(name, date_time=(2026, 10, 24, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                target.writestr(info, raw)
        return output.getvalue()
    base.load, base.template = load, template
    base.REPORT_FOLDER = 'ForecastMaster R17.8 R03 TEST.Report'
    with TemporaryDirectory(prefix='fm-perf-cell-build-') as temp:
        base.HERE = Path(temp)
        (base.HERE / 'receiving.pyfrag').write_text(fragment)
        result = base.build(archive)
        source = (base.HERE / 'INSTALL AND PREPARE PRIVATE TEST R02.py').read_text()
        # Change only the module docstring, never the embedded ZIP's base64.
        doc = ast.get_docstring(ast.parse(source), clean=False)
        source = source.replace(doc, doc.replace('R02', 'R03').replace('24 sequential', '30 sequential'), 1)
        ast.parse(source, feature_version=(3, 10))
        DESTINATION.mkdir()
        (DESTINATION / 'INSTALL AND PREPARE PRIVATE TEST R03.py').write_text(source)
        (DESTINATION / 'REPORT TEMPLATE.zip').write_bytes((base.HERE / 'REPORT TEMPLATE.zip').read_bytes())
    test = (OLD / 'test_receiving.py').read_text().replace('R02', 'R03').replace(
        "HERE.parent / 'adapter.py'", "HERE.parents[1] / 'ui-correction-r02/adapter.py'")
    test = test.replace("['PairedScalarComparisons'], 24", "['PairedScalarComparisons'], 30").replace(
        "['InstalledScalarReadbacks'], 24", "['InstalledScalarReadbacks'], 30")
    test = test.replace('HERE = Path(__file__).resolve().parent',
        'HERE = Path(__file__).resolve().parent\nsys.path.insert(0, str(HERE.parent))\nimport strictcells')
    test = test.replace('env.adapter.patch_database(before)[0]', 'strictcells.patch(env.adapter.patch_database(before)[0])')
    (DESTINATION / 'test_receiving.py').write_text(test)
    write_native_cases()
    result['CellBytes'] = len(source.encode())
    result['Revision'] = 'R03'
    result['PairedComparisons'] = 30
    return result


if __name__ == '__main__':
    import sys
    print(json.dumps(build(Path(sys.argv[1])), indent=2))
