"""Reproduce the 12-case native format/export diagnostic with fabricated data only."""
from pathlib import Path
import csv
import importlib.util
import json

HERE = Path(__file__).resolve().parent


def build(out):
    spec = importlib.util.spec_from_file_location('r178_format_report', HERE / 'prepare_project.py')
    r = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(r)
    if out.exists():
        raise ValueError('Preserve earlier diagnostic attempts')
    out.mkdir(parents=True)
    rows=[(1,'positive k',585900,'amount'),(2,'negative k',-585900,'amount'),(3,'positive m',18100000,'amount'),(4,'negative m',-18100000,'amount'),(5,'small',123,'amount'),(6,'negative small',-123,'amount'),(7,'zero',0,'amount'),(8,'blank',None,'amount'),(9,'ratio',.215,'ratio'),(10,'negative ratio',-.215,'ratio'),(11,'zero ratio',0,'ratio'),(12,'blank ratio',None,'ratio')]
    def lit(v):return 'BLANK()' if v is None else json.dumps(v)if isinstance(v,str)else str(v)
    expression='DATATABLE("Sort",INTEGER,"Label",STRING,"Amount",DOUBLE,"Kind",STRING,{'+','.join('{'+','.join(lit(v)for v in row)+'}'for row in rows)+'})'
    old='''VAR _pct=SELECTEDVALUE('Cases'[Kind])="ratio" VAR _value=ABS(SELECTEDMEASURE())
    VAR _number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" & UNICHAR(34)&"m"&UNICHAR(34),_value>=1000,"#,0,.0" & UNICHAR(34)&"k"&UNICHAR(34),"#,0")
    RETURN IF(_pct,"0.0%;−0.0%;0.0%","£"&_number&";−£"&_number&";£0")'''
    format_spec = importlib.util.spec_from_file_location('r178_format_candidate', HERE / 'display_formats.py')
    formats = importlib.util.module_from_spec(format_spec)
    format_spec.loader.exec_module(formats)
    core = formats.replacements()['N Headline Cell'].split('VAR _value=', 1)[1]
    new = 'VAR _pct=SELECTEDVALUE(\'Cases\'[Kind])="ratio" VAR _row="market" VAR _symbol="£"\nVAR _value=' + core
    db={'name':'ForecastMasterNativeSyntheticFormats','compatibilityLevel':1601,'model':{'culture':'en-GB','tables':[{'name':'Cases','columns':[{'name':n,'dataType':ty,'type':'calculatedTableColumn','sourceColumn':'['+n+']',**({'sortByColumn':'Sort'}if n=='Label'else{})}for n,ty in [('Sort','int64'),('Label','string'),('Amount','double'),('Kind','string')]],'partitions':[{'name':'Cases','mode':'import','source':{'type':'calculated','expression':expression}}],'measures':[{'name':'Raw','expression':"SELECTEDVALUE('Cases'[Amount])",'formatString':'0.####'},{'name':'Current','expression':"SELECTEDVALUE('Cases'[Amount])",'formatStringDefinition':{'expression':old}},{'name':'Proposed','expression':"SELECTEDVALUE('Cases'[Amount])",'formatStringDefinition':{'expression':new}}]}]}}
    r.write(out/'FormatCheck.SemanticModel/model.bim',db);r.write(out/'FormatCheck.SemanticModel/definition.pbism',{'version':'4.2','settings':{}})
    r.write(out/'FormatCheck.Report/definition.pbir',{'version':'4.0','datasetReference':{'byPath':{'path':'../FormatCheck.SemanticModel'}}})
    r.write(out/'FormatCheck.pbip',{'version':'1.0','artifacts':[{'report':{'path':'FormatCheck.Report'}}],'settings':{'enableAutoRecovery':True}})
    root=out/'FormatCheck.Report/definition'
    r.write(root/'version.json',{'$schema':r.BASE.PP.SCHEMA+'versionMetadata/1.0.0/schema.json','version':'2.0.0'})
    r.write(root/'report.json',{'$schema':r.BASE.PP.SCHEMA+'report/3.3.0/schema.json','themeCollection':{'baseTheme':{'name':'CY24SU10','reportVersionAtImport':{'visual':'2.0.0','report':'3.0.0','page':'2.0.0'},'type':'SharedResources'}},'settings':{'useEnhancedTooltips':True}})
    r.write(root/'pages/pages.json',{'$schema':r.BASE.PP.SCHEMA+'pagesMetadata/1.0.0/schema.json','pageOrder':['formats'],'activePageName':'formats'})
    r.write(root/'pages/formats/page.json',{'$schema':r.BASE.PP.SCHEMA+'page/2.1.0/schema.json','name':'formats','displayName':'Fabricated formats','displayOption':'FitToWidth','width':1280,'height':720})
    vs=[r.BASE.text('title','Fabricated native format/export comparison',20,20,1200,50,20),r.BASE.native_table('formats',20,100,1240,550,[('Cases','Label'),('Cases','Raw',True),('Cases','Current',True),('Cases','Proposed',True)])]
    for v in vs:r.write(root/'pages/formats/visuals'/v['name']/'visual.json',v)
    r.write(out/'EXPECTED.json',{'Rows':rows,'Claim':'Only formatting; all three measures remain numeric and return identical unscaled values.'})
    (out/'FROZEN-BUILDER.py').write_text(Path(__file__).read_text())


def verify(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    expected = [('positive k',585900,'£585.9k'),('negative k',-585900,'−£585.9k'),
        ('positive m',18100000,'£18.10m'),('negative m',-18100000,'−£18.10m'),
        ('small',123,'£123'),('negative small',-123,'−£123'),('zero',0,'£0'),
        ('ratio',.215,'21.5%'),('negative ratio',-.215,'−21.5%'),('zero ratio',0,'0.0%')]
    actual = {row['Label']: row for row in rows}
    failures = []
    if set(actual) != {item[0] for item in expected} or len(rows) != len(expected):
        failures.append('Population: two all-blank cases must remain absent')
    for label, value, display in expected:
        row = actual.get(label, {})
        if row.get('Proposed') != display or float(row.get('Raw', 'nan')) != value:
            failures.append(label)
    if failures:
        raise AssertionError(failures)
    return {'NativeCSVRows': len(rows), 'BlankCasesOmitted': 2,
            'NumericValuesUnscaled': True, 'SignScalePercentZeroChecksPassed': True}


if __name__ == '__main__':
    import sys
    if sys.argv[1] == 'build':
        build(Path(sys.argv[2]))
    elif sys.argv[1] == 'verify':
        print(json.dumps(verify(Path(sys.argv[2])), indent=2))
    else:
        raise ValueError('Use build NEW_DIRECTORY or verify EXPORTED_CSV')
