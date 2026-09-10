import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import { Workbook } from '@oai/artifact-tool';

const dir = process.argv[2];
const input = `${dir}/GB10_Fan_RevB_CPL_20260909.csv`;
const output = `${dir}/GB10_Fan_RevB_CPL_JLC_20260909.csv`;
const original = await fs.readFile(input);
const source = original.toString('utf16le');
const bom = source.startsWith('\ufeff') ? '\ufeff' : '';
const lines = source.slice(bom.length).split('\r\n');
const data = lines.filter(Boolean);
assert.equal(data.length, 17);
assert(data.every(line => line.split('\t').length === 15));
const workbook = await Workbook.fromCSV(data.join('\n').replaceAll('\t', ','), {sheetName:'CPL'});
const sheet = workbook.worksheets.getItem('CPL');
console.log((await workbook.inspect({kind:'region',sheetId:'CPL',range:'A1:O17',maxChars:2200,tableMaxCols:15,tableMaxRows:3})).ndjson);
const before = sheet.getRange('A1:O17').values;
const preview = await workbook.render({sheetName:'CPL',range:'A1:L17',scale:1,format:'png'});
await fs.writeFile(`${dir}/cpl-original-preview.png`, new Uint8Array(await preview.arrayBuffer()));
const selected = new Set(['C1','D1','Q1','J1']);
const edits = [];
for (let i=1;i<before.length;i++) {
  if (!selected.has(before[i][0])) continue;
  assert.equal(String(before[i][11]), '0');
  sheet.getRange(`L${i+1}`).values = [['180']];
  edits.push({designator:before[i][0],cell:`L${i+1}`,before:'0',after:'180'});
}
assert.equal(edits.length,4);
await workbook.recalculate();
const after = sheet.getRange('A1:O17').values;
for(let i=0;i<before.length;i++) for(let j=0;j<15;j++) {
  assert.equal(String(after[i][j]), j===11 && selected.has(before[i][0]) ? '180' : String(before[i][j]));
}
// Preserve every source byte outside the four Rotation fields, including BOM,
// quoting, tabs, negative coordinates, layers and the final CRLF.
const updated = lines.map((line,i)=> {
  if(!line || i===0 || !selected.has(before[i][0])) return line;
  const fields=line.split('\t'); fields[11]='"180"'; return fields.join('\t');
}).join('\r\n');
await fs.writeFile(output, Buffer.from(bom+updated,'utf16le'));
const reread=(await fs.readFile(output)).toString('utf16le');
const reverted=reread.split('\r\n').map(line=>{
  const fields=line.split('\t');
  if(selected.has(fields[0]?.replaceAll('"',''))) fields[11]='"0"';
  return fields.join('\t');
}).join('\r\n');
assert.equal(reverted,source);
console.log((await workbook.inspect({kind:'region',sheetId:'CPL',range:'J1:M17',maxChars:1800,tableMaxRows:17,tableMaxCols:4})).ndjson);
await fs.writeFile(`${dir}/cpl-jlc-angle-audit.json`,JSON.stringify({input:input.split('/').at(-1),output:output.split('/').at(-1),edits,encoding:'UTF-16LE',delimiter:'TAB',lineEnding:'CRLF',otherBytesUnchanged:true,errors:[]},null,2)+'\n');
console.log(JSON.stringify({output,edits,otherBytesUnchanged:true}));
