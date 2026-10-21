/** Saved-source comparisons. A plan never borrows another source's actuals. */
export type Source = { id: string; filename: string; label: string; driver: string; cycle: string; ims?: string; ef?: string; color?: string; dash?: string };
export type Metric = { id: string; aggregation: string; cutoffFamily: string; unit: string };
export type Part = { n: number | null; d: number | null; channel: string; subchannel: string; sector: string; nm?: number; dm?: number };
export type Dimensions = { channel: string; subchannel: string; sector: string };
export type Series = { id: string; label: string; members: Source[]; errors: string[]; cycle: string; color?: string; dash?: string };
export type Components = { n: number | null; d: number | null };
export type Kind = 'plan' | 'actual' | 't12' | 't24';
export const monthIndex = (value: string): number | null => /^\d{4}-(0[1-9]|1[0-2])$/.test(value || '') ? (Number(value.slice(0, 4)) - 2023) * 12 + Number(value.slice(5)) - 1 : null;
export const monthISO = (value: number): string => `${2023 + Math.floor(value / 12)}-${String(((value % 12) + 12) % 12 + 1).padStart(2, '0')}`;
export const cutoffFor = (file: Source, metric: Metric): number | null => monthIndex((metric.cutoffFamily === 'EF' ? file.ef : file.ims) || '');

export function seriesFor(files: Source[], cycles: string[], drivers: string[]): Series[] {
    if (drivers.length <= 1) return files.map(f => ({ id: f.id, label: f.label, members: [f], errors: [], cycle: f.cycle, color: f.color, dash: f.dash }));
    return cycles.map((cycle, index) => {
        const members = files.filter(f => f.cycle === cycle), errors: string[] = [];
        for (const driver of drivers) {
            const count = members.filter(f => f.driver === driver).length;
            if (count === 0) errors.push(`Select a file for ${driver} (${cycle}).`);
            if (count > 1) errors.push(`Select one version for ${driver} (${cycle}); ${count} versions are selected.`);
        }
        return { id: `total|${cycle}`, label: `Selected drivers total · ${cycle}`, members, errors, cycle, color: ['--fm-plan', '--fm-indi', '--fm-anuja'][index % 3], dash: index > 2 ? '7 3' : undefined };
    });
}

function reported(values: (number | null | undefined)[]): number | null {
    if (values.some(v => v !== null && v !== undefined && !Number.isFinite(v))) return null;
    const numeric = values.filter((v): v is number => typeof v === 'number' && Number.isFinite(v));
    return numeric.length ? numeric.reduce((a, b) => a + b, 0) : null;
}
function completeSum(values: (number | null)[]): number | null {
    return values.length && values.every(v => v !== null && Number.isFinite(v)) ? (values as number[]).reduce((a, b) => a + b, 0) : null;
}

export class CohortMath {
    private fits = new Map<string, { a: number; b: number } | null>();
    private amountsCache = new Map<string, Components>();
    constructor(private values: Map<string, { parts?: Part[]; n?: number | null; d?: number | null }>, public metric: Metric, private dims: Dimensions) { }
    amounts(file: Source, month: number): Components {
        const key = `${file.id}|${monthISO(month)}`, cached = this.amountsCache.get(key);
        if (cached) return cached;
        const row = this.values.get(key);
        const parts = (row?.parts || (row ? [row as Part] : [])).filter(p => !row?.parts || (['channel', 'subchannel', 'sector'] as const).every(k => this.dims[k] === 'all' || this.dims[k] === p[k]));
        const value = { n: reported(parts.map(p => p.n)), d: reported(parts.map(p => p.d)) };
        this.amountsCache.set(key, value);
        return value;
    }
    raw(file: Source, month: number): number | null {
        const a = this.amounts(file, month);
        return this.metric.aggregation === 'RATIO' ? a.n === null || a.d === null || a.d === 0 ? null : a.n / a.d : a.n;
    }
    fit(file: Source, count: number): { a: number; b: number } | null {
        const key = `${file.id}|${count}`;
        if (this.fits.has(key)) return this.fits.get(key)!;
        const cutoff = cutoffFor(file, this.metric);
        let result: { a: number; b: number } | null = null;
        if (cutoff !== null) {
            const points = Array.from({ length: count }, (_, i) => ({ x: cutoff - count + 1 + i, y: this.raw(file, cutoff - count + 1 + i) }));
            if (points.every(p => p.y !== null && Number.isFinite(p.y))) {
                const mx = points.reduce((s, p) => s + p.x, 0) / count, my = points.reduce((s, p) => s + p.y!, 0) / count;
                const denominator = points.reduce((s, p) => s + (p.x - mx) ** 2, 0);
                const b = points.reduce((s, p) => s + (p.x - mx) * (p.y! - my), 0) / denominator;
                result = { a: my - b * mx, b };
            }
        }
        this.fits.set(key, result);
        return result;
    }
    components(series: Series, month: number, kind: Kind = 'plan'): Components {
        if (series.errors.length || !series.members.length) return { n: null, d: null };
        const values = series.members.map(file => {
            const cutoff = cutoffFor(file, this.metric), actual = this.amounts(file, month);
            if (cutoff === null || (kind === 'actual' && month > cutoff)) return { n: null, d: null };
            if (kind === 'plan' || kind === 'actual' || month <= cutoff) return actual;
            const fit = this.fit(file, kind === 't12' ? 12 : 24), prediction = fit ? fit.a + fit.b * month : null;
            return { n: prediction === null ? null : this.metric.aggregation === 'RATIO' ? actual.d === null ? null : prediction * actual.d : prediction, d: actual.d };
        });
        return { n: completeSum(values.map(a => a.n)), d: this.metric.aggregation === 'RATIO' ? completeSum(values.map(a => a.d)) : null };
    }
    value(series: Series, month: number, kind: Kind = 'plan'): number | null {
        const a = this.components(series, month, kind);
        return this.metric.aggregation === 'RATIO' ? a.n === null || a.d === null || a.d === 0 ? null : a.n / a.d : a.n;
    }
    total(series: Series, start: number, end: number, kind: Kind = 'plan'): number | null {
        if (end < start) return null;
        const points = Array.from({ length: end - start + 1 }, (_, i) => this.components(series, start + i, kind));
        const n = completeSum(points.map(p => p.n));
        if (this.metric.aggregation !== 'RATIO') return n;
        const d = completeSum(points.map(p => p.d));
        return n === null || d === null || d === 0 ? null : n / d;
    }
    cutoffs(series: Series): number[] { return [...new Set(series.members.map(f => cutoffFor(f, this.metric)).filter((x): x is number => x !== null))].sort((a, b) => a - b); }
    status(series: Series, month: number): 'A' | 'F' | 'M' | '?' {
        const cutoffs = series.members.map(f => cutoffFor(f, this.metric));
        if (!cutoffs.length || cutoffs.some(c => c === null)) return '?';
        return cutoffs.every(c => month <= c!) ? 'A' : cutoffs.every(c => month > c!) ? 'F' : 'M';
    }
}
