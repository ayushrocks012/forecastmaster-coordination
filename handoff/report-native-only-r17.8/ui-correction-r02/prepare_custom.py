"""One custom chart with the repaired native controls; fabricated SAMPLE only."""
import importlib.util
import json
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
GUID = 'ForecastMasterOverlayR178'


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


report = load('r178_custom_report', 'prepare_project.py')
fixture = load('r178_custom_fixture', 'large_fixture.py')
context = load('r178_custom_context', 'chart_context.py')
presentation = load('r178_custom_gm', 'gm_presentation.py')
planning = load('r178_custom_planning', 'matrix_planning.py')
formats = load('r178_custom_formats', 'display_formats.py')


def build(destination, sectors=25):
    db = fixture.database()
    facts = next(t for t in db['model']['tables'] if t['name'] == 'fm_review_facts')
    source = facts['partitions'][0]['source']
    if not isinstance(sectors, int) or not 1 <= sectors <= 1000:
        raise ValueError('Invalid fabricated sector population')
    if source['expression'].count('GENERATESERIES(1,25)') != 1:
        raise ValueError('Fabricated generator changed')
    source['expression'] = source['expression'].replace('GENERATESERIES(1,25)', f'GENERATESERIES(1,{sectors})')
    report.create_sample(destination, fixture.defaults(), db,
                         'ForecastMaster R17.8 R02 CUSTOM OVERLAY SAMPLE')
    model_path = next(destination.glob('*.SemanticModel')) / 'model.bim'
    planned, cell_edits = planning.patch_database(json.loads(model_path.read_text()))
    planned, format_edits = formats.patch_database(planned)
    report.write(model_path, planned)
    folder = next(destination.glob('*.Report'))
    chart_path = folder / 'definition/pages/native_demand/visuals/native_chart/visual.json'
    chart = json.loads(chart_path.read_text())
    query = {}
    for role, table, name in [('Month', 'fm_review_axis', 'Month'),
            ('Series', 'fm_native_lines', 'SeriesLabel'), ('Scope', 'fm_native_lines', 'ScopeLabel'),
            ('Kind', 'fm_native_lines', 'LineKind')]:
        query[role] = {'projections': [report.projection(table, name)]}
    query['Value'] = {'projections': [report.projection('fm_native_measures', 'N Chart Monthly', True, 'Value')]}
    context_field = report.projection('fm_native_measures', context.NAME, True, 'Chart context')
    context_field['field']['Measure']['Expression']['SourceRef']['Schema'] = 'extension'
    query['Context'] = {'projections': [context_field]}
    extensions_path = folder / 'definition/reportExtensions.json'
    extensions = json.loads(extensions_path.read_text())
    entity = next(e for e in extensions['entities'] if e['name'] == 'fm_native_measures')
    entity['measures'].append({'name': context.NAME, 'dataType': 'Text', 'expression': context.EXPRESSION})
    report.write(extensions_path, extensions)
    chart['visual'].update(visualType=GUID, objects={}, query={
        'queryState': query,
        'sortDefinition': {'sort': [{'field': query['Month']['projections'][0]['field'], 'direction': 'Ascending'}],
                           'isDefaultSort': True}})
    report.write(chart_path, chart)
    config_path = folder / 'definition/report.json'
    config = json.loads(config_path.read_text())
    config.setdefault('resourcePackages', []).append({'name': GUID, 'type': 'CustomVisual',
        'items': [{'name': f'resources/{GUID}.pbiviz.json', 'path': f'{GUID}.pbiviz.json', 'type': 'CustomVisualMetadata'}]})
    report.write(config_path, config)
    presentation.apply(folder, report)
    package = next((HERE / 'custom-overlay-r01/dist').glob('*.pbiviz'))
    with ZipFile(package) as archive:
        for name in archive.namelist():
            if name.endswith('/'):
                continue
            target = folder / 'CustomVisuals' / GUID / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
    report.write(destination / 'EXPERIMENT.json', {'Stage': 'R178_ONE_CUSTOM_OVERLAY_SAMPLE',
        'FabricatedOnly': True, 'CustomVisuals': [GUID], 'OtherVisualsNative': True,
        'SectorsPerDriver': sectors, 'SectorCap': False, 'NumericKernelChangesFromR02': False,
        'MatrixCellEvaluationEdits': cell_edits,
        'SummaryDisplayFormatEdits': format_edits,
        'CompanyRelease': False, 'NativeDesktopAcceptance': 'PENDING'})


if __name__ == '__main__':
    import sys
    build(Path(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 25)
