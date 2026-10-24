// Presentation only. Values arrive from the existing semantic chart measure.
export type Point = { month: number; value: number };
export type Band = { id: string; start: number; end: number };
export type Series = { id: string; scope: string; colorKey: string; kind: number; points: Point[];
    cycle: string; cutoff: number; periods: Band[] };
export type Feed = { series: Series[]; ratio: boolean; display: string; unit: string };
const NS = 'http://www.w3.org/2000/svg';

function calendarMonth(raw: string): number {
    if (typeof raw !== 'string' || !/^\d{4}-(0[1-9]|1[0-2])$/.test(raw)) throw Error('Invalid chart calendar metadata.');
    return Number(raw.slice(0, 4)) * 12 + Number(raw.slice(5, 7)) - 1;
}

export function decode(table: any): Feed {
    const index = (role: string) => table.columns.findIndex((c: any) => c.roles?.[role]);
    const roles = ['Month', 'Series', 'Scope', 'Kind', 'Value', 'Context'];
    const ids = Object.fromEntries(roles.map(r => [r, index(r)]));
    if (roles.some(r => ids[r] < 0)) throw Error('The chart fields are incomplete.');
    const series = new Map<string, Series>();
    const contexts = new Map<string, any>();
    let ratio = false, display = 'Units', unit = '', metricSignature = '';
    for (const row of table.rows) {
        const raw = row[ids.Value];
        if (raw === null || raw === undefined) continue;
        if (typeof raw !== 'number') throw Error('Non-numeric chart point.');
        const value = raw, rawDate = row[ids.Month];
        if (rawDate === null || rawDate === undefined) throw Error('Missing chart month.');
        const date = rawDate instanceof Date ? rawDate : new Date(rawDate);
        if (!Number.isFinite(value) || !Number.isFinite(date.getTime())) throw Error('Invalid chart point.');
        // Power BI DateTime is a client wall-clock calendar value. A BST
        // April boundary can be March 31 at 23:00Z on the wire (R16.6 contract).
        const month = date.getFullYear() * 12 + date.getMonth();
        const id = row[ids.Series], scope = row[ids.Scope];
        const kind = Number(row[ids.Kind]);
        if (typeof id !== 'string' || !id || typeof scope !== 'string' || !scope || ![0, 1, 6, 12, 24].includes(kind)) throw Error('Invalid chart series.');
        const wire = row[ids.Context];
        if (typeof wire !== 'string') throw Error('Missing chart context; partial annotation withheld.');
        if (!contexts.has(wire)) {
            const context = JSON.parse(wire);
            if (!Array.isArray(context.periods) || !['Units', 'Value'].includes(context.display) ||
                typeof context.metric !== 'string' || typeof context.unit !== 'string' ||
                !/^\d{4}-\d{2}$/.test(context.cycle)) throw Error('Invalid chart context.');
            contexts.set(wire, { ...context, cutoff: calendarMonth(context.cutoff),
                periods: context.periods.map((p: any) => ({ id: String(p.id), start: calendarMonth(p.start), end: calendarMonth(p.end) })) });
        }
        const context = contexts.get(wire), signature = JSON.stringify([context.metric, context.display, context.unit]);
        if (metricSignature && metricSignature !== signature) throw Error('Mixed measure contexts; chart withheld.');
        metricSignature = signature; ratio = context.metric === 'share'; display = context.display; unit = context.unit;
        if (context.periods.some((p: Band) => p.start > p.end)) throw Error('Invalid selected period.');
        if (!series.has(id)) series.set(id, { id, scope, colorKey: scope, kind, points: [], cycle: context.cycle,
            cutoff: context.cutoff, periods: context.periods });
        const line = series.get(id)!;
        if (line.scope !== scope || line.kind !== kind || line.cycle !== context.cycle || line.cutoff !== context.cutoff ||
            JSON.stringify(line.periods) !== JSON.stringify(context.periods)) throw Error('Conflicting series context; chart withheld.');
        const duplicate = line.points.find(p => p.month === month);
        if (duplicate && duplicate.value !== value) throw Error('Conflicting series/month points; chart withheld.');
        if (!duplicate) line.points.push({ month, value });
    }
    for (const line of series.values()) {
        line.points.sort((a, b) => a.month - b.month);
        if (new Set(line.points.map(p => p.month)).size !== line.points.length)
            throw Error('Duplicate series/month points; chart withheld.');
    }
    const lines = [...series.values()];
    if (new Set(lines.map(s => s.cycle)).size > 1) for (const line of lines) line.scope += ' · ' + line.cycle;
    return { series: lines, ratio, display, unit };
}

