import powerbi from 'powerbi-visuals-api';
import {decode} from './live';
import {mount} from './engine';
import '../style/visual.less';
import IVisual=powerbi.extensibility.visual.IVisual;
import VisualConstructorOptions=powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions=powerbi.extensibility.visual.VisualUpdateOptions;

export class Visual implements IVisual {
 private root:HTMLElement; private host:any; private app:any; private fingerprint=''; private rows:any;
 constructor(options:VisualConstructorOptions){this.host=options.host;this.root=document.createElement('div');this.root.style.cssText='height:100%;width:100%;overflow:auto';options.element.append(this.root);}
 update(options:VisualUpdateOptions){
  this.host.eventService?.renderingStarted(options);
  try{
   const view=options.dataViews?.[0];
   if(view?.metadata?.segment){this.app?.destroy();this.app=null;this.root.textContent='Loading the saved monthly data once…';if(!this.host.fetchMoreData(true))throw Error('The result exceeds Power BI’s complete-data limit. Narrow the report’s cycle filter; partial totals are withheld.');return;}
   if(this.app&&!(options.type&powerbi.VisualUpdateType.Data))return;
   // Include every cell so a refreshed numeric value or source revision invalidates the cache.
   let h=2166136261;for(const row of view?.table?.rows||[])for(const cell of row){const s=cell instanceof Date?String(cell.getTime()):typeof cell+':'+String(cell);for(let i=0;i<s.length;i++){h^=s.charCodeAt(i);h=Math.imul(h,16777619);}}
   const signature=(view?.table?.rows?.length||0)+':'+(h>>>0);this.rows=view?.table?.rows;
   if(this.app&&this.fingerprint===signature)return;
   const feed=decode(view);if(!feed.files.length||!feed.rows.length||!feed.bounds)throw Error('The connected model has not returned the required reporting fields. Open this project on the work laptop and sign in with your existing account.');
   const objects:any=view?.metadata?.objects;let state=null;try{state=JSON.parse(objects?.general?.state||'null');}catch{}
   state=this.app?.getState()||state;this.app?.destroy();
   const page=objects?.general?.page==='sop'?'sop':'demand';
   this.app=mount(this.root,feed,state,s=>this.host.persistProperties({merge:[{objectName:'general',selector:null,properties:{state:JSON.stringify(s)}}]}),page);
   this.fingerprint=signature;
  }catch(error){this.app?.destroy();this.app=null;this.fingerprint='';this.root.textContent='ForecastMaster: '+String(error);this.host.eventService?.renderingFailed(options,String(error));}
  finally{this.host.eventService?.renderingFinished(options);}
 }
 getFormattingModel(){return {cards:[]};}
 destroy(){this.app?.destroy();}
}
