"""Synthetic host feed used only to exercise the packaged visual, never a live report."""
from pathlib import Path
from zipfile import ZipFile
import json
HERE=Path(__file__).resolve().parent
bridge=json.loads((HERE.parents[1]/'design/currency-plan-review-r15/bridge-catalog.json').read_text())
columns=[{'displayName':r,'roles':{r:True}} for r in ['FileID','Month','MetricKey','Channel','SubChannel','Sector','Numerator','NumeratorMissing','FileMetadata','Bounds']]
rows=[];files=[]
for driver in ['Core Oral','Paed SIP']:
    file={'id':'fixture-'+driver,'filename':f'UK_{driver}_Bridge_Oct 26_EF-Sep 26_IMS-Aug 26_ADS.xlsm','path':f'synthetic/{driver}/ADS.xlsm','fullLabel':'SYNTHETIC TEST ONLY','affiliate':'UK','driver':driver,'profile':'Ext','cycle':'2026-10','ims':'2026-08','ef':'2026-09','status':'SYNTHETIC DEMO'}
    files.append(file)
    for sector in ['Tier One','Tier Two']:
        first=True
        for t in range(72):
            month=f'{2024+t//12}-{t%12+1:02d}'
            components=[('product-units','Community','',1000+10*t),('abbott-units','Community','',100+t),('product-value','Community','',2000+20*t),('abbott-value','Community','',500+5*t)]
            for i,b in enumerate(bridge['bindings']):
                if b['id']=='share':continue
                identity='leaf' if b['units']['measure']=='ADS Selling units' else b['id']
                amount={'abbott':100+t,'market':1000+10*t,'pi':20,'net':80+t}.get(b['id'],200+i*10+t)
                for display,mult in [('units',1),('value',5)]:components.append((f'gm-{identity}-{display}',b['channel'],b['subChannel'] or '',amount*mult))
                if identity=='leaf':
                    components.extend([('ef-ads-units',b['channel'],b['subChannel'] or '',amount),('ef-ads-value',b['channel'],b['subChannel'] or '',amount*5)])
            for component,channel,subchannel,n in components:
                rows.append([file['id'],month,component,channel,subchannel,sector,n,0,json.dumps(file) if first else None,json.dumps({'first':'2024-01','last':'2029-12'}) if first else None]);first=False
view={'table':{'columns':columns,'rows':rows},'metadata':{'objects':{'general':{'page':'demand'}}}}
package=next((HERE/'Visual/dist').glob('*.pbiviz'))
with ZipFile(package) as z:resource=json.loads(z.read('resources/ForecastMasterGMReviewR16.pbiviz.json'))
testdir=HERE/'local-test';testdir.mkdir(exist_ok=True)
(testdir/'feed.json').write_text(json.dumps(view,separators=(',',':')))
html='''<!DOCTYPE html><html><head><meta charset="utf-8"><title>Synthetic R16 package test</title><style>html,body{margin:0;background:#f5f7fa}#host{width:1440px;height:1480px}</style></head><body><div id="host"></div><script>window.powerbi={visuals:{plugins:{}}};</script><script>'''+resource['content']['js']+'''</script><script>
window.errors=[];window.hostCalls={persist:0,fetch:0,failed:[]};
window.host={persistProperties:()=>hostCalls.persist++,fetchMoreData:()=>{hostCalls.fetch++;return true;},eventService:{renderingStarted:()=>{},renderingFinished:()=>{},renderingFailed:(o,e)=>hostCalls.failed.push(e)}};
window.visual=ForecastMasterGMReviewR16.default.create({element:document.getElementById('host'),host});
</script></body></html>'''
(testdir/'index.html').write_text(html)
print('Prepared synthetic feed:',len(rows),'monthly rows')
