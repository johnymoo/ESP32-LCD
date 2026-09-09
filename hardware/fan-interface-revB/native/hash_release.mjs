import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
const dir=path.resolve(process.argv[2]);
async function entries(rel='') {
  const result=[];
  for(const ent of await fs.readdir(path.join(dir,rel),{withFileTypes:true})) {
    const name=path.join(rel,ent.name);
    if(ent.isDirectory()) result.push(...await entries(name));
    else if(ent.isFile() && ent.name!=='SHA256SUMS' && ent.name!=='.DS_Store') result.push(name);
  }
  return result;
}
const names=(await entries()).sort();
const lines=[];
for(const name of names) lines.push(`${createHash('sha256').update(await fs.readFile(path.join(dir,name))).digest('hex')}  ${name}`);
await fs.writeFile(path.join(dir,'SHA256SUMS'),lines.join('\n')+'\n');
console.log(`Hashed ${names.length} release files`);
