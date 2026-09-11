// SPDX-License-Identifier: Apache-2.0
// Combine the mechanical review with separately attributed component visuals.
import {readFile,writeFile,mkdir,copyFile,readdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {createHash} from 'node:crypto';
const root=fileURLToPath(new URL('../../',import.meta.url)), pub=path.join(root,'viewer/public');
const read=async p=>JSON.parse(await readFile(path.join(root,p),'utf8'));
const assembly=await read('cad/assembly.json'),p=assembly.parameters;
const forbidden=new Set(['IMU','ServoController','Buck_0','Buck_1']);
if(!assembly.public_preview||assembly.parts.some(p=>forbidden.has(p.name)))throw Error('Use the public CAD export before staging the viewer.');
const copy=async(src,dst)=>{const to=path.join(pub,dst);await mkdir(path.dirname(to),{recursive:true});await copyFile(path.join(root,src),to);};
const linkJoints={body:null,left_leg:'left_hip',right_leg:'right_hip',head:'neck_yaw',jaw:'jaw_pitch'};
const componentRecords=await read('components/records.json'),notices=await read('components/NOTICE.json');
const parts=[];
for(const part of [...assembly.parts,...componentRecords.parts]){
  if(!/^[A-Za-z0-9_][A-Za-z0-9_.-]*$/.test(part.name)||part.name.includes('..'))throw Error('Invalid CAD name');
  const extra=forbidden.has(part.name),rel=`${extra?'components':'cad'}/meshes/${part.name}.json`,mesh=await read(rel),low=[Infinity,Infinity,Infinity],high=[-Infinity,-Infinity,-Infinity];
  if(extra){const notice=notices.assets.find(n=>n.name===part.name);if(!notice||createHash('sha256').update(await readFile(path.join(root,rel))).digest('hex')!==notice.mesh_sha256)throw Error('Component visual hash/notice mismatch: '+part.name);}
  for(let i=0;i<mesh.positions.length;i++){const a=i%3;low[a]=Math.min(low[a],mesh.positions[i]);high[a]=Math.max(high[a],mesh.positions[i]);}
  await copy(rel,`cad/meshes/${part.name}.json`);
  const downloads={};
  if(['print','coupon'].includes(part.kind))for(const ext of ['stl','3mf']){
    const src=`cad/${ext}/${part.name}.${ext}`,dst=`downloads/${ext}/${part.name}.${ext}`;
    await copy(src,dst);downloads[ext]='/'+dst;
  }
  parts.push({...part,label:part.label??part.name.replace(/([a-z])([A-Z])/g,'$1 $2'),joint:linkJoints[part.link],bbox:[...low,...high],downloads});
}
const joints={
  left_hip:{label:'Left leg',origin:[0,p.leg_y,p.hip_z],axis:[0,1,0],parent:null,limits:[-p.hip_limit_deg,p.hip_limit_deg]},
  right_hip:{label:'Right leg',origin:[0,-p.leg_y,p.hip_z],axis:[0,1,0],parent:null,limits:[-p.hip_limit_deg,p.hip_limit_deg]},
  neck_yaw:{label:'Neck rotation',origin:[0,0,p.neck_pivot_z],axis:[0,0,1],parent:null,limits:[-p.neck_limit_deg,p.neck_limit_deg]},
  jaw_pitch:{label:'Mouth opening',origin:[p.jaw_pivot_x,0,p.jaw_pivot_z],axis:[0,1,0],parent:'neck_yaw',limits:[0,p.jaw_limit_deg]},
};
const out={revision:p.design_revision,variant:'Complete component preview',cad_sha256:createHash('sha256').update(await readFile(path.join(root,'cad/MicroDuckling_R05_mechanical.FCStd'))).update(await readFile(path.join(root,'components/NOTICE.json'))).digest('hex'),mass_g:assembly.mass_g,com_mm:assembly.com_mm,public_preview:assembly.public_preview,parts,joints};
await writeFile(path.join(pub,'cad/assembly.json'),JSON.stringify(out));
for(const name of ['MicroDuckling_R05_printed.step','MicroDuckling_R05_mechanical.FCStd'])await copy('cad/'+name,'downloads/'+name);
for(const name of ['assembled.png','exploded.png'])await copy('assets/renders/'+name,'renders/'+name);
await copy('assets/brand/microduckling-mascot.png','brand/microduckling-mascot.png');
await copy('simulation/browser/robot-physics.json','simulation/robot-physics.json');
await copy('components/NOTICE.json','cad/components-NOTICE.json');
for(const name of await readdir(path.join(root,'docs')))if(name.endsWith('.md'))await copy('docs/'+name,'downloads/reports/'+name);
console.log(`Prepared ${parts.length} public part records and 32 printable downloads.`);
