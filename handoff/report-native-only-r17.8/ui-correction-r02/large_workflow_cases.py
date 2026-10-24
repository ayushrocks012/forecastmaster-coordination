"""Expanded fabricated native arithmetic and high-cardinality workflow checks."""
import importlib.util
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('large_workflow_fixture', HERE / 'large_fixture.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
tf = f.n.tf


def expected(cycle, metric, display, year, window):
    cut = 36 + int(cycle[-2:]) - (2 if metric == 'ef' else 3)
    months = range((year - 2023) * 12, (year - 2023 + 1) * 12)
    def numerator(mi):
        return f.total(cycle, mi, 'abbott' if metric == 'share' else metric, display)
    def denominator(mi):
        return f.total(cycle, mi, 'market', display)
    def monthly(mi):
        return numerator(mi) / denominator(mi) if metric == 'share' else numerator(mi)
    ys = [monthly(mi) for mi in range(cut - window + 1, cut + 1)]
    mean, center = sum(ys) / window, (window - 1) / 2
    slope = sum((i - center) * (v - mean) for i, v in enumerate(ys)) / sum((i - center)**2 for i in range(window))
    def trend(mi):
        return monthly(mi) if mi <= cut else mean + slope * (mi - cut + window - (window + 1) / 2)
    if metric == 'share':
        den = sum(denominator(mi) for mi in months)
        plan = sum(numerator(mi) for mi in months) / den
        benchmark = sum(trend(mi) * denominator(mi) for mi in months) / den
    else:
        plan, benchmark = sum(numerator(mi) for mi in months), sum(trend(mi) for mi in months)
    return {'[Plan]': plan, '[Benchmark]': benchmark, '[Percent]': (plan - benchmark) / abs(benchmark),
            '[Monthly]': monthly(45)}


def correct_chart_query(query):
    if "SUMMARIZECOLUMNS('fm_native_lines'[ScopeLabel]," in query:
        return query.replace("SUMMARIZECOLUMNS('fm_native_lines'[ScopeLabel],",
            "SUMMARIZECOLUMNS('fm_native_lines'[SeriesLabel],'fm_native_lines'[ScopeLabel],")
    start = 'EVALUATE CALCULATETABLE(ROW('
    expression = '"Forecast",CALCULATE([N Chart Monthly],' + tf('fm_native_lines', 'LineKind', [1]) + ')'
    if query.count(start) != 1 or query.count(expression) != 1:
        raise ValueError('Unknown chart checker query shape')
    return query.replace(start, "EVALUATE CALCULATETABLE(VAR _r=SUMMARIZECOLUMNS('fm_native_lines'[SeriesLabel],"
        + tf('fm_native_lines', 'LineKind', [1]) + ',"V",[N Chart Monthly]) RETURN ROW(').replace(
        expression, '"Forecast",SUMX(_r,[V])')


def build(directory, correction_only=False):
    if directory.exists():
        raise ValueError('Use a new bound evidence directory')
    directory.mkdir(parents=True)
    db, edits = f.n.m.patch_database(f.database())
    db['name'] = db['id'] = 'ForecastMasterNativeSyntheticR178LargeWorkflows'
    db['model'].pop('defaultPowerBIDataSourceVersion', None)
    queries, wants = [], {}
    def add(name, query, want=None):
        queries.append({'name': name, 'model': 'candidate', 'query': query})
        if want is not None:
            wants[name] = want
    def filters(cycle, metric='market', display='Units'):
        return [tf('fm_review_files', 'Country', ['UK']), tf('fm_review_files', 'DemandCycle', [cycle]),
            tf('fm_native_currency', 'Currency', ['Local']), f.n.DEFAULTS,
            tf('fm_native_metric', 'RowID', [metric]), tf('fm_native_display', 'Display', [display])]
    for cycle in f.CYCLES:
        for metric in ('market', 'abbott', 'share', 'pi', 'net', 'ef'):
            for display in ('Units', 'Value'):
                for year in (2026, 2027):
                    for window in (6, 12, 24):
                        context = filters(cycle, metric, display) + [tf('fm_native_periods', 'PeriodKey', [str(year) + ':FY']),
                            tf('fm_native_trend', 'Window', [window]), "TREATAS({DATE(2026,10,1)},'fm_review_axis'[Month])"]
                        name = '/'.join(('numeric', cycle, metric, display, str(year), str(window)))
                        add(name, 'EVALUATE CALCULATETABLE(ROW("Plan",[N Plan],"Benchmark",[N Benchmark],'
                            '"Percent",[N Variance %],"Monthly",[N Monthly]),' + ','.join(context) + ')',
                            expected(cycle, metric, display, year, window))
        for view, count in (('Total', 1), ('Drivers', 5), ('Sectors', 125)):
            context = filters(cycle) + [tf('fm_native_view', 'View', [view]), tf('fm_native_chart_trend', 'Window', [12]),
                tf('fm_native_lines', 'Chart', ['demand']), "TREATAS({DATE(2026,12,1)},'fm_review_axis'[Month])"]
            add('chart/' + cycle + '/' + view, "EVALUATE VAR _r=SUMMARIZECOLUMNS('fm_native_lines'[ScopeLabel],"
                "'fm_native_lines'[LineKind]," + ','.join(context) + ',"V",[N Chart Monthly]) '
                'RETURN ROW("Scopes",COUNTROWS(SUMMARIZE(_r,\'fm_native_lines\'[ScopeLabel])),"Rows",COUNTROWS(_r))',
                {'[Scopes]': count, '[Rows]': count * 2})
        context = filters(cycle) + [tf('fm_native_periods', 'PeriodKey', ['2026:FY']), tf('fm_native_trend', 'Window', [6, 12])]
        add('executive/' + cycle, "EVALUATE VAR _r=SUMMARIZECOLUMNS('fm_native_scope'[GrowthDriver],"
            "'fm_native_scope'[SectorLabel],'fm_native_columns'[ColumnLabel]," + ','.join(context) +
            ',"V",[N Summary Cell]) RETURN ROW("Drivers",COUNTROWS(SUMMARIZE(_r,\'fm_native_scope\'[GrowthDriver])),'
            '"Sectors",COUNTROWS(SUMMARIZE(_r,\'fm_native_scope\'[SectorLabel])),"Columns",COUNTROWS(SUMMARIZE(_r,'
            '\'fm_native_columns\'[ColumnLabel])),"Rows",COUNTROWS(_r))',
            {'[Drivers]': 5, '[Sectors]': 125, '[Columns]': 5, '[Rows]': 625})
        # One alternative in Driver 01, preferred ADS in the other four drivers.
        labels = "SELECTCOLUMNS(FILTER(ALL('fm_native_files'),[DemandCycle]=\"" + cycle + "\"&&IF([GrowthDriver]=\"Driver 01\",CONTAINSSTRING([SourceFileName],\"REVIEW_001\"),[ADSPriority]>0)),\"L\",[FileChoiceLabel])"
        context = [x for x in filters(cycle) if x != f.n.DEFAULTS] + ["TREATAS(" + labels + ",'fm_native_files'[FileChoiceLabel])",
            tf('fm_native_view', 'View', ['Total']), tf('fm_native_chart_trend', 'Window', [12]),
            tf('fm_native_lines', 'Chart', ['demand']), "TREATAS({DATE(2026,12,1)},'fm_review_axis'[Month])"]
        add('mixed/' + cycle, 'EVALUATE CALCULATETABLE(ROW("OK",[N Source OK],"Monthly",[N Monthly],'
            '"Forecast",CALCULATE([N Chart Monthly],' + tf('fm_native_lines', 'LineKind', [1]) + ')), ' + ','.join(context) + ')',
            {'[OK]': 1, '[Monthly]': f.total(cycle, 47, alternative_drivers=(1,)), '[Forecast]': f.total(cycle, 47, alternative_drivers=(1,))})
    for q in queries:
        if q['name'].startswith(('chart/', 'mixed/')):
            q['query'] = correct_chart_query(q['query'])
    if correction_only:
        queries = [q for q in queries if q['name'].startswith(('chart/', 'mixed/'))]
        wants = {q['name']: wants[q['name']] for q in queries}
    for name, data in [('candidate', db), ('baseline', db), ('queries', queries), ('expected', wants)]:
        (directory / (name + '.json')).write_text(json.dumps(data, ensure_ascii=False))
    return {'Queries': len(queries), 'ScalarOracleContexts': 144, 'ArithmeticComparisons': 576,
            'FullSectorExecutiveContexts': 2, 'MixedVersionContexts': 2, 'MeasureEdits': edits}


def verify(directory, corrected_charts=None):
    cases = json.loads((directory / 'queries.json').read_text())
    wants = json.loads((directory / 'expected.json').read_text())
    results = json.loads((directory / 'results.json').read_text(encoding='utf-8-sig'))
    correction = None
    if corrected_charts is not None:
        if (directory / 'candidate.json').read_bytes() != (corrected_charts / 'candidate.json').read_bytes():
            raise ValueError('Correction uses a changed candidate')
        corrected_queries = json.loads((corrected_charts / 'queries.json').read_text())
        corrected_results = json.loads((corrected_charts / 'results.json').read_text(encoding='utf-8-sig'))
        prior = {q['name']: q for q in cases if q['name'].startswith(('chart/', 'mixed/'))}
        if len(prior) != 8 or len(corrected_queries) != 8 or {q['name'] for q in corrected_queries} != set(prior):
            raise ValueError('Require exactly the eight corrected chart grouping contexts')
        for q in corrected_queries:
            if q != dict(prior[q['name']], query=correct_chart_query(prior[q['name']]['query'])):
                raise ValueError('Chart correction changed unrelated context')
        replacements = {r['name']: r for r in corrected_results}
        if len(replacements) != 8 or set(replacements) != set(prior):
            raise ValueError('Corrected results incomplete')
        results = [replacements.get(r['name'], r) for r in results]
        correction = {'OriginalCheckerContexts': sorted(prior), 'AdditionalExecutedQueries': 8,
            'OnlyChange': 'Group the native categorical chart by SeriesLabel before evaluating its value',
            'SHA256': {k: hashlib.sha256((corrected_charts / k).read_bytes()).hexdigest()
                       for k in ('candidate.json', 'queries.json', 'results.json')}}
    by = {r['name']: r for r in results}
    failures = []
    if len(by) != len(cases) or len(by) != len(results) or set(by) != set(wants):
        failures.append('Exact requested population')
    comparisons = 0
    for name, want in wants.items():
        got = by.get(name, {})
        if 'error' in got or len(got.get('rows', [])) != 1:
            failures.append(name + ': native read/cardinality')
            continue
        for key, value in want.items():
            actual = got['rows'][0].get(key)
            comparisons += 1
            if not (isinstance(actual, (int, float)) and math.isclose(actual, value, rel_tol=1e-9, abs_tol=1e-6)):
                failures.append(name + '/' + key)
    receipt = {'Stage': 'LOCAL_R178_R02_LARGE_WORKFLOWS', 'FabricatedOnly': True,
        'LogicalContexts': len(cases), 'NumericContexts': 144, 'NumericComparisons': 576,
        'TotalComparisons': comparisons, 'Failures': failures,
        'InputSHA256': {k: hashlib.sha256((directory / k).read_bytes()).hexdigest()
                       for k in ('candidate.json', 'queries.json', 'expected.json', 'results.json')},
        'ElapsedMs': {k: r.get('elapsedMs') for k, r in by.items() if not k.startswith('numeric/')},
        'CompanyAcceptance': False}
    if correction:
        receipt['CheckerCorrection'] = correction
    if failures:
        raise AssertionError(json.dumps(receipt, indent=2))
    return receipt


if __name__ == '__main__':
    import sys
    directory = Path(sys.argv[1])
    if '--verify' in sys.argv:
        correction = Path(sys.argv[sys.argv.index('--corrected-charts') + 1]) if '--corrected-charts' in sys.argv else None
        print(json.dumps(verify(directory, correction), indent=2))
    else:
        print(json.dumps(build(directory, '--correction-only' in sys.argv), indent=2))
