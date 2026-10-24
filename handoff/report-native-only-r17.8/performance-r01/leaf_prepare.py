"""Prepare exact single-source/sector period KPIs from actual sample exports.

No expected-result generator is imported. Missing months remain BLANK; known
zeros remain zero. Share uses weighted period ratios and future denominator
weights. Aggregate selections are deliberately not computed by summing Share
KPIs: their original grouped query calculation remains in the model.
"""
import math
import time

import numpy as np
import pandas as pd

import cache_prepare

METRICS=(*cache_prepare.METRICS,'share')
KINDS=('FY','YTD','YTG','H1','H2')


def field(metric,display,window):
    return metric+'_'+display.lower()+'_'+('Plan' if window==0 else 'B'+str(window))


def values(num,den,dates,cut,mean,slope,window,ratio):
    """Independent preparation arithmetic for one source/sector period."""
    if not len(dates):return None,None
    n=num.reindex(dates).to_numpy(dtype=float) if hasattr(num,'reindex') else np.asarray(num,dtype=float)
    d=(den.reindex(dates).to_numpy(dtype=float) if hasattr(den,'reindex') else np.asarray(den,dtype=float)) if ratio else None
    valid_n=bool(np.isfinite(n).all())
    valid_d=not ratio or bool(np.isfinite(d).all())
    plan=None
    if valid_n and valid_d:
        total=float(n.sum())
        plan=(total/float(d.sum()) if float(d.sum())!=0 else None) if ratio else total
    actual=dates<=cut;future=~actual
    if not valid_d or not np.isfinite(n[actual]).all() or future.any() and (mean is None or slope is None):
        return plan,None
    forecast=np.array([])
    if future.any():forecast=mean+slope*(dates[future]-cut+window-(window+1)/2)
    numerator=float(n[actual].sum())+float((forecast*d[future]).sum() if ratio else forecast.sum())
    benchmark=(numerator/float(d.sum()) if float(d.sum())!=0 else None) if ratio else numerator
    return plan,benchmark


def prepare(export):
    start=time.monotonic();monthly=cache_prepare.prepare(export)
    files=cache_prepare.read(export/'files.csv').set_index('SourceID').to_dict('index')
    frame=pd.DataFrame(monthly['monthly'],columns=['Key','Month',*cache_prepare.FIELDS.values()])
    stats={(int(k),m,d,int(w)):(mean,slope) for k,m,d,w,mean,slope,ready in monthly['statistics']}
    lo,hi=int(frame.Month.min()),int(frame.Month.max())
    years=range(2000+lo//12,2000+hi//12+1)
    dim=[];rows=[]
    columns=[field(m,d,w) for m in METRICS for d in cache_prepare.DISPLAYS for w in (0,6,12,24)]
    source_keys={int(k):(source,sector) for k,source,sector in monthly['dimension']}
    for key,group in frame.groupby('Key',sort=True):
        key=int(key);source,sector=source_keys[key];metadata=files[source]
        ims,ef=int(metadata['IMS']),int(metadata['EF'])
        dim.append((key,source,sector,ims,ef))
        indexed=group.set_index('Month').reindex(np.arange(lo,hi+1))
        arrays={n:indexed[n].to_numpy(dtype=float) for n in cache_prepare.FIELDS.values()}
        for year in years:
            for kind in KINDS:
                result=[]
                for metric in METRICS:
                    cut=ef if metric=='ef' else ims
                    month=cut%12;first=(year-2000)*12
                    lower=month+1 if kind=='YTG' else 6 if kind=='H2' else 0
                    upper=month if kind=='YTD' else 5 if kind=='H1' else 11
                    dates=np.arange(first+lower,first+upper+1)
                    for display in cache_prepare.DISPLAYS:
                        positions=dates-lo;present=(positions>=0)&(positions<=hi-lo)
                        num=np.full(len(dates),np.nan)
                        num[present]=arrays[cache_prepare.FIELDS['abbott' if metric=='share' else metric,display]][positions[present]]
                        den=np.full(len(dates),np.nan)
                        den[present]=arrays[cache_prepare.FIELDS['market',display]][positions[present]]
                        plan=None;benchmarks=[]
                        for w in (6,12,24):
                            mean,slope=stats[key,metric,display,w]
                            current,bench=values(num,den,dates,cut,mean,slope,w,metric=='share')
                            if w==6:plan=current
                            benchmarks.append(bench)
                        result.extend([plan,*benchmarks])
                rows.append((key,year,kind,*result))
    for row in rows:
        if any(v is not None and not math.isfinite(float(v)) for v in row[3:]):
            raise ValueError('Nonfinite prepared KPI')
    return {'dimension':dim,'rows':rows,'columns':columns,'minMonth':lo,'maxMonth':hi,
        'receipt':{**monthly['receipt'],'LeafRows':len(rows),'LeafSeries':len(dim),
            'YearMin':min(years),'YearMax':max(years),'LeafFields':len(columns),
            'PreparationTotalMs':round((time.monotonic()-start)*1000),
            'AggregateSharePrecomputedBySummingSectors':False,'Freshness':'Immutable fabricated source export only.'}}


def tables(data):
    return [cache_prepare.table('fm_leaf_series',[('Key','int64'),('SourceID','string'),('Sector','string'),
        ('IMS','int64'),('EF','int64')],data['dimension']),
        cache_prepare.table('fm_leaf_kpi',[('Key','int64'),('Year','int64'),('Kind','string'),
        *[(n,'double') for n in data['columns']]],data['rows'])]
