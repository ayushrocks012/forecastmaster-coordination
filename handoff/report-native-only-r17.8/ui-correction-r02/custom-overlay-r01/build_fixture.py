"""Bind the packaged chart to a complete, fabricated native-engine result."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent


def build(source, destination):
    if destination.exists():
        raise ValueError('Use a new browser evidence folder')
    result = json.loads((source / 'results.json').read_text(encoding='utf-8-sig'))
    if len(result) != 1 or 'error' in result[0]:
        raise ValueError('Complete native feed required')
    rows = result[0]['rows']
    columns = [('Month', 'fm_review_axis[Month]'), ('Series', 'fm_native_lines[SeriesLabel]'),
        ('Scope', 'fm_native_lines[ScopeLabel]'), ('Kind', 'fm_native_lines[LineKind]'),
        ('Value', '[Value]'), ('Context', '[Context]')]
    seen, series, scopes, months, data = set(), set(), set(), set(), []
    for row in rows:
        stamp = int(re.fullmatch(r'/Date\((\d+)\)/', row[columns[0][1]])[1])
        # This task-owned native runner serialized unspecified DateTime values
        # on the Windows Europe/London host; bind that serializer explicitly.
        day = datetime.fromtimestamp(stamp / 1000, timezone.utc).astimezone(ZoneInfo('Europe/London'))
        mi = (day.year - 2023) * 12 + day.month - 1
        match = re.fullmatch(r'Sector (\d+)\.(\d+) – Driver (\d+)', row[columns[2][1]])
        if not match or match[1] != match[3]:
            raise ValueError('Unexpected fabricated scope')
        driver, sector = int(match[1]), int(match[2])
        kind = row[columns[3][1]]
        context = json.loads(row['[Context]'])
        if (context['metric'], context['display'], context['unit'], context['cutoff']) != ('market', 'Units', 'Units', '2026-08'):
            raise ValueError('Unexpected native chart context')
        periods = {p['id']: (p['start'], p['end']) for p in context['periods']}
        if periods != {'2026:FY': ('2026-01', '2026-12'), '2026:YTD': ('2026-01', '2026-08'),
                       '2026:YTG': ('2026-09', '2026-12'), '2027:FY': ('2027-01', '2027-12')}:
            raise ValueError('Native selected period boundaries differ')
        expected = 40000 + driver * 2000 + sector * 100 + mi * 150
        if kind == 1 and mi > 43:
            expected += 1500
        if not abs(row['[Value]'] - expected) < 1e-7:
            raise ValueError('Independent fabricated point comparison failed')
        if kind not in (0, 1, 12) or not (mi <= 43 if kind == 0 else mi >= 43):
            raise ValueError('Actual/forecast/trend boundary mismatch')
        key = (row[columns[1][1]], mi)
        if key in seen:
            raise ValueError('Duplicate native point')
        seen.add(key); series.add(key[0]); scopes.add(row[columns[2][1]]); months.add(mi)
        values = [row[key] for _, key in columns]; values[0] = day.astimezone(timezone.utc).isoformat()
        data.append(values)
    if (len(rows), len(series), len(scopes), len(months)) != (18900, 450, 150, 84):
        raise ValueError('Exact complete 150-sector/84-month population required')
    destination.mkdir(parents=True)
    view = {'metadata': {}, 'table': {'columns': [{'displayName': role, 'roles': {role: True}} for role, _ in columns], 'rows': data}}
    (destination / 'feed.json').write_text(json.dumps(view, ensure_ascii=False))
    package = next((HERE / 'dist').glob('*.pbiviz'))
    with ZipFile(package) as archive:
        resource = json.loads(archive.read('resources/ForecastMasterOverlayR178.pbiviz.json'))
    (destination / 'visual.js').write_text(resource['content']['js'])
    (destination / 'visual.css').write_text(resource['content']['css'])
    (destination / 'index.html').write_text('''<!doctype html><meta charset="utf-8">
<title>Fabricated chart-only qualification</title><link rel="stylesheet" href="visual.css">
<style>body{margin:0}#host{width:1400px;height:360px}</style><div id="host"></div>
<script>window.powerbi={visuals:{plugins:{}}};</script><script src="visual.js"></script><script>
window.hostCalls={fetch:0,failed:[]};window.fetchAllowed=true;
window.host={fetchMoreData:()=>{hostCalls.fetch++;return fetchAllowed;},eventService:{renderingStarted:()=>{},renderingFinished:()=>{},renderingFailed:(o,e)=>hostCalls.failed.push(e)}};
window.visual=ForecastMasterOverlayR178.default.create({element:document.getElementById('host'),host});
</script>''')
    receipt = {'Stage': 'COMPLETE_FABRICATED_NATIVE_CHART_FEED', 'Points': len(rows),
        'Series': len(series), 'Sectors': len(scopes), 'Months': len(months),
        'IndependentPointComparisons': len(rows), 'NativeQueryElapsedMs': result[0]['elapsedMs'],
        'ProductionChanged': False, 'CompanyAmounts': False,
        'SHA256': {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                   for name in ('candidate.json', 'queries.json', 'results.json')},
        'PackageSHA256': hashlib.sha256(package.read_bytes()).hexdigest()}
    (destination / 'NATIVE-FEED-VALIDATION.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt


if __name__ == '__main__':
    import sys
    print(json.dumps(build(Path(sys.argv[1]), Path(sys.argv[2])), indent=2))
