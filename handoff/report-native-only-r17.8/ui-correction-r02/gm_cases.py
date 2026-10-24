"""Native DAX presentation checks at both signs of every alert boundary."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r178_gm', HERE / 'gm_presentation.py')
gm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gm)


def build(directory, candidate):
    if directory.exists():
        raise ValueError('Preserve earlier evidence')
    directory.mkdir(parents=True)
    (directory / 'candidate.json').write_bytes(candidate.read_bytes())
    definitions = '\n'.join("MEASURE 'fm_native_measures'[" + name + '] = ' + value for name, value in gm.MEASURES.items())
    # Threshold isolation uses valid admission; real source/period values are
    # covered independently by matrix_cases. No business measure is installed.
    definitions += '''
MEASURE 'fm_native_measures'[N Source OK] = 1
MEASURE 'fm_native_measures'[N Period Available] = 1
MEASURE 'fm_native_measures'[N Actual Only] = 0
'''
    admitted = ",TREATAS({\"market\"},'fm_native_metric'[RowID]),TREATAS({6,12,24},'fm_native_trend'[Window])"
    cases, expected = [], {}
    boundaries = [(None, None), (0, '#E5F2E6'), (.049999, '#E5F2E6'), (.05, '#E5F2E6'),
                  (.050001, '#FFF3CD'), (.10, '#FFF3CD'), (.100001, '#F9E1E3'), (1, '#F9E1E3')]
    for source, color_measure, column, keys in [('Headline', 'N GM Review Color', 'fm_native_headline', ['variance', 'pct']),
            ('Summary', 'N GM Summary Color', 'fm_native_columns', ['12:abs', '12:pct'])]:
        for key in keys:
            for value, color in boundaries:
                for sign in ([-1, 1] if value else [1]):
                    number = 'BLANK()' if value is None else repr(value * sign)
                    name = f'{source}/{key}/{number}'
                    pct = 'N Headline Variance %' if source == 'Headline' else 'N Variance %'
                    cell = 'N Headline Cell' if source == 'Headline' else 'N Summary Cell'
                    define = definitions + f"\nMEASURE 'fm_native_measures'[{pct}] = {number}\nMEASURE 'fm_native_measures'[{cell}] = 1"
                    field = 'Key' if source == 'Headline' else 'ColumnKey'
                    query = 'DEFINE ' + define + f'\nEVALUATE CALCULATETABLE(ROW("Color",[{color_measure}]),TREATAS({{"{key}"}},\'{column}\'[{field}])' + admitted + ')'
                    cases.append({'name': name, 'model': 'candidate', 'query': query}); expected[name] = color
        for key, cell_value in [('plan', '1'), (keys[0], 'BLANK()')]:
            cell = 'N Headline Cell' if source == 'Headline' else 'N Summary Cell'
            pct = 'N Headline Variance %' if source == 'Headline' else 'N Variance %'
            field = 'Key' if source == 'Headline' else 'ColumnKey'
            name = source + '/uncoloured/' + key
            ratio = '.5' if cell_value == '1' else 'BLANK()'
            query = 'DEFINE ' + definitions + f"\nMEASURE 'fm_native_measures'[{pct}] = {ratio}\nMEASURE 'fm_native_measures'[{cell}] = {cell_value}"
            query += f'\nEVALUATE CALCULATETABLE(ROW("Color",[{color_measure}]),TREATAS({{"{key}"}},\'{column}\'[{field}])' + admitted + ')'
            cases.append({'name': name, 'model': 'candidate', 'query': query}); expected[name] = None
    for window, color in [(6, '#E5F2E6'), (12, '#FFF3CD'), (24, '#F9E1E3')]:
        define = definitions + '''
MEASURE 'fm_native_measures'[N Summary Cell] = 1
MEASURE 'fm_native_measures'[N Variance %] = SWITCH(SELECTEDVALUE('fm_native_trend'[Window]),6,.05,12,.1,24,.15)
'''
        name = f'Summary/independent-column-window/{window}'
        query = 'DEFINE ' + define + f'''EVALUATE CALCULATETABLE(ROW("Color",[N GM Summary Color]),
TREATAS({{"{window}:pct"}},'fm_native_columns'[ColumnKey])''' + admitted + ')'
        cases.append({'name': name, 'model': 'candidate', 'query': query}); expected[name] = color
    # Explicit guard and deselected-window edges, with a nonblank large ratio.
    for source, measure, table, field, key in [('Headline', 'N GM Review Color', 'fm_native_headline', 'Key', 'pct'),
                                             ('Summary', 'N GM Summary Color', 'fm_native_columns', 'ColumnKey', '12:pct')]:
        pct = 'N Headline Variance %' if source == 'Headline' else 'N Variance %'
        for edge in ('source', 'period', 'metric', 'window', 'actual'):
            if source == 'Headline' and edge in ('window', 'actual'):
                continue  # Headline actual-only admission belongs to its variance measure.
            define = definitions + f"\nMEASURE 'fm_native_measures'[{pct}] = .5\n"
            filters = admitted
            if edge in ('source', 'period'):
                guard = 'N Source OK' if edge == 'source' else 'N Period Available'
                define = define.replace(f'[{guard}] = 1', f'[{guard}] = 0')
            elif edge == 'actual':
                define = define.replace('[N Actual Only] = 0', '[N Actual Only] = 1')
            elif edge == 'metric':
                filters = filters.replace('TREATAS({"market"},\'fm_native_metric\'[RowID])', "REMOVEFILTERS('fm_native_metric')")
            elif edge == 'window':
                filters = filters.replace('TREATAS({6,12,24}', 'TREATAS({6}')
            name = source + '/admission/' + edge
            query = 'DEFINE ' + define + f' EVALUATE CALCULATETABLE(ROW("Color",[{measure}]),TREATAS({{"{key}"}},\'{table}\'[{field}])' + filters + ')'
            cases.append({'name': name, 'model': 'candidate', 'query': query}); expected[name] = None
    for name, value in [('queries', cases), ('expected', expected)]:
        (directory / (name + '.json')).write_text(json.dumps(value))
    return {'Cases': len(cases)}


def verify(directory):
    results = json.loads((directory / 'results.json').read_text(encoding='utf-8-sig'))
    expected = json.loads((directory / 'expected.json').read_text())
    failures = [r['name'] for r in results if 'error' in r or len(r['rows']) != 1
                or r['rows'][0].get('[Color]') != expected[r['name']]]
    if len(results) != len(expected) or {r['name'] for r in results} != set(expected):
        failures.append('Requested population')
    receipt = {'Stage': 'LOCAL_GM_NATIVE_FORMAT_RULES', 'Cases': len(expected), 'Failures': failures,
               'NumericModelChanged': False, 'CompanyAcceptance': False,
               'SHA256': {f: hashlib.sha256((directory / f).read_bytes()).hexdigest()
                          for f in ('candidate.json', 'queries.json', 'results.json')}}
    if failures:
        raise AssertionError(json.dumps(receipt))
    return receipt


if __name__ == '__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[1])) if '--verify' in sys.argv else
                     build(Path(sys.argv[1]), Path(sys.argv[2])), indent=2))
