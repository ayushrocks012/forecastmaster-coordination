// Convert the approved HTML render assignments into sanitized DOM replacement.
const fs=require('fs'),ts=require('./Visual/node_modules/typescript');
const file=__dirname+'/Visual/src/engine.ts',text=fs.readFileSync(file,'utf8');
const tree=ts.createSourceFile(file,text,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS),edits=[];
function walk(node){
 if(ts.isBinaryExpression(node)&&node.operatorToken.kind===ts.SyntaxKind.EqualsToken&&ts.isPropertyAccessExpression(node.left)&&node.left.name.text==='innerHTML'){
  edits.push([node.getStart(tree),node.end,'setHTML('+node.left.expression.getText(tree)+','+node.right.getText(tree)+')']);return;
 }
 ts.forEachChild(node,walk);
}
walk(tree);let result=text;for(const [a,b,value] of edits.sort((a,b)=>b[0]-a[0]))result=result.slice(0,a)+value+result.slice(b);
fs.writeFileSync(file,result);process.stdout.write('Sanitized '+edits.length+' DOM render assignments.\n');
