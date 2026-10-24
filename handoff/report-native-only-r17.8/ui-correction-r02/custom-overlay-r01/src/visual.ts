import powerbi from 'powerbi-visuals-api';
import { Chart, decode } from './chart';
import '../style/visual.less';

export class Visual implements powerbi.extensibility.visual.IVisual {
    private chart: Chart;
    private host: powerbi.extensibility.visual.IVisualHost;
    constructor(options: powerbi.extensibility.visual.VisualConstructorOptions) {
        this.host = options.host; this.chart = new Chart(options.element);
    }
    update(options: powerbi.extensibility.visual.VisualUpdateOptions) {
        this.host.eventService?.renderingStarted(options);
        try {
            const view = options.dataViews?.[0];
            if (view?.metadata?.segment) {
                this.chart.message('Loading the complete selected comparison…');
                if (!this.host.fetchMoreData(true)) throw Error('Power BI could not return the complete chart. Partial lines are withheld.');
                return;
            }
            if (!view?.table?.columns?.length) { this.chart.message('Waiting for the selected chart data…'); return; }
            this.chart.draw(decode(view.table), Math.max(1, options.viewport.width), Math.max(1, options.viewport.height));
        } catch (error) {
            this.chart.message(String(error)); this.host.eventService?.renderingFailed(options, String(error));
        } finally { this.host.eventService?.renderingFinished(options); }
    }
    getFormattingModel() { return { cards: [] }; }
}
