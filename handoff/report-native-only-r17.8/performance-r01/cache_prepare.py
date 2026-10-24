"""Prepare a local serving experiment from ACTUAL calculated SAMPLE exports.

No fixture amount generator or expected-result oracle is used here. Preserve
the source/sector/component missing-cell rule before making a wide monthly
table and complete-history per-series regression statistics. Converted FX and
unsupported channels stay on the original query path in the model adapter.
"""
from pathlib import Path
import json
import math
import time

import numpy as np
import pandas as pd

import export_sample

METRICS=('market','abbott','pi','net','ef')
DISPLAYS=('Units','Value')
FIELDS={(m,d):m+'_'+d.lower() for m in METRICS for d in DISPLAYS}


def read(path):
    data=pd.read_csv(path,keep_default_na=False)
    data.columns=[c.removeprefix('[').removesuffix(']') for c in data.columns]
    return data


def prepare(source):
    proof=export_sample.verify(source)
    start=time.monotonic()
    facts,files,catalog=(read(source/(n+'.csv')) for n in ('facts','files','catalog'))
    facts['Amount']=pd.to_numeric(facts['Amount'],errors='coerce')
    facts['MissingCells']=pd.to_numeric(facts['MissingCells'].replace('',0),errors='raise').fillna(0)
    facts['Bad']=facts['MissingCells'].ne(0)|facts['Amount'].isna()
    if np.isinf(facts['Amount']).any() or len(files['SourceID'].unique())!=len(files):
        raise ValueError('Nonfinite values or duplicate source identities')
    groups=[]
    for metric in METRICS:
        for display in DISPLAYS:
            if metric=='ef':
                component,channel,sub='ef-ads-'+display.lower(),'*','*'
            else:
                definition=catalog[(catalog.Metric==metric)&(catalog.Display==display)]
                if len(definition)!=1:
                    raise ValueError('Unknown core catalog definition')
                row=definition.iloc[0]
                component,channel,sub=row.Component,row.Channel,row.SubChannel
            chosen=facts[facts.Component.eq(component)]
            if channel!='*':
                chosen=chosen[chosen.Channel.eq(channel)]
            if sub!='*':
                chosen=chosen[chosen.SubChannel.eq(sub)]
            grouped=chosen.groupby(['SourceID','Sector','Month'],sort=True).agg(
                Raw=('Amount','sum'),Bad=('Bad','sum'))
            groups.append(grouped.Raw.where(grouped.Bad.eq(0)).rename(FIELDS[metric,display]))
    # Do not infer a different Share numerator, denominator or channel contract.
    for display in DISPLAYS:
        rows={m:catalog[(catalog.Metric==m)&(catalog.Display==display)].iloc[0] for m in ('market','abbott','share')}
        if rows['share'].Component!=rows['abbott'].Component or rows['share'].Denominator!=rows['market'].Component or any(
            rows[m][c]!=rows['share'][c] for m in ('market','abbott') for c in ('Channel','SubChannel')):
            raise ValueError('Unknown weighted Share definition')
    wide=pd.concat(groups,axis=1).sort_index().reset_index()
    pairs=wide[['SourceID','Sector']].drop_duplicates().sort_values(['SourceID','Sector'])
    pairs['Key']=range(1,len(pairs)+1)
    wide=wide.merge(pairs,on=['SourceID','Sector'],validate='many_to_one')
    monthly=wide[['Key','Month',*FIELDS.values()]]
    prepare_ms=round((time.monotonic()-start)*1000)
    metadata=files.set_index('SourceID').to_dict('index')
    stats=[]
    for (source_id,sector),frame in wide.groupby(['SourceID','Sector'],sort=True):
        key=int(frame.Key.iloc[0])
        indexed=frame.set_index('Month')
        for metric in (*METRICS,'share'):
            cut=int(metadata[source_id]['EF' if metric=='ef' else 'IMS'])
            for display in DISPLAYS:
                for window in (6,12,24):
                    series=indexed.reindex(range(cut-window+1,cut+1))
                    values=series[FIELDS['abbott' if metric=='share' else metric,display]].to_numpy(dtype=float)
                    if metric=='share':
                        den=series[FIELDS['market',display]].to_numpy(dtype=float)
                        with np.errstate(divide='ignore',invalid='ignore'):
                            values=values/den
                    ready=bool(np.isfinite(values).all())
                    mean=slope=None
                    if ready:
                        mean=float(np.mean(values))
                        x=np.arange(window)-(window-1)/2
                        slope=float(np.dot(x,values-mean)/np.dot(x,x))
                    stats.append((key,metric,display,window,mean,slope,int(ready)))
    statistics_ms=round((time.monotonic()-start)*1000)-prepare_ms
    if not len(monthly) or len(monthly)!=len(monthly.drop_duplicates(['Key','Month'])):
        raise ValueError('Empty or duplicate monthly key')
    return {
        'dimension':list(pairs[['Key','SourceID','Sector']].itertuples(index=False,name=None)),
        'monthly':list(monthly.itertuples(index=False,name=None)),
        'statistics':stats,
        'receipt':{'SourceExportProof':proof,'Facts':len(facts),'Pairs':len(pairs),'MonthlyRows':len(monthly),
            'StatisticsRows':len(stats),'PrepareMonthlyMs':prepare_ms,'PrepareStatisticsMs':statistics_ms,
            'CompanyData':False,'Method':'Source-export facts; component/channel/subchannel grouping; invalidate any missing member per sector/month; complete-history statistics only.'}}


def literal(value,kind):
    if value is None or isinstance(value,(float,np.floating)) and math.isnan(value):
        return 'BLANK()'
    if kind=='string':
        return json.dumps(str(value),ensure_ascii=False)
    if kind=='int64':
        return str(int(value))
    if not math.isfinite(float(value)):
        raise ValueError('Nonfinite prepared amount')
    return format(float(value),'.17g')


def table(name,columns,rows):
    types={'int64':'INTEGER','string':'STRING','double':'DOUBLE'}
    expression='DATATABLE('+','.join(json.dumps(n)+','+types[k] for n,k in columns)+',{' + ','.join(
        '{'+','.join(literal(v,k) for v,(_,k) in zip(row,columns,strict=True))+'}' for row in rows)+'})'
    return {'name':name,'isHidden':True,
        'columns':[{'name':n,'dataType':k,'type':'calculatedTableColumn','sourceColumn':'['+n+']','summarizeBy':'none'} for n,k in columns],
        'partitions':[{'name':name,'mode':'import','source':{'type':'calculated','expression':expression}}]}


def tables(data):
    return [
        table('fm_cache_series',[('Key','int64'),('SourceID','string'),('Sector','string')],data['dimension']),
        table('fm_cache_monthly',[('Key','int64'),('Month','int64'),*[(n,'double') for n in FIELDS.values()]],data['monthly']),
        table('fm_cache_statistics',[('Key','int64'),('Metric','string'),('Display','string'),('Window','int64'),
            ('Mean','double'),('Slope','double'),('Ready','int64')],data['statistics'])]


if __name__=='__main__':
    import sys
    print(json.dumps(prepare(Path(sys.argv[1]))['receipt'],indent=2))
