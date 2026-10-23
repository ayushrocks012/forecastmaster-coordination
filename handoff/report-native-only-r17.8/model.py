"""Draft R17.8 metadata/selection repair. Never writes to Fabric.

The receiving diagnostic must be reviewed before an updater is prepared.
Valid source arithmetic and every numeric format remain R17.7's definitions.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('r178_previous',HERE.parent/'report-native-only-r17.7/model.py')
OLD=importlib.util.module_from_spec(spec);spec.loader.exec_module(OLD)
expression_hash=OLD.expression_hash
PICKED="(ISFILTERED('fm_native_files'[FileChoiceLabel])||ISFILTERED('fm_review_files'[FileLabel]))"
MODE='IF('+PICKED+',"Selected files","Automatic ADS")'
OLD_MODE='SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic ADS")'
DATE_OK="COUNTROWS(FILTER(_dates,ISBLANK([Cutoff])||[Cutoff]<DATE(2000,1,1)||[Cutoff]>=DATE(2100,1,1)))=0"


def original_database():
    with ZipFile(HERE.parent/'report-native-only-r17.7/candidate/ForecastMaster Native Only R17.7 SAMPLE.zip') as z:
        return json.loads(z.read(next(p for p in z.namelist() if p.endswith('/model.bim'))))


def replacements():
    measures={m['name']:m for t in original_database()['model']['tables'] for m in t.get('measures',[])}
    result={name:m['expression'].replace(OLD_MODE,MODE) for name,m in measures.items() if OLD_MODE in m['expression']}
    for name in ('N Cutoff','N Fit Cutoff'):
        body=result[name]
        assert body.count('RETURN IF(_sourceOK &&')==1
        result[name]=body.replace('RETURN IF(_sourceOK &&','RETURN IF(_sourceOK && '+DATE_OK+' &&')
    caption=result['N Source Caption'].replace('Choose saved files below, then Apply filters','Choose saved files below')
    for table,column in (('_ims','IMSActualsThrough'),('_ef','ExFactoryActualsThrough')):
        old='FORMAT(MAXX('+table+",'fm_native_files'["+column+']),"mmm yy")'
        new='IF(MAXX('+table+",'fm_native_files'["+column+'])>=DATE(2000,1,1)&&MAXX('+table+",'fm_native_files'["+column+'])<DATE(2100,1,1),'+old+',"unavailable")'
        assert caption.count(old)==1
        caption=caption.replace(old,new)
    result['N Source Caption']='''VAR _c=[N Cutoff]
RETURN IF([N Source OK]=1&&(ISBLANK(_c)||_c<DATE(2000,1,1)||_c>=DATE(2100,1,1)),
 "Cutoff metadata unavailable · investigate source/native dates",
'''+caption+')'
    # Headline has no source-version row. Its existing complete/unique source
    # admission guard already refuses ambiguous alternative versions.
    prefix="IF(HASONEVALUE('fm_native_scenario'[Scenario]),\n"
    assert measures['N Headline Cell']['expression'].startswith(prefix)
    result['N Headline Cell']=measures['N Headline Cell']['expression'][len(prefix):-1]
    body=measures['N Summary Cell']['expression']
    assert body.startswith(prefix)
    result['N Summary Cell']=body.replace(prefix,
        "IF(HASONEVALUE('fm_native_scenario'[Scenario])&&SELECTEDVALUE('fm_native_scenario'[Mode])="+MODE+",\n",1)
    return result


def file_expression():
    table=next(t for t in original_database()['model']['tables'] if t['name']=='fm_native_files')
    before=table['partitions'][0]['source']['expression']
    old='''"FileChoiceLabel",[SourceFileName]&" | "&IF(ISBLANK([_Imported]),"Import time unavailable",
 FORMAT([_Imported],"dd MMM yyyy HH:mm:ss","en-GB")&" UTC")&" | "&[SourceRevisionID],'''
    new='''"FileChoiceLabel",VAR _name=[SourceFileName] VAR _id=[SourceRevisionID]
 VAR _stamp=IF(ISBLANK([_Imported]),"Import time unavailable",FORMAT([_Imported],"dd MMM yyyy HH:mm:ss","en-GB")&" UTC")
 VAR _same=FILTER(_ranked,[SourceFileName]=_name&&
  IF(ISBLANK([_Imported]),"Import time unavailable",FORMAT([_Imported],"dd MMM yyyy HH:mm:ss","en-GB")&" UTC")=_stamp)
 VAR _number=1+COUNTROWS(FILTER(_same,[SourceRevisionID]<_id))
 RETURN _name&" · "&_stamp&IF(COUNTROWS(_same)>1," · v"&FORMAT(_number,"0"),""),'''
    assert before.count(old)==1
    return before,before.replace(old,new)


FILE_AVAILABLE='''VAR _countries=VALUES('fm_review_files'[Country])
VAR _cycles=VALUES('fm_review_files'[DemandCycle])
VAR _drivers=VALUES('fm_native_scope'[GrowthDriver])
RETURN IF(COUNTROWS(FILTER('fm_native_files','fm_native_files'[Country] IN _countries
 &&'fm_native_files'[DemandCycle] IN _cycles&&'fm_native_files'[GrowthDriver] IN _drivers))>0,1)'''


def patch_database(database):
    before=original_database()
    expected={m['name']:m for t in before['model']['tables'] for m in t.get('measures',[]) if t['name']=='fm_native_measures'}
    fixed=deepcopy(database)
    tables={t['name']:t for t in fixed['model']['tables']}
    actual={m['name']:m for m in tables['fm_native_measures']['measures']}
    if set(actual)!=set(expected):raise ValueError('Require known R17.7 measure inventory')
    for name,old in expected.items():
        if expression_hash(actual[name]['expression'])!=expression_hash(old['expression']):raise ValueError('Unknown R17.7 expression')
        if actual[name].get('formatStringDefinition')!=old.get('formatStringDefinition'):raise ValueError('Unknown format')
    edits=replacements()
    for name,body in edits.items():actual[name]['expression']=body
    tables['fm_native_measures']['measures'].append({'name':'N File Available','expression':FILE_AVAILABLE,
        'displayFolder':'Native metadata','isHidden':True,'formatString':'0'})
    old,new=file_expression()
    source=tables['fm_native_files']['partitions'][0]['source']
    if expression_hash(source['expression'])!=expression_hash(old):raise ValueError('Unknown file helper')
    source['expression']=new
    restored=deepcopy(fixed)
    orig={t['name']:t for t in database['model']['tables']}
    for t in restored['model']['tables']:
        if t['name']=='fm_native_measures':t['measures']=deepcopy(orig[t['name']]['measures'])
        if t['name']=='fm_native_files':t['partitions']=deepcopy(orig[t['name']]['partitions'])
    if restored!=database:raise AssertionError('Unrelated metadata changed')
    return fixed,sorted(edits)+['N File Available','fm_native_files.FileChoiceLabel expression']
