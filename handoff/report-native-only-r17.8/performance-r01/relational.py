"""Separate relational monthly prototype, retaining the canonical period graph.

Keep the original facts intact. A keyed calculated copy and a small sector
index let storage aggregate members directly. Monthly source/currency admission
is unchanged; FX still converts valid source-sector members before summing.
This is a local fabricated prototype, not a company migration or RLS approval.
"""
from copy import deepcopy

import bulk_exact
import prepared
import strictcells

FACT='fm_rel_facts'
DIM='fm_rel_sectors'
KEY='SectorKey'


def column(name,kind):
    return {'name':name,'dataType':kind,'type':'calculatedTableColumn','sourceColumn':'['+name+']','summarizeBy':'none'}


def tables(database):
    original=next(t for t in database['model']['tables'] if t['name']=='fm_review_facts')
    fields=[(c['name'],c['dataType']) for c in original['columns']]
    base="SELECTCOLUMNS('fm_review_facts',"+','.join('"'+n+'",\'fm_review_facts\'['+n+']' for n,_ in fields)+')'
    expression='''VAR _base='''+base+'''
RETURN ADDCOLUMNS(_base,"SectorKey",VAR _id=[SourceRevisionID]
 VAR _gd=LOOKUPVALUE('fm_native_files'[GrowthDriver],'fm_native_files'[SourceRevisionID],_id)
 RETURN FORMAT(LEN(_gd),"0")&":"&_gd&[Sector])'''
    dimension='''DISTINCT(SELECTCOLUMNS('fm_native_scope',
 "GrowthDriver",'fm_native_scope'[GrowthDriver],"Sector",'fm_native_scope'[Sector],
 "SectorKey",FORMAT(LEN('fm_native_scope'[GrowthDriver]),"0")&":"&'fm_native_scope'[GrowthDriver]&'fm_native_scope'[Sector]))'''
    return [
        {'name':FACT,'isHidden':True,'columns':[column(n,k) for n,k in fields+[(KEY,'string')]],
         'partitions':[{'name':FACT,'mode':'import','source':{'type':'calculated','expression':expression}}]},
        {'name':DIM,'isHidden':True,'columns':[column(n,'string') for n in ('GrowthDriver','Sector',KEY)],
         'partitions':[{'name':DIM,'mode':'import','source':{'type':'calculated','expression':dimension}}]}]


def raw(converted=False):
    rate='VAR _rate=[P Rel Rate]\n' if converted else ''
    groups='''VAR _groups=SUMMARIZECOLUMNS('fm_rel_facts'[SourceRevisionID],'fm_rel_facts'[Sector],
 "Raw",SUM('fm_rel_facts'[Amount]),
 "Bad",SUMX('fm_rel_facts',INT('fm_rel_facts'[MissingCells]<>0||ISBLANK('fm_rel_facts'[Amount]))))
VAR _good=FILTER(_groups,[Bad]=0)
'''
    if converted:
        return rate+groups+'''VAR _badFX=COUNTROWS(FILTER(_good,NOT ISBLANK([Raw])&&(ISBLANK(_rate)||ISERROR([Raw]*_rate))))
RETURN IF(_badFX=0,SUMX(_good,IFERROR([Raw]*_rate,BLANK())))'''
    return groups+'RETURN SUMX(_good,[Raw])'


def monthly(original):
    if original.count('VAR _members=GENERATE(_files,')!=1:
        raise ValueError('Unknown original monthly iterator')
    prefix=original[:original.index('VAR _members=GENERATE(_files,')]
    suffix=original[original.index('VAR _available='):]
    filters='''REMOVEFILTERS('fm_rel_facts'),
 TREATAS(_scope,'fm_rel_sectors'[GrowthDriver],'fm_rel_sectors'[Sector]),
 TREATAS(_currencyIDs,'fm_rel_facts'[SourceRevisionID]),TREATAS({_date},'fm_rel_facts'[Month]),
 TREATAS({_component},'fm_rel_facts'[ComponentKey]),
 FILTER(ALL('fm_rel_facts'[Channel]),IF(_channel="*",'fm_rel_facts'[Channel] IN _selectedChannels,'fm_rel_facts'[Channel]=_channel)),
 FILTER(ALL('fm_rel_facts'[SubChannel]),IF(_sub="*",'fm_rel_facts'[SubChannel] IN _selectedSubs,COALESCE('fm_rel_facts'[SubChannel],"")=_sub))'''
    return prefix+'''
VAR _currencySet=DISTINCT(SELECTCOLUMNS(_currencies,"CC",IF(_value,[CC],"Units")))
VAR _members=GENERATE(_currencySet,
 VAR _cc=[CC]
 VAR _currencyIDs=SELECTCOLUMNS(FILTER(_files,NOT _value||
 LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],'fm_native_files'[Country])=_cc),
 "ID",'fm_native_files'[SourceRevisionID])
 VAR _raw=CALCULATE([P Rel Raw Amount],'''+filters+''')
 VAR _amount=IF(_convert,CALCULATE([P Rel Converted Amount],'''+filters+''',
 TREATAS({_cc},'fm_native_currency_map'[Currency])),_raw)
 RETURN FILTER(ROW("Amount",_amount,"FXMissing",INT(_convert&&NOT ISBLANK(_raw)&&ISBLANK(_amount)),
 "SourceCurrency",_cc),NOT ISBLANK(_raw)))
'''+suffix


def patch(database):
    fixed=deepcopy(database);old=prepared.adapter.planning.measures(database)
    current=prepared.adapter.planning.measures(fixed)
    expected=prepared.adapter.planning.measures(strictcells.patch(
        prepared.adapter.patch_database(prepared.adapter.selection.original_database())[0]))
    text=prepared.adapter.selection.OLD.expression_text
    if any(t['name'] in {FACT,DIM} for t in fixed['model']['tables']):
        raise ValueError('Relational prototype already installed')
    for n in ('N Monthly Numerator','N Monthly Denominator'):
        if text(old[n]['expression'])!=text(expected[n]['expression']):
            raise ValueError('Unknown R03 monthly kernel')
    fixed['model']['tables'].extend(tables(database))
    fixed['model']['relationships'].append({'name':'Rel-Fact-Sector','fromTable':FACT,'fromColumn':KEY,
        'toTable':DIM,'toColumn':KEY,'crossFilteringBehavior':'oneDirection'})
    target=next(t for t in fixed['model']['tables'] if t['name']=='fm_native_measures')['measures']
    target.extend({'name':n,'expression':e,'isHidden':True} for n,e in [
        ('P Rel Raw Amount',raw()),('P Rel Converted Amount',raw(True)),
        ('P Rel Rate',"VAR _cc=SELECTEDVALUE('fm_native_currency_map'[Currency])\n"+
         "VAR _fx=FILTER(CALCULATETABLE('fm_native_state',ALLEXCEPT('fm_native_state','fm_native_state'[Token])),'fm_native_state'[Kind]=\"fx\")\n"+bulk_exact.rate('_cc'))])
    for n in ('N Monthly Numerator','N Monthly Denominator'):
        current[n]['expression']=monthly(text(old[n]['expression']))
    return fixed