export function format(value: number, ratio = false, raw = false): string {
    if (ratio) return (value * 100).toLocaleString('en-GB', { maximumFractionDigits: raw ? 4 : 1 }) + '%';
    const abs = Math.abs(value), scale = raw ? 1 : abs >= 1e6 ? 1e6 : abs >= 1e3 ? 1e3 : 1;
    return (value / scale).toLocaleString('en-GB', { maximumFractionDigits: raw ? 4 : 2 }) +
        (scale === 1e6 ? 'm' : scale === 1e3 ? 'k' : '');
}

export function monthLabel(month: number): string {
    return new Date(Date.UTC(Math.floor(month / 12), month % 12, 1))
        .toLocaleDateString('en-GB', { month: 'short', year: 'numeric', timeZone: 'UTC' });
}

function element(tag: string, attrs: Record<string, string | number> = {}, text?: string): SVGElement {
    const node = document.createElementNS(NS, tag);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
    if (text !== undefined) node.textContent = text;
    return node;
}

export class Chart {
    private root: HTMLElement;
    constructor(container: HTMLElement) {
        this.root = document.createElement('div'); this.root.className = 'fm-overlay';
        container.append(this.root);
    }
    message(text: string) { this.root.replaceChildren(); this.root.textContent = text; }
    draw(feed: Feed, width: number, height: number) {
        this.root.replaceChildren();
        this.root.style.width = width + 'px'; this.root.style.height = height + 'px';
        if (!feed.series.length) { this.message('Select a saved file and a compatible measure.'); return; }
        const scopes = [...new Set(feed.series.map(s => s.scope))].sort();
        // Stable identity across filter changes. Severity red/amber/green is
        // reserved for table exceptions, rather than categorical chart colours.
        const actual = ['#0F766E', '#4338CA', '#475569', '#7E22CE', '#075985', '#86198F', '#155E75', '#3730A3'];
        const forecast = ['#2563EB', '#8B5CF6', '#0891B2', '#C026D3', '#6366F1', '#9333EA', '#4F46E5', '#0284C7'];
        const keys = new Map(feed.series.map(s => [s.scope, s.colorKey]));
        const color = (scope: string, kind = 0) => {
            const identity = keys.get(scope) || scope;
            let hash = 0; for (let i = 0; i < identity.length; i++) hash = (Math.imul(hash, 31) + identity.charCodeAt(i)) >>> 0;
            const index = identity === 'Selected total' ? 0 : hash % actual.length;
            return (kind === 1 ? forecast : actual)[index];
        };
        const tools = document.createElement('div'); tools.className = 'fm-overlay-tools';
        const search = document.createElement('input'); search.placeholder = 'Highlight a sector or driver';
        search.setAttribute('aria-label', search.placeholder);
        if (width < 520) { search.placeholder = 'Highlight'; search.style.width = '85px'; }
        const count = document.createElement('span'); count.textContent = scopes.length === 1 ? scopes[0] : scopes.length + ' selected';
        count.className = 'fm-overlay-count'; count.title = count.textContent;
        const key = document.createElement('span'); key.className = 'fm-overlay-key';
        for (const [label, kind] of [['Actual', 0], ['Forecast', 1],
            [[...new Set(feed.series.filter(s => s.kind > 1).map(s => s.kind + 'M trend'))].join(', '), 12]] as [string, number][]) {
            const item = document.createElement('span'), swatch = document.createElement('i');
            swatch.style.borderColor = color(scopes[0], kind); swatch.style.borderTopStyle = kind > 1 ? 'dashed' : 'solid';
            item.append(swatch, document.createTextNode(label)); key.append(item);
        }
        if (scopes.length > 1) tools.append(search);
        tools.append(count, key); this.root.append(tools);
        const legend = document.createElement('div'); legend.className = 'fm-overlay-legend';
        const plot = document.createElement('div'); plot.className = 'fm-overlay-plot';
        const plotHeight = Math.max(110, height - (scopes.length > 1 ? 76 : 30)), m = { l: 64, r: 14, t: 18, b: 30 };
        const prefix = ({ GBP: '£', USD: '$', EUR: '€' } as Record<string, string>)[feed.unit] || '';
        const number = (value: number, raw = false) => prefix + format(value, feed.ratio, raw);
        let minMonth = Infinity, maxMonth = -Infinity, lo = Infinity, hi = -Infinity;
        for (const line of feed.series) for (const p of line.points) {
            minMonth = Math.min(minMonth, p.month); maxMonth = Math.max(maxMonth, p.month);
            lo = Math.min(lo, p.value); hi = Math.max(hi, p.value);
        }
        const pad = Math.max((hi - lo) * .12, Math.abs(hi) * .04, hi === 0 ? 1 : 0);
        lo -= pad; hi += pad;
        const x = (month: number) => m.l + (month - minMonth) / Math.max(1, maxMonth - minMonth) * (width - m.l - m.r);
        const y = (value: number) => plotHeight - m.b - (value - lo) / (hi - lo || 1) * (plotHeight - m.t - m.b);
        const svg = element('svg', { viewBox: `0 0 ${width} ${plotHeight}`, role: 'img',
            'aria-label': `${scopes.length} selected scopes, actual, forecast and trend overlay` });
        const title = element('title', {}, 'Monthly comparison for every selected scope'); svg.append(title);
        const bands = new Set<string>();
        for (const line of feed.series) for (const period of line.periods) {
            const start = Math.max(minMonth, period.start - .5), end = Math.min(maxMonth, period.end + .5);
            const key = start + '|' + end;
            if (end <= start || bands.has(key)) continue; bands.add(key);
            const band = element('rect', { x: x(start), y: m.t, width: x(end) - x(start), height: plotHeight - m.t - m.b,
                fill: '#b8d5e2', 'fill-opacity': '.13', 'data-review-period': period.id });
            band.append(element('title', {}, period.id)); svg.append(band);
        }
        for (let i = 0; i <= 4; i++) {
            const value = lo + (hi - lo) * i / 4, py = y(value);
            svg.append(element('line', { x1: m.l, x2: width - m.r, y1: py, y2: py, stroke: '#e8edf1' }),
                element('text', { x: m.l - 8, y: py + 4, 'text-anchor': 'end' }, number(value)));
        }
        const tickCount = width < 600 ? 4 : 7;
        for (const index of new Set(Array.from({ length: tickCount }, (_, i) =>
            Math.round(i * (maxMonth - minMonth) / (tickCount - 1))))) {
            const month = minMonth + index;
            svg.append(element('text', { x: x(month), y: plotHeight - 8, 'text-anchor':
                month === minMonth ? 'start' : month === maxMonth ? 'end' : 'middle' }, monthLabel(month)));
        }
        const marks = element('g'); svg.append(marks);
        const cutoffs = [...new Set(feed.series.map(s => s.cutoff))];
        for (const [i, cutoff] of cutoffs.entries()) if (cutoff >= minMonth && cutoff < maxMonth) {
            const px = x(cutoff + .5);
            svg.append(element('line', { x1: px, x2: px, y1: m.t, y2: plotHeight - m.b,
                stroke: '#60758a', 'stroke-width': '1', 'stroke-dasharray': '4 4', 'data-actuals-cutoff': cutoff }),
                element('text', { x: Math.min(width - 145, px + 5), y: m.t + 10 + (i % 3) * 13,
                    'paint-order': 'stroke', stroke: '#fff', 'stroke-width': 3 }, 'Actuals through ' + monthLabel(cutoff)));
        }
        const paths: { scope: string; path: SVGElement }[] = [];
        for (const line of feed.series) {
            let last = -Infinity, path = '';
            for (const p of line.points) { path += (p.month === last + 1 ? 'L' : 'M') + x(p.month).toFixed(2) + ',' + y(p.value).toFixed(2); last = p.month; }
            const node = element('path', { d: path, fill: 'none', stroke: color(line.scope, line.kind),
                'stroke-width': scopes.length > 10 ? 1.2 : 1.8, 'stroke-dasharray': line.kind > 1 ? '7 4' : '',
                'data-series': line.id, 'data-scope': line.scope, 'data-kind': line.kind,
                'data-points': line.points.length });
            marks.append(node); paths.push({ scope: line.scope, path: node });
        }
        let focused = new Set<string>(), pinned = false;
        const focus = (selected: string[]) => {
            focused = new Set(selected);
            for (const p of paths) {
                p.path.setAttribute('opacity', focused.size && !focused.has(p.scope) ? '.13' : '1');
                p.path.setAttribute('stroke-width', focused.has(p.scope) ? '3' : scopes.length > 10 ? '1.2' : '1.8');
            }
            for (const button of Array.from(legend.querySelectorAll('button')))
                button.setAttribute('aria-pressed', String(focused.has(button.dataset.scope!)));
        };
        for (const scope of scopes) {
            const button = document.createElement('button'); button.type = 'button'; button.textContent = scope;
            button.dataset.scope = scope; button.style.borderBottomColor = color(scope); button.setAttribute('aria-pressed', 'false');
            button.addEventListener('click', () => focus(focused.size === 1 && focused.has(scope) ? [] : [scope])); legend.append(button);
        }
        search.addEventListener('input', () => {
            const matches = search.value ? scopes.filter(s => s.toLocaleLowerCase().includes(search.value.toLocaleLowerCase())) : [];
            focus(matches);
            const target = Array.from(legend.querySelectorAll('button')).find(b => b.dataset.scope === matches[0]);
            target?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
        });
        const guide = element('line', { stroke: '#60758a', 'stroke-width': 1, visibility: 'hidden' }); svg.append(guide);
        const hit = element('rect', { x: m.l, y: m.t, width: width - m.l - m.r,
            height: plotHeight - m.t - m.b, fill: 'transparent', tabindex: '0', role: 'button',
            'aria-label': 'Monthly values. Arrow keys move month; Enter pins details; Escape clears highlight.' }); svg.append(hit);
        const tip = document.createElement('div'); tip.className = 'fm-overlay-tooltip'; tip.hidden = true;
        let current = minMonth;
        const show = (month: number) => {
            current = month; tip.replaceChildren(); tip.hidden = false;
            guide.setAttribute('visibility', 'visible'); guide.setAttribute('x1', String(x(month))); guide.setAttribute('x2', String(x(month)));
            guide.setAttribute('y1', String(m.t)); guide.setAttribute('y2', String(plotHeight - m.b));
            const heading = document.createElement('strong'); heading.textContent = monthLabel(month) + (pinned ? ' · pinned' : ' · click to pin'); tip.append(heading);
            for (const scope of scopes.filter(s => !focused.size || focused.has(s))) {
                const values = feed.series.filter(s => s.scope === scope).flatMap(s => {
                    const p = s.points.find(p => p.month === month);
                    return p ? [(s.kind === 0 ? 'Actual' : s.kind === 1 ? 'Forecast' : s.kind + 'M trend') + ' ' + number(p.value, true)] : [];
                });
                if (!values.length) continue;
                const row = document.createElement('div'); row.textContent = scope + ' · ' + values.join(' · '); tip.append(row);
            }
        };
        hit.addEventListener('pointermove', (event: PointerEvent) => {
            if (pinned) return; const box = svg.getBoundingClientRect();
            const px = (event.clientX - box.left) * width / box.width;
            show(Math.max(minMonth, Math.min(maxMonth, Math.round(minMonth + (px - m.l) / (width - m.l - m.r) * (maxMonth - minMonth)))));
        });
        hit.addEventListener('pointerleave', () => { if (!pinned) { tip.hidden = true; guide.setAttribute('visibility', 'hidden'); } });
        hit.addEventListener('click', () => { pinned = !pinned; show(current); });
        hit.addEventListener('keydown', (event: KeyboardEvent) => {
            if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') { event.preventDefault(); show(Math.max(minMonth, Math.min(maxMonth, current + (event.key === 'ArrowRight' ? 1 : -1)))); }
            if (event.key === 'Enter') { pinned = !pinned; show(current); }
            if (event.key === 'Escape') { pinned = false; search.value = ''; focus([]); tip.hidden = true; guide.setAttribute('visibility', 'hidden'); }
        });
        plot.append(svg, tip); this.root.append(plot);
        if (scopes.length > 1) this.root.append(legend);
    }
}
