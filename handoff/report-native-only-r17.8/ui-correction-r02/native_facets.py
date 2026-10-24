"""Isolated native small-multiples experiment; never a company installer.

Preserves every numeric expression and date/source binding in the R02 SAMPLE.
Only the local calculated line dictionary gains a presentation label.
"""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r178_facets_report', HERE / 'prepare_project.py')
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)
spec = importlib.util.spec_from_file_location('r178_facets_fixture', HERE / 'large_fixture.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def build(destination):
    report.create_sample(destination, fixture.defaults(), fixture.database(),
                         'ForecastMaster Native R17.8 R02 FACETS SAMPLE')
    semantic = next(destination.glob('*.SemanticModel/model.bim'))
    database = json.loads(semantic.read_text())
    lines = next(t for t in database['model']['tables'] if t['name'] == 'fm_native_lines')
    lines['columns'].append({'name': 'ComparisonLabel', 'type': 'calculated',
        'dataType': 'string', 'isHidden': True,
        'expression': '(SWITCH(\'fm_native_lines\'[LineKind],0,"Actual",1,"Forecast",'
                      'FORMAT(\'fm_native_lines\'[LineKind],"0")&"M trend"))'
                      '&" · "&\'fm_native_lines\'[DemandCycle]'})
    report.write(semantic, database)
    visual_path = next(destination.glob('*.Report/definition/pages/native_demand/visuals/native_chart/visual.json'))
    visual = json.loads(visual_path.read_text())
    query = visual['visual']['query']['queryState']
    query['Series']['projections'] = [report.projection('fm_native_lines', 'ComparisonLabel', label='Comparison')]
    # Desktop-authored placement uses Rows, not SmallMultiples. Keep the cycle
    # in the legend key: the disconnected line dictionary spans both cycles.
    query['Rows'] = {'projections': [report.projection('fm_native_lines', 'ScopeLabel', label='Scope')]}
    visual['filterConfig']['filters'].append(report.BASE.page_filter('fm_native_lines', 'Mode', 'Automatic ADS'))
    report.write(visual_path, visual)
    report.write(destination / 'EXPERIMENT.json', {
        'Stage': 'R178_NATIVE_FACETS_EXPERIMENT', 'FabricatedOnly': True,
        'NumericExpressionsChangedFromR02': False, 'CompanyRelease': False,
        'NativeScopePopulationAndScroll': 'PENDING'})


if __name__ == '__main__':
    import sys
    build(Path(sys.argv[1]))
