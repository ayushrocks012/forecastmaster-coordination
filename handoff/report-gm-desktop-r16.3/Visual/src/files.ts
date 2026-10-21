// @ts-nocheck
export function fileKey(file){return file.path?String(file.path).replace(/\\/g,'/').split('/').filter(Boolean).join('/').toLocaleLowerCase():'id:'+file.id;}
export function importedAt(file){const m=String(file.fullLabel||'').match(/ · Imported ([^·]+) · /);const t=m?Date.parse(m[1].trim()):NaN;return Number.isFinite(t)?t:0;}
export function currentFiles(files){const latest=new Map();for(const f of files){const key=fileKey(f),old=latest.get(key);if(!old||importedAt(f)>importedAt(old)||(importedAt(f)===importedAt(old)&&String(f.id).localeCompare(String(old.id))>0))latest.set(key,f);}return [...latest.values()];}
