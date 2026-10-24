"""Native SAMPLE correction builder. TEST templates are held, with no company defaults.

File defaults are supplied as private labels, never inferred from a filename.
Existing report/model packages stay byte-identical.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


OLD = load('r178_ui_old_report', HERE.parent / 'test-release-r01/prepare_project.py')
MODEL = load('r178_ui_model', HERE / 'model.py')
BASE, lit, projection, write = OLD.BASE, OLD.lit, OLD.projection, OLD.write
NAME = 'ForecastMaster Native R17.8 R02 SAMPLE'


def selection_bookmark(name, section, metric):
    states = {}
    for target, column, value in (('section', 'Section', section), ('metric', 'MetricLabel', metric)):
        states[target] = {'singleVisual': {'objects': {'merge': {'general': [{'properties': {
            'filter': {'filter': BASE.PP.category_filter('fm_native_metric', column, [value])}}}]}}}}
    return {'$schema': BASE.PP.SCHEMA + 'bookmark/1.3.0/schema.json', 'name': name,
            'displayName': section, 'options': {'applyOnlyToTargetVisuals': True,
                'targetVisualNames': ['section', 'metric'], 'suppressActiveSection': True,
                'suppressData': False, 'suppressDisplay': True},
            'explorationState': {'version': '1.3', 'activeSection': 'native_demand',
                                'sections': {'native_demand': {'visualContainers': states}}}}


def make_page(default_labels):
    if not isinstance(default_labels, list) or not default_labels or not all(isinstance(x, str) and x for x in default_labels):
        raise ValueError('Explicit verified default file labels required')
    page, before = OLD.make_page()
    vs = {v['name']: deepcopy(v) for v in before}
    layout = {'headline': (20, 272, 1400, 144), 'dynamic_chart_title': (20, 430, 1090, 28),
              'native_chart': (20, 472, 1400, 300), 'executive_title': (20, 790, 900, 24),
              'executive_summary': (20, 834, 1400, 288), 'files_heading': (20, 1134, 1400, 24),
              'file_picker': (20, 1188, 1400, 166), 'view': (1200, 426, 220, 44),
              'view_label': (1138, 434, 54, 20), 'trend': (1200, 782, 220, 44),
              'trend_label': (1078, 790, 114, 20)}
    for name, rect in layout.items():
        vs[name]['position'].update(zip(('x', 'y', 'width', 'height'), rect))
    vs['heading']['visual']['objects']['general'][0]['properties']['paragraphs'][0]['textRuns'][0]['value'] = (
        'ForecastMaster · R17.8 R02 SAMPLE · FABRICATED DATA')
    # Data-only bookmarks set Section and a compatible measure in one action.
    # They do not reset files, scope, periods or independent trend selections.
    vs['section']['isHidden'] = True
    vs['section']['position'].update(x=380, y=86, width=240, height=64)
    vs['section_label'] = OLD.padding(BASE.text('section_label', 'Section', 388, 91, 220, 18, 10), 0)
    vs['section_ims'] = BASE.button('section_ims', 'IMS / Market', 380, 112, 130, 'section_ims')
    vs['section_ef'] = BASE.button('section_ef', 'Ex-factory', 512, 112, 108, 'section_ef')
    for name in ('section_ims', 'section_ef'):
        vs[name]['position']['height'] = 36
    chart = vs['native_chart']['visual']
    chart['objects']['valueAxis'][0]['properties'].update(labelDisplayUnits=lit(1), labelPrecision=lit(2))
    chart['objects']['legend'][0]['properties'].update(position=lit('Bottom'), fontSize=lit(10))
    chart['objects']['seriesLabels'][0]['properties']['show'] = lit(False)
    # Fixed native matrix height includes headers, three rows, padding and scrollbars.
    OLD.padding(vs['headline'], 4)
    executive = vs['executive_summary']['visual']
    rows = [p for p in executive['query']['queryState']['Rows']['projections']
            if p['queryRef'] != 'fm_native_scenario.Scenario']
    executive['query']['queryState']['Rows']['projections'] = rows
    for role in ('Rows', 'Columns'):
        for index, p in enumerate(executive['query']['queryState'][role]['projections']):
            # Desktop-authored Drill up marks SectorLabel inactive until the
            # user expands a driver. Active hidden descendants still enter the
            # query and consume its 102-row window before Driver 05 is reached.
            p['active'] = role == 'Columns' or index == 0
    # Old isToggled=True children inverted a non-collapsed period default.
    # Let native levels expand columns, and expose driver -> sector rows directly.
    executive['expansionStates'] = [{'roles': [role], 'levels': [{
        'queryRefs': [p['queryRef']], 'identityKeys': [p['field']],
        'isCollapsed': role == 'Rows', 'isPinned': role == 'Rows'} for p in ps], 'root': {}}
        for role, ps in ((r, executive['query']['queryState'][r]['projections']) for r in ('Rows', 'Columns'))]
    # Use the same file dimension for driver and filename selections. Native
    # categorical filtering then excludes other drivers before value evaluation.
    driver = vs['drivers']['visual']
    driver['query']['queryState']['Values']['projections'] = [projection('fm_native_files', 'GrowthDriver', label='Growth drivers')]
    driver.pop('syncGroup', None)
    vs['drivers'].pop('filterConfig', None)
    BASE.PP.measure_filter(vs['drivers'], 'N File Available')
    # This control is bound to SectorLabel, not a tier-code field.
    vs['tiers']['visual']['objects']['header'][0]['properties']['text'] = lit('Sectors / forecast tiers')
    picker = vs['file_picker']['visual']
    # Desktop-authored conversion verified that listSlicer hides out-of-scope
    # selected items. The classic slicer pins those items above its filtered list.
    picker['visualType'] = 'listSlicer'
    picker['objects'] = {
        'general': [{'properties': {'selfFilterEnabled': lit(True), 'filter': {
            'filter': BASE.PP.category_filter('fm_native_files', 'FileChoiceLabel', default_labels)}}}],
        'selection': [{'properties': {'singleSelect': lit(False), 'strictSingleSelect': lit(False),
                                    'selectAllCheckboxEnabled': lit(False)}}],
        'value': [{'properties': {'fontSize': lit(10), 'textWrap': lit(False)}}],
        'layout': [{'properties': {'showFixedSize': lit(True), 'fixedHeight': lit(28)}}]}
    vs['files_heading']['visual']['objects']['general'][0]['properties']['paragraphs'][0]['textRuns'][0]['value'] = (
        'Saved files · select one version per driver · clear to hide results')
    page['height'] = 1366
    interactions = {(i['source'], i['target']): i for i in page['visualInteractions']}
    interactions[('drivers', 'file_picker')] = {'source': 'drivers', 'target': 'file_picker', 'type': 'DataFilter'}
    for name in vs:
        if name not in ('drivers', 'file_picker'):
            interactions[('drivers', name)] = {'source': 'drivers', 'target': name, 'type': 'DataFilter'}
    page['visualInteractions'] = list(interactions.values())
    for i, v in enumerate(vs.values()):
        v['position'].update(z=i, tabOrder=i)
    return page, list(vs.values())


def create_sample(destination, default_labels, fabricated_database=None, project_name=NAME):
    if destination.exists():
        raise ValueError('Use a new destination; preserve earlier builds')
    source = HERE.parent / 'test-release-r01/candidate/ForecastMaster Compact Native R17.8 SAMPLE.zip'
    with ZipFile(source) as z:
        z.extractall(destination)
    report = next(destination.glob('*.Report'))
    semantic = next(destination.glob('*.SemanticModel'))
    db = fabricated_database if fabricated_database is not None else json.loads((semantic / 'model.bim').read_text())
    # Both sample routes are fully local calculated models. Never accept a
    # live/directLake partition or cloud-bound model as a fabricated fixture.
    for table in db['model']['tables']:
        for partition in table.get('partitions', []):
            if partition.get('source', {}).get('type') != 'calculated':
                raise ValueError('SAMPLE requires calculated-only fabricated partitions')
    fixed, changed = MODEL.patch_database(db)
    write(semantic / 'model.bim', fixed)
    root = report / 'definition'
    shutil.rmtree(root / 'pages')
    page, visuals = make_page(default_labels)
    write(root / 'pages/pages.json', {'$schema': BASE.PP.SCHEMA + 'pagesMetadata/1.0.0/schema.json',
        'pageOrder': ['native_demand'], 'activePageName': 'native_demand'})
    write(root / 'pages/native_demand/page.json', page)
    for v in visuals:
        write(root / 'pages/native_demand/visuals' / v['name'] / 'visual.json', v)
    for name, section, metric in [('section_ims', 'IMS / Market', 'Market'), ('section_ef', 'Ex-factory', 'Ex-factory ADS')]:
        write(root / 'bookmarks' / (name + '.bookmark.json'), selection_bookmark(name, section, metric))
    write(root / 'bookmarks/bookmarks.json', {'$schema': BASE.PP.SCHEMA + 'bookmarksMetadata/1.0.0/schema.json',
                                            'items': [{'name': n} for n in ('section_ims', 'section_ef')]})
    for old in destination.glob('*.pbip'):
        project = json.loads(old.read_text())
        old.unlink()
        write(destination / (project_name + '.pbip'), project)
    write(destination / 'OPEN FIRST.txt', 'FABRICATED SAMPLE ONLY. Local native inspection; no company installation or acceptance.\n')
    write(destination / 'PRESERVATION.json', {'Stage': 'R178_R02_LOCAL_UI_REPAIR_SAMPLE',
        'FabricatedDataOnly': True, 'CloudConnection': False, 'SemanticMeasureEdits': changed,
        'CompanyInstallation': 'NOT PREPARED; do not run an old installer for this candidate',
        'NativeInspection': 'PENDING'})
    return changed
