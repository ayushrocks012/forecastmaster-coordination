"""Build the guarded R02 cell and thin template from the qualified SAMPLE05.

The generated cell embeds only existing public definitions/chart resources.
Actual file defaults are injected privately in the company notebook.
"""
import ast
import base64
from copy import deepcopy
import hashlib
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import pprint
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPORT_FOLDER = 'ForecastMaster R17.8 R02 TEST.Report'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def selected(source, names):
    parts, found = [], set()
    for node in ast.parse(source).body:
        keys = {node.name} if isinstance(node, (ast.FunctionDef, ast.ClassDef)) else {t.id for t in node.targets if isinstance(t, ast.Name)} if isinstance(node, ast.Assign) else set()
        if keys & names:
            parts.append(ast.get_source_segment(source, node))
            found |= keys & names
    if found != names:
        raise ValueError('Missing frozen helper declarations: ' + str(names - found))
    return '\n\n'.join(parts)


def template(sample_archive):
    with ZipFile(sample_archive) as source:
        report_root = next(n.split('/')[0] for n in source.namelist() if n.endswith('/definition.pbir'))
        files = {REPORT_FOLDER + n[len(report_root):]: source.read(n) for n in source.namelist() if n.startswith(report_root + '/') and not n.endswith('/')}
    old_test = ROOT.parent / 'test-release-r01/candidate/ForecastMaster Compact Native R17.8 TEST.zip'
    with ZipFile(old_test) as frozen:
        binding = next(n for n in frozen.namelist() if n.endswith('/definition.pbir'))
        files[REPORT_FOLDER + '/definition.pbir'] = frozen.read(binding)
    heading = REPORT_FOLDER + '/definition/pages/native_demand/visuals/heading/visual.json'
    value = json.loads(files[heading])
    value['visual']['objects']['general'][0]['properties']['paragraphs'][0]['textRuns'][0]['value'] = 'ForecastMaster · Demand review · R17.8 R02 TEST'
    files[heading] = json.dumps(value, ensure_ascii=False, indent=2).encode()
    picker = REPORT_FOLDER + '/definition/pages/native_demand/visuals/file_picker/visual.json'
    value = json.loads(files[picker])
    value['visual']['objects']['general'][0]['properties']['filter']['filter']['Where'][0]['Condition']['In']['Values'] = [[{'Literal': {'Value': "'__PRIVATE_ADS_DEFAULTS__'"}}]]
    files[picker] = json.dumps(value, ensure_ascii=False, indent=2).encode()
    files['ForecastMaster R17.8 R02 TEST.pbip'] = json.dumps({'$schema': 'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json',
        'version': '1.0', 'artifacts': [{'report': {'path': REPORT_FOLDER}}], 'settings': {'enableAutoRecovery': True}}, indent=2).encode()
    files['OPEN FIRST.txt'] = b'PRIVATE TEST REPORT. Existing R17.8 R02 adapter must have verified readback. No manual refresh or publish. Extract all contents to a NEW folder; open the PBIP. File defaults are explicit choices from preparation time; new imports require selecting their visible file entries. Clearing files blanks results. Keep this ZIP private.\n'
    if any('.SemanticModel/' in n for n in files):
        raise ValueError('Thin report contains a model')
    payload = BytesIO()
    with ZipFile(payload, 'w', compression=ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = ZipInfo(name, date_time=(2026, 10, 24, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, data)
    return payload.getvalue()


def build(sample_archive):
    adapter = load('r178_receiving_adapter', ROOT / 'adapter.py')
    before = adapter.selection.original_database()
    after, names = adapter.patch_database(before)
    old, new = adapter.planning.measures(before), adapter.planning.measures(after)
    expected = {n: {k: deepcopy(m[k]) for k in ('expression', 'formatString', 'formatStringDefinition') if k in m} for n, m in old.items()}
    patches = {n: new[n]['expression'] for n in names}
    formats = {n: new[n]['formatStringDefinition']['expression'] for n in adapter.formats.NAMES}
    archive = template(sample_archive)
    (HERE / 'REPORT TEMPLATE.zip').write_bytes(archive)
    previous = (ROOT.parent / 'test-release-r01/INSTALL COMPACT TEST R01.py').read_text()
    helpers = {'WORKSPACE', 'LAKEHOUSE', 'TEST', 'NAME', 'FIELDS', 'ITEM', 'KINDS', 'DATE_QUERY',
        'CheckStopped', 'require', 'http', 'operation_path', 'read_definition', 'digest', 'identity', 'routing', 'connections',
        'as_date', 'semantic_dates', 'verified_backup', 'safe_failure', 'expression_text', 'normalized',
        'processing_history', 'complete_update', 'date_signature', 'validate_dates'}
    source = '''"""ONE NEW company ForecastMaster_GM_Setup cell, existing TEST only, ONCE.
24 sequential paired scalars plus three no-file blanks; values never printed/stored.
Full private backup, exact installed R01 guard, one update/readback, private report
download with actual ADS defaults. No refresh/source/production write or publish.
STOPPED or uncertain: return JSON; do not retry, delete markers or refresh.
"""
import base64
from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
from io import BytesIO
import json
import math
from numbers import Number
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from urllib.parse import quote, urlsplit
from uuid import UUID, uuid4
from zipfile import ZipFile, ZIP_DEFLATED

''' + selected(previous, helpers) + '\n\n'
    for name, value in [('EXPECTED_NATIVE', expected), ('EXPRESSION_PATCHES', patches), ('FORMAT_PATCHES', formats),
            ('REPORT_FOLDER', REPORT_FOLDER), ('TEMPLATE_SHA256', hashlib.sha256(archive).hexdigest())]:
        source += name + ' = ' + pprint.pformat(value, width=110, sort_dicts=False) + '\n\n'
    source += 'TEMPLATE = base64.b64decode(' + repr(base64.b64encode(archive).decode()) + ', validate=True)\n\n'
    numeric = load('r178_receiving_numeric', ROOT.parents[1] / 'report-native-only-r17.7/numeric_check.py')
    source += 'METADATA_QUERY = ' + repr(numeric.METADATA_QUERY) + '\n\n'
    defaults = '''EVALUATE SELECTCOLUMNS(FILTER(ALL('fm_native_files'),
 'fm_native_files'[ADSPriority]>0&&'fm_native_files'[PreferenceRank]=1&&'fm_native_files'[PreferenceTies]=1),
 "Country",'fm_native_files'[Country],"Cycle",'fm_native_files'[DemandCycle],"Driver",'fm_native_files'[GrowthDriver],
 "Label",'fm_native_files'[FileChoiceLabel],"Scenario",'fm_native_files'[Scenario])'''
    source += 'DEFAULTS_QUERY = ' + repr(defaults) + '\n\n'
    source += (HERE / 'receiving.pyfrag').read_text() + '''

if __name__ == '__main__':
    import sempy.fabric as fabric
    import notebookutils
    run(fabric.FabricRestClient(retry_config={"total": 0}), fabric.PowerBIRestClient(retry_config={"total": 0}), notebookutils.fs, fabric.evaluate_dax)
'''
    ast.parse(source, feature_version=(3, 10))
    (HERE / 'INSTALL AND PREPARE PRIVATE TEST R02.py').write_text(source)
    return {'CellBytes': len(source.encode()), 'ExpressionEdits': len(patches), 'DisplayDefinitions': len(formats),
            'TemplateSHA256': hashlib.sha256(archive).hexdigest(), 'TemplateBytes': len(archive)}


if __name__ == '__main__':
    import sys
    print(json.dumps(build(Path(sys.argv[1])), indent=2))
