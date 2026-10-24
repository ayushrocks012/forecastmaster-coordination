"""Public fabricated workload: 2 cycles, 20 files, 5 drivers, 25 sectors/file.

One ADS and one saved alternative per driver/cycle; 84 months, Units/Value.
Small DAX generators materialize 420,000 fact rows without embedding company data.
"""
from datetime import date
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r178_large_cases', HERE / 'native_cases.py')
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)
CYCLES = ('2026-07', '2026-10')
DRIVERS = tuple('Driver ' + str(i).zfill(2) for i in range(1, 6))
SECTORS = 25


def files():
    rows = []
    for ci, cycle in enumerate(CYCLES, 1):
        cm = int(cycle[-2:])
        for di, driver in enumerate(DRIVERS, 1):
            for scenario in ('ADS', 'REVIEW_001'):
                key = cycle + '-D' + str(di) + '-' + scenario
                name = 'UK_Driver_' + str(di).zfill(2) + '_' + cycle + '_IMS2026' + str(cm - 2).zfill(2) + '_' + scenario + '.xlsm'
                stamp = '2026-10-23T' + str(8 + ci).zfill(2) + ':' + str(di).zfill(2) + ':00Z'
                rows.append({'SourceRevisionID': key, 'SourceFileName': name, 'SourceRelativePath': 'SyntheticLarge/' + name,
                    'Country': 'UK', 'DemandCycle': cycle, 'GrowthDriver': driver, 'SourceProfile': 'Ext',
                    'PublicationStatus': 'SAVED', 'FileLabel': name + ' · Imported ' + stamp + ' · SyntheticLarge/' + key,
                    'IMSActualsThrough': date(2026, cm - 2, 1), 'ExFactoryActualsThrough': date(2026, cm - 1, 1)})
    return rows


def defaults():
    result = []
    for row in files():
        if row['SourceFileName'].endswith('_ADS.xlsm'):
            stamp = row['FileLabel'].split(' · Imported ')[1].split(' · ')[0]
            from datetime import datetime
            text = datetime.fromisoformat(stamp.replace('Z', '+00:00')).strftime('%d %b %Y %H:%M:%S')
            result.append(row['SourceFileName'] + ' · ' + text + ' UTC')
    return result


def database():
    db = n.m.original_database()
    tables = {t['name']: t for t in db['model']['tables']}
    tables['fm_review_files']['partitions'] = n.old.f.datatable('fm_review_files', files())['partitions']
    month = 'SELECTCOLUMNS(GENERATESERIES(0,83),"Month",EDATE(DATE(2023,1,1),[Value]))'
    for name in ('fm_review_axis', 'fm_review_months'):
        tables[name]['partitions'][0]['source']['expression'] = month
    # The aggregate metric ef reads ef-ads-* components across channels, not
    # the separate gm-ads-* sector-total component. Use one explicit EF channel
    # in this fabricated workload so the independent expected total is exact.
    catalog = [dict(r, RowID='ads') if r['RowID'] == 'wholesaler' else r
               for r in n.old.f.nm.catalog_rows()
               if r['RowID'] in {'market', 'abbott', 'pi', 'net', 'wholesaler'}]
    columns = ['RowID', 'Channel', 'SubChannel', 'Display', 'Component']
    comp = 'DATATABLE(' + ','.join(json.dumps(k) + ',STRING' for k in columns) + ',{' + ','.join(
        '{' + ','.join(json.dumps(row[k]) for k in columns) + '}' for row in catalog) + '})'
    expression = '''VAR _files=SELECTCOLUMNS('fm_review_files',"_id",[SourceRevisionID],
 "_driver",VALUE(RIGHT([GrowthDriver],2)),"_cycle",IF([DemandCycle]="2026-07",1,2),
 "_ims",DATEDIFF(DATE(2023,1,1),[IMSActualsThrough],MONTH),
 "_ef",DATEDIFF(DATE(2023,1,1),[ExFactoryActualsThrough],MONTH),
 "_alt",IF(CONTAINSSTRING([SourceFileName],"REVIEW_001"),1.03,1.0))
VAR _sectors=SELECTCOLUMNS(GENERATESERIES(1,25),"_sector",[Value])
VAR _months=SELECTCOLUMNS(GENERATESERIES(0,83),"_month",[Value])
VAR _components=''' + comp + '''
RETURN SELECTCOLUMNS(CROSSJOIN(_files,_sectors,_months,_components),
 "SourceRevisionID",[_id],"Channel",[Channel],"SubChannel",[SubChannel],
 "Sector","Sector "&FORMAT([_driver],"00")&"."&FORMAT([_sector],"00"),
 "Month",EDATE(DATE(2023,1,1),[_month]),"ComponentKey",[Component],
 "Amount",VAR _b=40000+[_driver]*2000+[_sector]*100+[_month]*150
 VAR _market=(_b+IF([_month]>[_ims],750*[_cycle],0))*[_alt]
 VAR _abbott=(_b*(0.2+[_sector]*0.001)+IF([_month]>[_ims],120*[_cycle],0))*[_alt]
 VAR _pi=_b*0.02*[_alt]
 VAR _ads=(_b*0.3+IF([_month]>[_ef],400*[_cycle],0))*[_alt]
 VAR _price=2+[_driver]*0.1+[_sector]*0.01
 RETURN IF([Display]="Units",SWITCH([RowID],"market",_market,"abbott",_abbott,"pi",_pi,
 "net",_abbott-_pi,"ads",_ads),SWITCH([RowID],"market",_market*_price,
 "abbott",_abbott*(_price+0.3),"pi",_pi*(_price+0.1),
 "net",_abbott*(_price+0.3)-_pi*(_price+0.1),"ads",_ads*_price)),
 "MissingCells",0,"NumericCells",1)'''
    tables['fm_review_facts']['partitions'][0]['source']['expression'] = expression
    return db


