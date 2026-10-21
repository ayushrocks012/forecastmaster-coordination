/** Decode the complete cycle feed once. Numeric components retain their model types. */
const roleIndex = (cols: any[], name: string) => cols.findIndex(c => c.roles?.[name]);
const safeJSON = (text: any, fallback: any) => { try { return typeof text === 'string' ? JSON.parse(text) : fallback; } catch { return fallback; } };
export const cycleKey = (value: any) => JSON.stringify([value?.affiliate || '', (value?.cycles || [value?.cycle]).filter(Boolean).slice().sort()]);

export function decode(view: any) {
    const cols = view?.table?.columns || [], rows = view?.table?.rows || [], index: any = {};
    for (const key of ['FileID', 'Month', 'Numerator', 'Denominator', 'NumeratorMissing', 'DenominatorMissing', 'FileMetadata', 'Catalog', 'Context', 'Dimensions', 'Bounds', 'Country', 'DemandCycle', 'GrowthDriver', 'SourceProfile', 'MetricKey', 'Channel', 'SubChannel', 'Sector']) index[key] = roleIndex(cols, key);
    const feed: any = { files: [], catalog: [], context: null, dimensions: [], bounds: null, values: new Map(), metricValues: new Map(), presence: new Map() };
    const ids = new Set();
    for (const row of rows) {
        const f = safeJSON(row[index.FileMetadata], null);
        if (row[index.FileMetadata] && !f) throw new Error('Incomplete FileMetadata. Partial results are not displayed.');
        if (f && !ids.has(f.id)) { feed.files.push(f); ids.add(f.id); }
        for (const [role, key] of [['Catalog', 'catalog'], ['Context', 'context'], ['Dimensions', 'dimensions'], ['Bounds', 'bounds']]) if (row[index[role]]) {
            const value = safeJSON(row[index[role]], null);
            if (value === null) throw new Error('Incomplete ' + role + ' metadata. Narrow the selected source cohort; partial results are not displayed.');
            feed[key] = value;
        }
        let date = row[index.Month];
        if (typeof date === 'number' || (typeof date === 'string' && /T.*(?:Z|[+-]\d{2}:\d{2})$/.test(date))) date = new Date(date);
        // DateTime is a wall-clock date; UTC conversion shifts month starts during BST.
        const month = date instanceof Date ? String(date.getFullYear()) + '-' + String(date.getMonth() + 1).padStart(2, '0') : String(date || '').slice(0, 7);
        const id = String(row[index.FileID] ?? ''), metric = String(row[index.MetricKey] ?? '');
        if (!id || !/^\d{4}-\d{2}$/.test(month)) continue;
        const part = { n: typeof row[index.Numerator] === 'number' ? row[index.Numerator] : null, d: typeof row[index.Denominator] === 'number' ? row[index.Denominator] : null, nm: row[index.NumeratorMissing] ?? 0, dm: row[index.DenominatorMissing] ?? 0, channel: row[index.Channel] ?? '', subchannel: row[index.SubChannel] ?? '', sector: row[index.Sector] ?? '' };
        let values = feed.metricValues.get(metric);
        if (!values) { values = new Map(); feed.metricValues.set(metric, values); }
        const key = id + '|' + month, value = values.get(key) || { parts: [] };
        value.parts.push(part); values.set(key, value);
        if (Number.isFinite(part.n) || Number.isFinite(part.d)) {
            let dimensions = feed.presence.get(id);
            if (!dimensions) { dimensions = new Map(); feed.presence.set(id, dimensions); }
            const tuple = JSON.stringify([part.channel, part.subchannel, part.sector]);
            let dim = dimensions.get(tuple);
            if (!dim) { dim = { channel: part.channel, subchannel: part.subchannel, sector: part.sector, metrics: new Map() }; dimensions.set(tuple, dim); }
            dim.metrics.set(metric, (dim.metrics.get(metric) || 0) | (Number.isFinite(part.n) ? 1 : 0) | (Number.isFinite(part.d) ? 2 : 0));
        }
    }
    if (feed.context?.schema === 5) {
        if (feed.context.complete !== true && feed.context.complete !== false) throw new Error('Cycle feed completeness is missing. Partial results are not displayed.');
    } else {
        feed.values = feed.metricValues.get(feed.context?.metric) || feed.metricValues.values().next().value || new Map();
        const availability = new Map(feed.catalog.map((m: any) => [m.availabilityIndex, m.id]));
        if (feed.context?.schema === 4) feed.dimensions = feed.dimensions.map((d: any) => ({ ...d, metrics: (d.metrics || []).map((x: any) => typeof x === 'number' ? availability.get(x) : x).filter(Boolean) }));
    }
    feed.files.sort((a: any, b: any) => a.filename.localeCompare(b.filename));
    return feed;
}

/** Same availability rule as the former DAX: reported numerator, and denominator for ratios. */
export function dimensionsFor(feed: any, files: any[]) {
    const key = JSON.stringify(files.map(f => f.id).sort());
    if (feed.lastDimensions?.key === key) return feed.lastDimensions.value;
    const dims = new Map();
    for (const file of files) for (const [tuple, source] of feed.presence.get(file.id) || []) {
        let dim = dims.get(tuple);
        if (!dim) { dim = { ...source, metrics: new Map() }; dims.set(tuple, dim); }
        for (const [metric, flags] of source.metrics) dim.metrics.set(metric, (dim.metrics.get(metric) || 0) | flags);
    }
    const value = [...dims.values()].map(d => ({ ...d, metrics: feed.catalog.filter(m => (d.metrics.get(m.id) & 1) && (m.aggregation !== 'RATIO' || (d.metrics.get(m.id) & 2))).map(m => m.id) }));
    feed.lastDimensions = { key, value };
    return value;
}
