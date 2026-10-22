"""Reduce executive-table text without changing any computed cell."""


def compact_summary(demand):
    start = demand.index('function renderSummary()')
    end = demand.index('function updateScrollNote', start)
    block = demand[start:end]
    before = 'data-period-group="${period.id}">${period.name}<small class="fm-period-range">${periodHeaderRange(period)}</small></th>'
    after = 'data-period-group="${period.id}" data-tooltip="${escape(periodHeaderRange(period))}">${period.name}</th>'
    assert block.count(before) == 1
    block = block.replace(before, after, 1)
    before = "   const caption=name+(tier&&state.tableView==='sector'?`<small class=\"fm-tier-parent\">${escape(driverNames[tier.driver])}</small>`:partial?`<small class=\"fm-tier-parent\">${subset.length} of ${sectors.filter(s=>s.driver===driver).length} tiers selected</small>`:'');"
    after = """   const context=tier?label+' – '+driverNames[tier.driver]:partial?label+' · '+subset.length+' of '+sectors.filter(s=>s.driver===driver).length+' tiers selected':label;
   const caption=tier&&state.tableView==='sector'?escape(context):name;"""
    assert block.count(before) == 1
    block = block.replace(before, after, 1)
    assert block.count('<td>${caption}</td>') == 1
    block = block.replace('<td>${caption}</td>', '<td data-tooltip="${escape(context)}"><span class="gm-compact-row-label">${caption}</span></td>', 1)
    return demand[:start] + block + demand[end:]
