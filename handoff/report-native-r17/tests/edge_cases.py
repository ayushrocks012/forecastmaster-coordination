"""Native scenarios, blank-tier plotting, classification and clean-export checks."""
import json
import math
from pathlib import Path
import sys
from native_fixture import fixture,oracle,ALL_SECTORS
from fx_cases import rate_tokens
import native_model as nm


def queries():
    base=['TREATAS({"UK"},\'fm_review_files\'[Country])','TREATAS({"2026-10"},\'fm_review_files\'[DemandCycle])',
          'TREATAS({"Units"},\'fm_native_display\'[Display])','TREATAS({"Local"},\'fm_native_currency\'[Currency])']
    q=[]
    f=base+['TREATAS({"Selected files"},\'fm_native_file_mode\'[Mode])','TREATAS({"UK-a","UK-a-review"},\'fm_review_files\'[FileLabel])','TREATAS({"2026:FY"},\'fm_review_periods\'[PeriodKey])']
    q.append(dict(name='scenarios',query="EVALUATE SUMMARIZECOLUMNS('fm_native_scenario'[Scenario],"+','.join(f)+',"Plan",[N Plan],"Visible",[N Scenario Visible])'))
    for month in [24,31,32]:
        year=2024+month//12;number=month%12+1
        filters=base+['TREATAS({"Sectors"},\'fm_native_view\'[View])','TREATAS({"Automatic ADS"},\'fm_native_file_mode\'[Mode])',
         'TREATAS({"none"},\'fm_native_state\'[Token])',f'TREATAS({{DATE({year},{number},1)}},\'fm_review_axis\'[Month])',
         'TREATAS({"demand"},\'fm_native_lines\'[Chart])','TREATAS({""},\'fm_native_lines\'[ScopeSector])','TREATAS({1},\'fm_native_lines\'[IsSector])']
        q.append(dict(name='blank-tier-'+str(month),query="EVALUATE SUMMARIZECOLUMNS('fm_native_lines'[LineKind],"+','.join(filters)+',"Amount",[N Chart Amount])'))
    # Clean export reads the raw catalogue, not the invisible presentation labels.
    for display in ('Units','Value'):
        tokens=['none']+rate_tokens('GBP',1.32)
        for row in nm.catalog_rows():
            if row['RowID'] in {'market','share','internal'}:tokens.append(f"row:{row['RowID']}:{row['Display']}:{row['ChannelRank']}:{row['SubRank']}:{row['MeasureRank']}")
        filters=[x for x in base if 'fm_native_display' not in x and 'fm_native_currency' not in x]+[
         f'TREATAS({{"{display}"}},\'fm_native_display\'[Display])','TREATAS({"USD"},\'fm_native_currency\'[Currency])',
         'TREATAS({'+','.join(json.dumps(t) for t in tokens)+'},\'fm_native_state\'[Token])','TREATAS({"2026:FY"},\'fm_review_periods\'[PeriodKey])']
        q.append(dict(name='export-'+display,query="EVALUATE SUMMARIZECOLUMNS('fm_native_catalog'[RowID],"+','.join(filters)+',"Plan",[N Export Plan],"Order",[N Export Order])'))
        # A matrix row cross-filter must not remove the independent FX tokens.
        rank=next(r['MeasureRank'] for r in nm.catalog_rows() if r['RowID']=='market')
        label='Market '+display.lower()+'\u200b'*rank
        extra=['TREATAS({"Community"},\'fm_native_rows\'[Channel])','TREATAS({'+json.dumps(label,ensure_ascii=False)+'},\'fm_native_rows\'[Measure])']
        q.append(dict(name='sop-fx-row-'+display,query='EVALUATE SUMMARIZECOLUMNS('+','.join(filters+extra)+',"Plan",[N SOP Plan])'))
    return q


if __name__=='__main__':
    root=Path(sys.argv[1])
    if len(sys.argv)==2:
        (root/'edge-queries.json').write_text(json.dumps(queries()));print('Prepared native scenario/export/plot edge cases.')
    else:
        results=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8-sig'));_,lookup=fixture();checks=0;failures=[]
        def compare(actual,expected,description):
            global checks
            checks+=1
            if expected is None:
                if actual is not None:failures.append(description+': expected missing, got '+str(actual))
            elif not isinstance(actual,(int,float)) or not math.isclose(actual,expected,rel_tol=1e-9,abs_tol=1e-8):failures.append(description+f': {actual} != {expected}')
        if len(results)!=len(queries()) or {r['name'] for r in results}!={r['name'] for r in queries()}:failures.append('Missing or duplicate edge query groups.')
        for result in results:
            name=result['name']
            if 'error' in result:failures.append(name+': '+result['error']);continue
            rows=result['rows']
            if name=='scenarios':
                found={r['fm_native_scenario[Scenario]']:r.get('[Plan]') for r in rows if r.get('[Visible]')==1}
                value=oracle(lookup,'market','Units','2026:FY',sectors=('Example A','Example B',''))
                compare(found.get('ADS'),value,'ADS scenario');compare(found.get('REVIEW_001'),value*1.1,'Reviewer scenario')
                if set(found)!={'ADS','REVIEW_001'}:failures.append('Scenarios missing or combined.')
            elif name.startswith('blank-tier-'):
                index=int(name.rsplit('-',1)[1]);found={r['fm_native_lines[LineKind]']:r['[Amount]'] for r in rows}
                actual=lookup[('UK','','market','Units',index)]
                compare(found.get(0),actual if index<=31 else None,name+' actual')
                compare(found.get(1),actual if index>31 else None,name+' forecast')
            elif name.startswith('export-'):
                display=name.split('-',1)[1];found={r['fm_native_catalog[RowID]']:r for r in rows}
                if set(found)!={'market','share','internal'}:failures.append('Clean export lost or invented selected measures.')
                for key in ('market','share','internal'):
                    expected=oracle(lookup,key,display,'2026:FY',rates={'GBP':1.32},usd=True)
                    compare(found.get(key,{}).get('[Plan]'),expected,name+' '+key)
            elif name.startswith('sop-fx-row-'):
                display=name.removeprefix('sop-fx-row-');expected=oracle(lookup,'market',display,'2026:FY',rates={'GBP':1.32},usd=True)
                compare(rows[0].get('[Plan]') if rows else None,expected,name)
        output={'Checks':checks,'Failures':failures,'Evidence':'Actual local native Power BI engine; synthetic saved-version, blank-tier, classification and export-value checks.'}
        (root/'VALIDATION-NATIVE-EDGES.json').write_text(json.dumps(output,indent=2));print(json.dumps(output,indent=2));sys.exit(bool(failures))
