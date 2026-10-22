const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),cp=require('node:child_process');
const ts=require('./Visual/node_modules/typescript');
const root=path.resolve(__dirname,'../..'),old='handoff/report-gm-desktop-r16.5/';
const files=cp.execFileSync('git',['ls-files',old],{cwd:root,encoding:'utf8'}).trim().split('\n');
for(const file of files)assert(fs.readFileSync(path.join(root,file)).equals(cp.execFileSync('git',['show','HEAD:'+file],{cwd:root})),file+' changed');
const previous=fs.readFileSync(path.join(root,old,'Visual/src/live.ts'),'utf8'),current=fs.readFileSync(path.join(__dirname,'Visual/src/live.ts'),'utf8');
function functions(source){const result={};const ast=ts.createSourceFile('live.ts',source,ts.ScriptTarget.Latest,true);function visit(node){if(ts.isFunctionDeclaration(node)&&node.name)result[node.name.text]=node.getText(ast);ts.forEachChild(node,visit);}visit(ast);return result;}
const before=functions(previous),after=functions(current),numeric=['read','cutoff','fit','parts','point','decode'];
for(const name of numeric)assert.equal(after[name],before[name],name+' must retain R16.5 leaf/transport rules');
const support=['GM-RULES.json','SETUP REPORTING FEED.py','build_setup.py','Visual/src/files.ts','Visual/src/scope.ts','Visual/src/scope-ui.ts','compact_adapters.py','review_adapters.py','Visual/src/layout.ts','Visual/src/visual.ts','Visual/src/review-order.ts','Visual/src/hierarchy-drag.ts','monthly_hover.py'];
for(const name of support)assert(fs.readFileSync(path.join(__dirname,name)).equals(fs.readFileSync(path.join(root,old,name))),name+' changed');
const result={previousR16_5TrackedFilesUnchanged:files.length,exactFunctionsPreserved:numeric,exactSupportingFilesPreserved:support,companyDataRepaired:false};
fs.writeFileSync(path.join(__dirname,'VALIDATION-PRESERVATION.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
