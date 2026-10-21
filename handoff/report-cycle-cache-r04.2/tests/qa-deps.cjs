const path=require('node:path');
exports.tool=name=>{
 if(process.env.FM_QA_NODE_MODULES)return require(path.join(process.env.FM_QA_NODE_MODULES,name));
 return require(name);
};
exports.browserOptions=()=>({headless:true,...(process.env.FM_QA_CHROMIUM_PATH?{executablePath:process.env.FM_QA_CHROMIUM_PATH}:{})});
