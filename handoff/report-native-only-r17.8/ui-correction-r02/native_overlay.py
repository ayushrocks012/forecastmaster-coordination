"""Fabricated single-overlay qualification, never a company installer.

Uses Desktop's saved allowBinnedLineSample=False option. No numeric measure
body changes, top-N sector filter, manual comparison cap, grid or company data.
"""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


report = load('r178_overlay_report', 'prepare_project.py')
fixture = load('r178_overlay_fixture', 'large_fixture.py')


def build(destination, sectors=30):
    if sectors not in (25, 30):
        raise ValueError('This qualification fixture covers 25 and 30 sectors')
    db = fixture.database()
    facts = next(t for t in db['model']['tables'] if t['name'] == 'fm_review_facts')
    source = facts['partitions'][0]['source']
    old = 'GENERATESERIES(1,25)'
    if source['expression'].count(old) != 1:
        raise ValueError('Fabricated fact generator changed')
    source['expression'] = source['expression'].replace(old, f'GENERATESERIES(1,{sectors})')
    report.create_sample(destination, fixture.defaults(), db,
                         f'ForecastMaster Native R17.8 R02 OVERLAY {sectors} SAMPLE')
    root = next(destination.glob('*.Report/definition/pages/native_demand/visuals'))
    chart_path = root / 'native_chart/visual.json'
    chart = json.loads(chart_path.read_text())
    chart['visual']['query']['options'] = {'allowBinnedLineSample': False}
    report.write(chart_path, chart)
    driver_path = root / 'drivers/visual.json'
    driver = json.loads(driver_path.read_text())
    driver['visual'].setdefault('objects', {}).setdefault('general', [{}])[0].setdefault('properties', {})['filter'] = {
        'filter': report.BASE.PP.category_filter('fm_native_files', 'GrowthDriver', ['Driver 01'])}
    report.write(driver_path, driver)
    view_path = root / 'view/visual.json'
    view = json.loads(view_path.read_text())
    view['visual']['objects']['general'][0]['properties']['filter'] = {
        'filter': report.BASE.PP.category_filter('fm_native_view', 'View', ['Sectors'])}
    report.write(view_path, view)
    report.write(destination / 'EXPERIMENT.json', {
        'Stage': 'R178_SINGLE_OVERLAY_QUALIFICATION_PENDING',
        'FabricatedOnly': True, 'SectorsPerDriver': sectors, 'Files': 20,
        'Cycles': 2, 'GrowthDrivers': 5, 'FactRows': sectors * 20 * 84 * 10,
        'DefaultProbe': 'Driver 01 / Sectors / October / Market / Units',
        'ManualSectorLimit': False, 'SmallMultiples': False, 'CompanyRelease': False})


if __name__ == '__main__':
    import sys
    build(Path(sys.argv[1]))
