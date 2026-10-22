"""Native-engine FX and selection cases with an independent arithmetic oracle."""
import json
import math
from pathlib import Path
import sys
from native_fixture import fixture,oracle,PERIODS


def rate_tokens(currency,value):
    mantissa,exponent=format(float(value),'.17e').split('e');digits=mantissa.replace('.','')
    return [f'fx:{currency}:{i}:{int(digits[i*3:i*3+3])}' for i in range(6)]+[f'fx:{currency}:6:{int(exponent)-17}']


def cases():
    result=[]
    for countries in [('UK',),('UK','Example EUR'),('UK','Example EUR','Example USD')]:
        for rates in ({},{'GBP':0.,'EUR':0.},{'GBP':1.32,'EUR':.98}):
            tokens=['none']+[token for c,v in rates.items() for token in rate_tokens(c,v)]
            filters=["TREATAS({"+','.join(json.dumps(c) for c in countries)+"},'fm_review_files'[Country])",
                     "TREATAS({\"2026-10\"},'fm_review_files'[DemandCycle])","TREATAS({\"USD\"},'fm_native_currency'[Currency])",
                     "TREATAS({"+','.join(json.dumps(p) for p in PERIODS)+"},'fm_review_periods'[PeriodKey])",
                     "TREATAS({"+','.join(json.dumps(t) for t in tokens)+"},'fm_native_state'[Token])"]
            query="EVALUATE SUMMARIZECOLUMNS('fm_native_catalog'[RowID],'fm_native_display'[Display],'fm_review_periods'[PeriodKey],"+','.join(filters)+',"Plan",[N Plan],"Benchmark",[N Benchmark],"Nonempty sentinel",1)'
            result.append(dict(name=str(len(result)),countries=countries,rates=rates,query=query))
    return result


if __name__=='__main__':
    root=Path(sys.argv[1]);definitions=cases()
    if len(sys.argv)==2:
        (root/'fx-queries.json').write_text(json.dumps(definitions));print('Prepared',len(definitions),'native FX query groups.')
    else:
        _,lookup=fixture();results=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8-sig'));checks=0;failures=[]
        if len(results)!=len(definitions) or {r['name'] for r in results}!={r['name'] for r in definitions}:failures.append('Missing or duplicate FX query groups.')
        for group in results:
            definition=definitions[int(group['name'])]
            if 'error' in group:failures.append(group['error']);continue
            if len(group['rows'])!=18*2*len(PERIODS):failures.append(group['name']+': expected every catalogue/display/period row, including missing cells.')
            for row in group['rows']:
                key=row['fm_native_catalog[RowID]'];display=row['fm_native_display[Display]'];period=row['fm_review_periods[PeriodKey]']
                for name,window in [('Plan',0),('Benchmark',12)]:
                    expected=oracle(lookup,key,display,period,window,countries=definition['countries'],rates=definition['rates'],usd=True)
                    actual=row.get('['+name+']');checks+=1
                    if expected is None:
                        if actual is not None:failures.append(f'{group["name"]}: {key} {display} {period} {name} expected missing, got {actual}')
                    elif not isinstance(actual,(float,int)) or not math.isclose(expected,actual,rel_tol=1e-9,abs_tol=1e-8):
                        failures.append(f'{group["name"]}: {key} {display} {period} {name}: {actual} != {expected}')
        result={'Checks':checks,'Failures':failures,'Evidence':'Local native Power BI engine. Synthetic GBP/EUR/USD only; no live multi-affiliate qualification.'}
        (root/'VALIDATION-NATIVE-FX.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));sys.exit(bool(failures))
