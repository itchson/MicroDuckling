import test from 'node:test';
import assert from 'node:assert/strict';
import {createCadMesh,cadMaterials,highlightCadMesh,disposeCadMesh,friendlyName,isShell,separation} from '../lib/robot.ts';
const part={name:'ESP32CAM',label:'ESP32CAM',color:'#111111',kind:'hardware',link:'head',bbox:[0,0,0,27,40.5,11]};
const base={positions:[0,0,0,1,0,0,1,1,0,0,1,0],indices:[0,1,2,0,2,3]};
const colored={...base,materials:[{name:'PCB',color:'#155a83',roughness:.6,metalness:0},{name:'pins',color:'#cfa956',roughness:.2,metalness:.8}],groups:[{start:0,count:3,materialIndex:0},{start:3,count:3,materialIndex:1}]};
test('creased normals preserve every triangle and material range',()=>{
  const mesh=createCadMesh(colored,part),position=mesh.geometry.getAttribute('position');
  assert.equal(mesh.geometry.index,null);assert.equal(position.count,base.indices.length);
  assert.deepEqual(mesh.geometry.groups,colored.groups);
  for(let i=0;i<base.indices.length;i++)for(let axis=0;axis<3;axis++)assert.equal(position.array[i*3+axis],base.positions[base.indices[i]*3+axis]);
  assert.deepEqual(cadMaterials(mesh).map(m=>m.color.getHexString()),['155a83','cfa956']);
  assert.equal(cadMaterials(mesh)[1].metalness,.8);disposeCadMesh(mesh);
});
test('legacy geometry still uses one material and all triangles',()=>{
  const mesh=createCadMesh(base,part);assert.equal(Array.isArray(mesh.material),false);
  assert.equal(mesh.geometry.getAttribute('position').count,6);assert.equal(cadMaterials(mesh)[0].color.getHexString(),'111111');disposeCadMesh(mesh);
});
test('selection updates every material and disposal releases each resource',()=>{
  const mesh=createCadMesh(colored,part);let disposed=0;
  mesh.geometry.addEventListener('dispose',()=>disposed++);
  for(const material of cadMaterials(mesh))material.addEventListener('dispose',()=>disposed++);
  highlightCadMesh(mesh,true);assert.ok(cadMaterials(mesh).every(m=>m.emissive.getHex()===0x914215));
  highlightCadMesh(mesh,false);assert.ok(cadMaterials(mesh).every(m=>m.emissive.getHex()===0));
  assert.deepEqual(cadMaterials(mesh).map(m=>m.color.getHexString()),['155a83','cfa956']);
  disposeCadMesh(mesh);assert.equal(disposed,3);
});
test('invalid, overlapping, missing and partial material ranges fail before display',()=>{
  for(const groups of [[{start:0,count:3,materialIndex:0}],[{start:0,count:3,materialIndex:0},{start:0,count:3,materialIndex:1}],[{start:0,count:6,materialIndex:2}],[{start:0,count:5,materialIndex:0}]])assert.throws(()=>createCadMesh({...colored,groups},part));
  assert.throws(()=>createCadMesh({...base,materials:colored.materials},part));
  assert.throws(()=>createCadMesh({...colored,materials:[{color:'#fff',roughness:NaN}]},part));
});
test('R02 electronics are named, separated, and retained in the internal view',()=>{
  assert.equal(friendlyName(part),'ESP32-CAM controller');
  for(const name of ['ESP32CAM','ServoController','OV2640Camera','CameraCradle','CameraBoardClamp','Buck_0','Buck_1'])assert.equal(isShell({...part,name}),false);
  for(const name of ['BodyScrew171','BodyNut171','HoodScrew1','FaceScrew33_125'])assert.equal(isShell({...part,name}),true);
  assert.notDeepEqual(separation({...part,name:'ESP32CAM'}).toArray(),separation({...part,name:'ServoController'}).toArray());
});