def amount(cycle, driver, sector, month, row='market', display='Units', alternative=False):
    ci = CYCLES.index(cycle) + 1
    ims = 36 + int(cycle[-2:]) - 3
    ef = ims + 1
    base = 40000 + driver * 2000 + sector * 100 + month * 150
    scale = 1.03 if alternative else 1.0
    market = (base + (750 * ci if month > ims else 0)) * scale
    abbott = (base * (0.2 + sector * 0.001) + (120 * ci if month > ims else 0)) * scale
    pi = base * .02 * scale
    ads = (base * .3 + (400 * ci if month > ef else 0)) * scale
    price = 2 + driver * .1 + sector * .01
    if display == 'Value':
        market, abbott, pi, ads = market * price, abbott * (price + .3), pi * (price + .1), ads * price
    return {'market': market, 'abbott': abbott, 'pi': pi, 'net': abbott - pi, 'ef': ads}[row]


def total(cycle, month, row='market', display='Units', drivers=range(1, 6), alternative_drivers=()):
    return sum(amount(cycle, d, s, month, row, display, d in alternative_drivers)
               for d in drivers for s in range(1, 26))


def build(directory):
    if directory.exists():
        raise ValueError('Preserve previous large-run inputs')
    directory.mkdir(parents=True)
    baseline = database()
    candidate, edits = n.m.patch_database(baseline)
    for db in (baseline, candidate):
        db['name'] = db['id'] = 'ForecastMasterNativeSyntheticR178Large'
        db['model'].pop('defaultPowerBIDataSourceVersion', None)
    cases, expected = [], {}
    tf = n.tf

    def add(name, query, want=None, model='candidate'):
        cases.append({'name': name, 'model': model, 'query': query})
        if want is not None:
            expected[name] = want

    add('population', 'EVALUATE ROW("Files",COUNTROWS(\'fm_review_files\'),"Cycles",DISTINCTCOUNT(\'fm_review_files\'[DemandCycle]),'
        '"Drivers",DISTINCTCOUNT(\'fm_review_files\'[GrowthDriver]),"FileSectors",COUNTROWS(\'fm_native_scope\'),'
        '"Months",COUNTROWS(\'fm_review_axis\'),"Facts",COUNTROWS(\'fm_review_facts\'))',
        {'[Files]': 20, '[Cycles]': 2, '[Drivers]': 5, '[FileSectors]': 500, '[Months]': 84, '[Facts]': 420000})
    for cycle in CYCLES:
        for row in ('market', 'ef', 'share'):
            filters = [tf('fm_review_files', 'Country', ['UK']), tf('fm_review_files', 'DemandCycle', [cycle]),
                       n.DEFAULTS, tf('fm_native_metric', 'RowID', [row]), tf('fm_native_display', 'Display', ['Units'])]
            mi = 43
            value = total(cycle, mi, row if row != 'share' else 'abbott')
            if row == 'share':
                value /= total(cycle, mi)
            add('monthly/' + cycle + '/' + row, 'EVALUATE CALCULATETABLE(ROW("V",[N Monthly]),' +
                ','.join(filters + ["TREATAS({DATE(2026,8,1)},'fm_review_axis'[Month])"]) + ')', {'[V]': value})
        filters = [tf('fm_review_files', 'Country', ['UK']), tf('fm_review_files', 'DemandCycle', [cycle]),
            n.DEFAULTS, tf('fm_native_metric', 'RowID', ['market']), tf('fm_native_display', 'Display', ['Units']),
            tf('fm_native_periods', 'PeriodKey', ['2026:FY'])]
        plan = sum(total(cycle, mi) for mi in range(36, 48))
        add('plan/' + cycle, 'EVALUATE CALCULATETABLE(ROW("V",[N Plan]),' + ','.join(filters) + ')', {'[V]': plan})
        add('clear/' + cycle, 'EVALUATE CALCULATETABLE(ROW("V",[N Plan],"OK",[N Source OK]),' + ','.join(
            [f for f in filters if f != n.DEFAULTS]) + ')', {'[V]': None, '[OK]': 0})
    add('labels', 'EVALUATE SELECTCOLUMNS(\'fm_native_files\',"Label",[FileChoiceLabel],"Stamp",FORMAT([ImportedAtUTC],"yyyy-MM-dd HH:mm:ss"))')
    for name, value in [('baseline', baseline), ('candidate', candidate), ('queries', cases), ('expected', expected)]:
        (directory / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False))
    return {'Files': 20, 'Cycles': 2, 'Drivers': 5, 'SectorsPerFile': 25,
            'FileSectors': 500, 'Months': 84, 'FactRows': 420000, 'Queries': len(cases), 'MeasureEdits': edits}


