"""Use saved monthly points for hover; never interpolate business observations."""


def snap_hover(demand, sop):
    def once(source, before, after):
        assert source.count(before) == 1, "Monthly hover source anchor drifted"
        return source.replace(before, after, 1)

    demand = once(
        demand,
        "nearest=Math.round(t),index=Math.max(0,Math.min(months.length-1,Math.floor(t-months[0]))),alpha=t-months[0]-index;",
        "index=Math.max(0,Math.min(months.length-1,Math.round(t-months[0]))),nearest=months[index],snapX=x(nearest);",
    )
    demand = once(
        demand,
        'x1="${px}" x2="${px}"',
        'x1="${snapX}" x2="${snapX}"',
    )
    demand = once(
        demand,
        "const a=s.points[index],b=s.points[Math.min(index+1,s.points.length-1)];if(a?.y==null||b?.y==null)continue;const value=a.y+(b.y-a.y)*alpha;",
        "const point=s.points[index];if(point?.y==null)continue;const value=point.y;",
    )
    demand = once(demand, 'cx="${px}"', 'cx="${snapX}"')
    demand = once(
        demand,
        "rows.join('');tip.hidden=!rows.length;",
        "(rows.length?rows.join(''):'<div>No data for this month</div>');tip.hidden=false;",
    )
    sop = once(
        sop,
        "i=Math.max(0,Math.min(months.length-1,Math.floor(t-first))),a=t-first-i;",
        "i=Math.max(0,Math.min(months.length-1,Math.round(t-first))),nearest=months[i],snapX=x(nearest);",
    )
    sop = once(sop, ".attr('x1',px).attr('x2',px)", ".attr('x1',snapX).attr('x2',snapX)")
    sop = once(
        sop,
        "const one=s.points[i],two=s.points[Math.min(i+1,s.points.length-1)];if(one?.y==null||two?.y==null)continue;const value=one.y+(two.y-one.y)*a;",
        "const point=s.points[i];if(point?.y==null)continue;const value=point.y;",
    )
    sop = once(sop, ".attr('cx',px)", ".attr('cx',snapX)")
    sop = once(sop, "monthName(Math.round(t))", "monthName(nearest)")
    sop = once(
        sop,
        "entries.map(e=>'<div><span>'+esc(e.name)+'</span><span>'+fmt(e.value,e.ratio?'ratio':'amount',true)+'</span></div>').join('');tip.hidden=!entries.length;",
        "(entries.length?entries.map(e=>'<div><span>'+esc(e.name)+'</span><span>'+fmt(e.value,e.ratio?'ratio':'amount',true)+'</span></div>').join(''):'<div>No data for this month</div>');tip.hidden=false;",
    )
    return demand, sop
