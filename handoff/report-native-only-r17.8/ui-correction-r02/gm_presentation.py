"""Report-local GM presentation; no numeric model expression or format edits."""
import json
from pathlib import Path

COLORS = {'green': '#E5F2E6', 'amber': '#FFF3CD', 'red': '#F9E1E3'}
RULE = '''IF(NOT ISBLANK(_value),
 VAR _size=ABS(_value)
 RETURN SWITCH(TRUE(),_size<=0.05,"#E5F2E6",_size<=0.10,"#FFF3CD","#F9E1E3"))'''
MEASURES = {
    'N GM Review Color': '''VAR _key=SELECTEDVALUE('fm_native_headline'[Key])
RETURN IF(HASONEVALUE('fm_native_metric'[RowID])&&[N Source OK]=1&&[N Period Available]=1
 &&_key IN {"variance","pct"},
 VAR _value=[N Headline Variance %]
 RETURN ''' + RULE + ')',
    'N GM Summary Color': '''VAR _key=SELECTEDVALUE('fm_native_columns'[ColumnKey])
VAR _window=SELECTEDVALUE('fm_native_columns'[Window])
RETURN IF(HASONEVALUE('fm_native_metric'[RowID])&&HASONEVALUE('fm_native_columns'[ColumnKey])&&_key<>"plan"
 &&_window IN VALUES('fm_native_trend'[Window])&&[N Source OK]=1&&[N Period Available]=1&&[N Actual Only]<>1,
 VAR _value=CALCULATE([N Variance %],REMOVEFILTERS('fm_native_trend'),
 TREATAS({_window},'fm_native_trend'[Window]))
 RETURN ''' + RULE + ')',
}


def apply(folder: Path, report):
    extension_path = folder / 'definition/reportExtensions.json'
    extensions = json.loads(extension_path.read_text())
    entity = next(e for e in extensions['entities'] if e['name'] == 'fm_native_measures')
    existing = {m['name'] for m in entity['measures']}
    if existing.intersection(MEASURES):
        raise ValueError('Refusing duplicate presentation extension')
    entity['measures'].extend({'name': name, 'dataType': 'Text', 'expression': expression}
                              for name, expression in MEASURES.items())
    report.write(extension_path, extensions)
    root = folder / 'definition/pages/native_demand/visuals'
    for name, measure, color in [('headline', 'N Headline Cell', 'N GM Review Color'),
                                  ('executive_summary', 'N Summary Cell', 'N GM Summary Color')]:
        path = root / name / 'visual.json'
        visual = json.loads(path.read_text())
        objects = visual['visual']['objects']
        expression = report.projection('fm_native_measures', color, True)['field']
        expression['Measure']['Expression']['SourceRef']['Schema'] = 'extension'
        objects.setdefault('values', []).append({'properties': {
            'backColor': {'solid': {'color': {'expr': expression}}}},
            'selector': {'data': [{'dataViewWildcard': {'matchingOption': 0}}],
                         'metadata': 'fm_native_measures.' + measure}})
        objects['columnHeaders'][0]['properties'].update(
            backColor={'solid': {'color': report.lit('#E8EFF4')}},
            fontColor={'solid': {'color': report.lit('#17384D')}})
        for key in ('values', 'rowHeaders', 'columnHeaders'):
            objects[key][0]['properties']['fontSize'] = report.lit(11 if name == 'headline' else 10)
        report.write(path, visual)
    # Native compact key alongside each heading; it consumes no new report row.
    for name, y in [('review_variance_key', 238), ('summary_variance_key', 794)]:
        visual = report.OLD.padding(report.BASE.text(name, '', 360, y, 660, 20, 10), 0)
        paragraph = visual['visual']['objects']['general'][0]['properties']['paragraphs'][0]
        paragraph['textRuns'] = [
            {'value': 'Variance size: ', 'textStyle': {'fontFamily': 'Segoe UI', 'fontSize': '10pt', 'color': '#52677C'}},
            *[{'value': text, 'textStyle': {'fontFamily': 'Segoe UI', 'fontSize': '10pt', 'color': ink}}
              for text, ink in [('≤5%  ', '#25603C'), ('>5–10%  ', '#805500'), ('>10%', '#9A2632')]]]
        visual['position'].update(z=70, tabOrder=70 if y == 238 else 71)
        report.write(root / name / 'visual.json', visual)
    config = json.loads((folder / 'definition/report.json').read_text())
    resources = next(p for p in config['resourcePackages'] if p['name'] == 'RegisteredResources')
    theme = next(i for i in resources['items'] if i['type'] == 'CustomTheme')
    theme_path = folder / 'StaticResources/RegisteredResources' / theme['path']
    if not theme_path.is_file():
        candidates = list((folder / 'StaticResources/RegisteredResources').glob('*theme*.json'))
        if len(candidates) != 1:
            raise ValueError('Require one unambiguous local theme resource')
        theme_path = candidates[0]
    theme['path'] = theme_path.name
    report.write(folder / 'definition/report.json', config)
    data = json.loads(theme_path.read_text())
    data.update(name='ForecastMaster GM navy and teal',
                dataColors=['#0F766E', '#2563EB', '#4338CA', '#7E22CE', '#075985', '#86198F'],
                foreground='#17384D', background='#FFFFFF', tableAccent='#0F766E')
    for text in data.get('textClasses', {}).values():
        text['color'] = '#17384D'
    report.write(theme_path, data)