def verify(directory):
    results = json.loads((directory / 'results.json').read_text(encoding='utf-8-sig'))
    cases = json.loads((directory / 'queries.json').read_text())
    expected = json.loads((directory / 'expected.json').read_text())
    by = {r['name']: r for r in results}
    failures = []
    if len(by) != len(results) or set(by) != {c['name'] for c in cases}:
        failures.append('Exact requested query population')
    for name, result in by.items():
        if 'error' in result:
            failures.append(name + ': ' + result['error'])
        if name not in expected:
            continue
        rows = result.get('rows', [])
        if len(rows) != 1:
            failures.append(name + ': expected one scalar row')
            continue
        for column, want in expected[name].items():
            got = rows[0].get(column)
            if not (want is None and got is None or isinstance(want, (int, float))
                    and isinstance(got, (int, float))
                    and math.isclose(want, got, rel_tol=1e-9, abs_tol=1e-6)):
                failures.append(name + '/' + column)
    labels = by.get('labels', {}).get('rows', [])
    if len(labels) != 20 or len({r.get('[Label]') for r in labels}) != 20:
        failures.append('20 unique file labels')
    if not set(defaults()) <= {r.get('[Label]') for r in labels}:
        failures.append('All 10 global preferred ADS labels match native values')
    if any('unavailable' in r.get('[Label]', '') or not r.get('[Stamp]', '').startswith('2026-10-23') for r in labels):
        failures.append('Readable valid import timestamps')
    receipt = {'Stage': 'LOCAL_R178_R02_LARGE_NATIVE_CHECKS', 'FabricatedOnly': True,
        'Queries': len(cases), 'Population': by.get('population', {}).get('rows'),
        'Failures': failures, 'QueryElapsedMs': {k: r.get('elapsedMs') for k, r in by.items()},
        'InputSHA256': {f: hashlib.sha256((directory / f).read_bytes()).hexdigest()
                        for f in ('baseline.json', 'candidate.json', 'queries.json', 'expected.json')},
        'CompanyFabricSpeedOrBusinessAcceptance': False}
    if failures:
        raise AssertionError(json.dumps(receipt, indent=2))
    return receipt


if __name__ == '__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[1])) if '--verify' in sys.argv else build(Path(sys.argv[1])), indent=2))
