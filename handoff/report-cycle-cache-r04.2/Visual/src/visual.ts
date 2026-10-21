import powerbi from 'powerbi-visuals-api';
import { BasicFilter } from 'powerbi-models';
import { mount } from './engine';
import '../style/visual.less';
import IVisual = powerbi.extensibility.visual.IVisual;
import VisualConstructorOptions = powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions = powerbi.extensibility.visual.VisualUpdateOptions;

const roleIndex=(cols:any[],name:string)=>cols.findIndex(c=>c.roles?.[name]);
const safeJSON=(text:any,fallback:any)=>{try{return typeof text==='string'?JSON.parse(text):fallback;}catch{return fallback;}};
export { decode } from './feed';
import { decode, cycleKey } from './feed';
export class Visual implements IVisual {
 private root:HTMLElement;private host:any;private app:any;private restored:any;private lastOptions:any;private pending=false;private audited=false;private schema=4;private wantedCycle='';
 constructor(options:VisualConstructorOptions){this.host=options.host;this.root=document.createElement('div');this.root.id='fm-review-preview';options.element.appendChild(this.root);}
 update(options:VisualUpdateOptions){
  this.lastOptions=options;this.host.eventService?.renderingStarted(options);
  try{
   const view=options.dataViews?.[0];
   if(view?.metadata?.segment){this.pending=true;if(!this.app)this.root.textContent='Loading the selected demand cycle…';const accepted=this.host.fetchMoreData(true);if(!accepted){this.reset('The monthly aggregate result exceeds the visual data limit. Select fewer demand cycles before reviewing. Partial results are not displayed.');}this.host.eventService?.renderingFinished(options);return;}
   this.pending=false;
   const feed=decode(view);this.schema=feed.context?.schema||4;if(this.app&&this.wantedCycle&&this.schema===5&&feed.context.complete&&cycleKey(feed.context)!==this.wantedCycle){this.host.eventService?.renderingFinished(options);return;}this.audit(view,feed);if(!feed.files.length||!feed.bounds||!feed.catalog.length){this.reset('Load the report model measures and the Review meeting data fields. The complete aggregate feed is required.');this.host.eventService?.renderingFinished(options);return;}
   const saved=(view?.metadata?.objects as any)?.general?.state;
   if(!this.app){this.restored=safeJSON(saved,null);this.root.replaceChildren();this.app=mount(this.root,feed,this.restored,s=>this.filter(s),s=>this.persist(s));}
   else this.app.update(feed);
   this.host.eventService?.renderingFinished(options);
  }catch(error){this.reset('Forecast review could not render: '+String(error));this.host.eventService?.renderingFailed(options,String(error));}
 }
 private reset(message:string){this.app?.destroy();this.app=undefined;this.root.textContent=message;}
 private audit(view:any,feed:any){
  if(this.audited||![...feed.values.values()].some(v=>v.parts?.some(p=>p.n!==null))||!feed.context?.metric||!feed.files.every(f=>f.status==='SYNTHETIC DEMO'))return;
  this.audited=true;const i=roleIndex(view.table.columns,'Month');const debug={version:'3.0.0.6-C3',columns:view.table.columns.map(c=>({name:c.displayName,roles:c.roles})),rows:view.table.rows.map(r=>({date:String(r[i]),type:Object.prototype.toString.call(r[i]),ym:r[i] instanceof Date?[r[i].getFullYear(),r[i].getMonth()+1,r[i].getDate()]:null,values:r.map(v=>v instanceof Date?v.toString():v)}))};
  this.host.persistProperties({merge:[{objectName:'diagnostics',selector:null,properties:{snapshot:JSON.stringify(debug)}}]});
 }
 private filter(scope:any){
  const map:any={affiliate:['fm_review_reference','Country'],cycle:['fm_review_reference','DemandCycle'],driver:['fm_review_reference','GrowthDriver'],profile:['fm_review_reference','SourceProfile'],metric:['fm_review_measures','MetricKey'],sector:['fm_review_facts','Sector'],channel:['fm_review_facts','Channel'],subchannel:['fm_review_facts','SubChannel']};
  const filters=Object.entries(map).filter(([k])=>(this.schema===5?['affiliate','cycle']:['affiliate','cycle','driver','profile','metric']).includes(k)).map(([k,[table,column]]:any)=>new BasicFilter({table,column},scope[k]==='all'?'All':'In',scope[k]==='all'?[]:k==='cycle'?scope.cycles:k==='driver'?scope.drivers:[scope[k]]).toJSON());
  if(this.schema===5)this.wantedCycle=cycleKey(scope);
  this.host.applyJsonFilter(filters,'general','selfFilter',powerbi.FilterAction.merge);
 }
 private persist(state:any){this.host.persistProperties({merge:[{objectName:'general',selector:null,properties:{state:JSON.stringify(state)}}]});}
 public getFormattingModel(){return {cards:[]};}
 public destroy(){this.app?.destroy();}
}
