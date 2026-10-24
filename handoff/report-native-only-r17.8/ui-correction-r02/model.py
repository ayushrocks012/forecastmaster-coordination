"""Isolated R17.8 UI correction; pure transform of the installed R01 adapter.

No source tables, dates, relationships, calculation arithmetic or formats change.
Selection admission is explicit; a cleared file selector cannot invoke ADS.
"""
from copy import deepcopy
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r178_ui_baseline', HERE.parent / 'test-release-r01/model.py')
OLD = importlib.util.module_from_spec(spec)
spec.loader.exec_module(OLD)


def original_database():
    return OLD.patch_database(OLD.original_database())[0]


def replacements():
    measures = {m['name']: m for t in original_database()['model']['tables'] for m in t.get('measures', [])}
    edits = {name: OLD.expression_text(m['expression']).replace(OLD.MODE, '"Selected files"')
             for name, m in measures.items() if OLD.MODE in OLD.expression_text(m['expression'])}
    # Demand uses the explicitly chosen source per driver, including a mixture
    # of saved scenario names across different drivers. A chart legend group
    # must not reinterpret that selection as a separate complete-source scenario.
    scenario = "COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario]))"
    for name, body in edits.items():
        edits[name] = body.replace(scenario,
            "IF(SELECTEDVALUE('fm_native_lines'[Chart])=\"demand\",BLANK()," + scenario + ")")
    # Reuse the legacy aggregate line dictionary rows, whose display labels omit
    # scenario suffixes. This selects presentation rows ONLY: the source kernels
    # above remain Selected files and still refuse an absent/ambiguous selection.
    before = '&& _mode="Selected files"'
    if edits['N Line Visible'].count(before) != 1:
        raise ValueError('Unknown line admission')
    edits['N Line Visible'] = edits['N Line Visible'].replace(before,
        '&& _mode=IF(_chart="demand","Automatic ADS","Selected files")')
    before = 'VAR _mode=SELECTEDVALUE(\'fm_native_lines\'[Mode])="Selected files"'
    if edits['N Chart Monthly'].count(before) != 1:
        raise ValueError('Unknown monthly line mode')
    edits['N Chart Monthly'] = edits['N Chart Monthly'].replace(before,
        'VAR _mode=SELECTEDVALUE(\'fm_native_lines\'[Mode])=IF(_type="demand","Automatic ADS","Selected files")')
    # The selected-source guard still refuses two versions of the same driver.
    # Remove only the presentation-dependent scenario admission around the cell.
    body = edits['N Summary Cell']
    prefix = "IF(HASONEVALUE('fm_native_scenario'[Scenario])&&SELECTEDVALUE('fm_native_scenario'[Mode])=\"Selected files\",\n"
    if not body.startswith(prefix) or not body.endswith(')'):
        raise ValueError('Unknown R01 summary guard')
    edits['N Summary Cell'] = body[len(prefix):-1]
    edits['N Source Caption'] = '''VAR _picked=ISFILTERED('fm_native_files'[FileChoiceLabel])||ISFILTERED('fm_review_files'[FileLabel])
VAR _countries=VALUES('fm_review_files'[Country])
VAR _cycles=VALUES('fm_review_files'[DemandCycle])
VAR _drivers=VALUES('fm_native_scope'[GrowthDriver])
VAR _chosen=INTERSECT(VALUES('fm_native_files'[SourceRevisionID]),VALUES('fm_review_files'[SourceRevisionID]))
VAR _files=FILTER(ALL('fm_native_files'),'fm_native_files'[SourceRevisionID] IN _chosen
 &&'fm_native_files'[Country] IN _countries&&'fm_native_files'[DemandCycle] IN _cycles
 &&'fm_native_files'[GrowthDriver] IN _drivers)
VAR _ims=MAXX(_files,'fm_native_files'[IMSActualsThrough])
VAR _ef=MAXX(_files,'fm_native_files'[ExFactoryActualsThrough])
RETURN SWITCH(TRUE(),NOT _picked,"Select saved files below",
 [N Source OK]<>1,"Select one saved version for each required growth driver",
 ISBLANK(_ims)||ISBLANK(_ef)||_ims<DATE(2000,1,1)||_ef<DATE(2000,1,1)
 ||_ims>=DATE(2100,1,1)||_ef>=DATE(2100,1,1),"Actuals cutoff metadata unavailable",
 FORMAT(COUNTROWS(_files),"0")&" selected file(s) · IMS through "&FORMAT(_ims,"mmm yy")
 &" · Ex-factory through "&FORMAT(_ef,"mmm yy"))'''
    return edits


def patch_database(database):
    expected = {m['name']: m for t in original_database()['model']['tables']
                if t['name'] == 'fm_native_measures' for m in t['measures']}
    fixed = deepcopy(database)
    tables = {t['name']: t for t in fixed['model']['tables']}
    if len(tables) != len(fixed['model']['tables']):
        raise ValueError('Duplicate tables')
    measures = tables['fm_native_measures']['measures']
    actual = {m['name']: m for m in measures}
    if len(actual) != len(measures) or set(actual) != set(expected):
        raise ValueError('Require exact installed R17.8 R01 native measure inventory')
    for name, before in expected.items():
        if OLD.expression_hash(actual[name]['expression']) != OLD.expression_hash(before['expression']):
            raise ValueError('Unknown R01 native expression: ' + name)
        for key in ('formatStringDefinition',):
            if OLD.normalized(actual[name].get(key)) != OLD.normalized(before.get(key)):
                raise ValueError('Unknown R01 numeric format')
        if actual[name].get('formatString', '') != before.get('formatString', ''):
            raise ValueError('Unknown R01 static format')
    edits = replacements()
    for name, expression in edits.items():
        actual[name]['expression'] = expression
    restored = deepcopy(fixed)
    next(t for t in restored['model']['tables'] if t['name'] == 'fm_native_measures')['measures'] = deepcopy(
        next(t for t in database['model']['tables'] if t['name'] == 'fm_native_measures')['measures'])
    if restored != database:
        raise AssertionError('Unrelated semantic metadata changed')
    return fixed, sorted(edits)
