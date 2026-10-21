const path=require('node:path'),fs=require('node:fs'),child=require('node:child_process'),esbuild=require(path.join(process.env.FM_QA_NODE_MODULES,'esbuild'));
const root=path.resolve(__dirname,'..');
async function bundle(source,name,extras={}){await esbuild.build({absWorkingDir:root,entryPoints:[source],bundle:true,nodePaths:[path.join(root,'Visual/node_modules'),process.env.FM_QA_VISUAL_NODE_MODULES].filter(Boolean),outfile:path.join(__dirname,name),...extras});}
(async()=>{
 await bundle('Visual/src/cohorts.ts','cohorts.cjs',{platform:'node',format:'cjs'});
 await bundle('Visual/src/engine.ts','engine.js',{format:'iife',globalName:'ReviewEngine'});
 await bundle('Visual/src/visual.ts','native-visual.js',{format:'iife',globalName:'NativeReview',loader:{'.less':'empty'}});
 await bundle('Visual/src/visual.ts','bridge-visual.js',{format:'iife',globalName:'NativeReview',loader:{'.less':'empty'},alias:{'powerbi-visuals-api':'./tests/powerbi-api-mock.ts'}});
 await bundle('Visual/src/feed.ts','feed.js',{format:'iife',globalName:'CycleFeed'});
 await bundle('baseline/legacy/engine.ts','legacy-engine.js',{format:'iife',globalName:'LegacyEngine'});
 for(const script of ['cohorts.test.cjs','browser.test.cjs','native_feed.test.cjs','bridge.test.cjs','cycle-cache.test.cjs','cycle-stress.test.cjs'])child.execFileSync(process.execPath,[path.join(__dirname,script)],{cwd:root,env:process.env,stdio:'inherit'});
})().catch(e=>{console.error(e);process.exit(1)});
