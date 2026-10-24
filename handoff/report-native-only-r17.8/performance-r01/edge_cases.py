"""Independent scalar-cell boundary expectations using virtual fake measures."""
import prepared


def build(measures):
    cases = prepared.load('perf_edges_chart', prepared.R02 / 'chart_cases.py')
    scenarios = [('positive', 110, 100), ('negative-plan', -110, 100),
        ('negative-benchmark', 110, -100), ('both-negative', -110, -100),
        ('zero-plan', 0, 100), ('zero-benchmark', 100, 0), ('both-zero', 0, 0),
        ('blank-plan', None, 100), ('blank-benchmark', 100, None), ('both-blank', None, None)]
    requests, expected = [], {}
    def literal(value):
        return 'BLANK()' if value is None else str(value)
    for label, plan, benchmark in scenarios:
        for key in ('plan', 'variance', 'pct'):
            hkey = key
            skey = {'plan': 'plan', 'variance': '12:abs', 'pct': '12:pct'}[key]
            pair = plan is not None and benchmark is not None
            value = plan if key == 'plan' else plan-benchmark if key == 'variance' and pair else \
                (plan-benchmark)/abs(benchmark) if key == 'pct' and pair and benchmark != 0 else None
            name = 'scalar-edge/' + label + '/' + key
            # Native diagnostic: stored cells did not pick up leaf substitutions
            # in this harness. Bind the exact tested cell bodies in query scope.
            definitions = 'DEFINE\n' + '\n'.join("MEASURE 'fm_native_measures'[" + n + ']=' +
                prepared.adapter.selection.OLD.expression_text(measures[n]['expression'])
                for n in ('N Headline Cell', 'N Summary Cell')) + "\nMEASURE 'fm_native_measures'[N Plan]=" + literal(plan) + \
                "\nMEASURE 'fm_native_measures'[N Benchmark]=" + literal(benchmark) + '''
MEASURE 'fm_native_measures'[N Source OK]=1
MEASURE 'fm_native_measures'[N Period Available]=1
MEASURE 'fm_native_measures'[N Actual Only]=0
'''
            filters = [cases.tf('fm_native_metric', 'RowID', ['market']),
                cases.tf('fm_native_headline', 'Key', [hkey]), cases.tf('fm_native_columns', 'ColumnKey', [skey]),
                cases.tf('fm_native_trend', 'Window', [12]), cases.tf('fm_native_chart_trend', 'Window', [12])]
            query = definitions + 'EVALUATE CALCULATETABLE(ROW("H",[N Headline Cell],"S",[N Summary Cell]),' + ','.join(filters) + ')'
            requests.append({'name': name, 'model': 'candidate', 'query': query})
            expected[name] = {'[H]': value, '[S]': value}
    return requests, expected
