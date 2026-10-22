from pathlib import Path
from zipfile import ZipFile
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from native_model import catalog_rows

root=Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=True)
here=Path(__file__).resolve().parent.parent
with ZipFile(next((here/'Controls/dist').glob('*.pbiviz'))) as z:
    resource=json.loads(z.read('resources/ForecastMasterNativeControlsR17.pbiviz.json'))
roles=['RowID','Channel','SubChannel','Measure','Display','ChannelRank','SubRank','MeasureRank']
view={'metadata':{'objects':{'general':{'variant':'sop','currencies':'GBP'}}},
      'table':{'columns':[{'displayName':r,'roles':{r:True}} for r in roles],
               'rows':[[row[r] for r in roles] for row in catalog_rows() if row['Display']=='Units']}}
(root/'controls-view.json').write_text(json.dumps(view))
html='''<!doctype html><meta charset="utf-8"><title>Synthetic control host only</title>
<div id="host" style="width:430px;height:1100px"></div><div id="fx" style="width:320px;height:180px"></div>
<script>window.powerbi={visuals:{plugins:{}}};</script><script>'''+resource['content']['js']+'''</script><script>
window.calls={filters:[],preferences:null};window.fxCalls={filters:[],preferences:null};
window.mockHost=calls=>({applyJsonFilter:f=>calls.filters.push(structuredClone(f)),persistProperties:p=>calls.preferences=p.merge[0].properties.preferences});
window.visual=ForecastMasterNativeControlsR17.default.create({element:document.getElementById('host'),host:mockHost(calls)});
window.echo=()=>visual.update({dataViews:[{...testView,metadata:{objects:{general:{variant:'sop',currencies:'GBP',preferences:calls.preferences}}}}],jsonFilters:[calls.filters.at(-1)],type:2});
</script>'''
(root/'controls.html').write_text(html)
print('Prepared metadata-only control fixture; no company figures.')
