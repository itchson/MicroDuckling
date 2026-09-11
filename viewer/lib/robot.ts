import * as T from 'three';
import {toCreasedNormals} from 'three/addons/utils/BufferGeometryUtils.js';
export type Part = {name:string; label:string; link:string; kind:string; color:string; mass_g:number; pcb_dimensions_mm?:number[]; note:string; joint:string|null; bbox:number[]; downloads:Record<string,string>};
export type Joint = {label:string; origin:number[]; axis:number[]; parent:string|null; limits:number[]};
export type Assembly = {revision:string; variant:string; cad_sha256:string; mass_g:number; com_mm:number[]; parts:Part[]; joints:Record<string,Joint>};
export type Mode = 'assembly'|'explode'|'grid';

export type CadMaterial={name?:string;color:string;roughness?:number;metalness?:number};
export type CadMeshData={positions:number[];indices:number[];materials?:CadMaterial[];groups?:{start:number;count:number;materialIndex:number}[]};
export function createCadMesh(data:CadMeshData,part:Pick<Part,'name'|'color'|'kind'>):T.Mesh {
  const grouped=!!data.materials?.length||!!data.groups?.length;
  const specs=grouped?data.materials:[{name:part.name,color:part.color,roughness:part.kind==='hardware'?.45:.65,metalness:part.color==='#8d9398'?.6:0}];
  if(!specs?.length||(grouped&&!data.groups?.length))throw Error('Both CAD materials and groups are required');
  for(const material of specs){
    if(!/^#[0-9a-f]{6}$/i.test(material.color))throw Error('Invalid CAD material color');
    for(const value of [material.roughness??.5,material.metalness??0])if(!Number.isFinite(value)||value<0||value>1)throw Error('Invalid CAD material property');
  }
  if(data.indices.length%3)throw Error('Incomplete CAD triangle');
  if(grouped){
    let end=0;
    for(const group of [...data.groups!].sort((a,b)=>a.start-b.start)){
      const {start,count,materialIndex}=group;
      if(![start,count,materialIndex].every(Number.isSafeInteger)||start!==end||count<=0||start%3||count%3||materialIndex<0||materialIndex>=specs.length)throw Error('Invalid CAD material group');
      end=start+count;
    }
    if(end!==data.indices.length)throw Error('CAD material groups must cover every triangle exactly once');
  }
  const raw=new T.BufferGeometry();raw.setAttribute('position',new T.Float32BufferAttribute(data.positions,3));raw.setIndex(data.indices);
  const geometry=toCreasedNormals(raw,Math.PI/6);if(geometry!==raw)raw.dispose();
  // toCreasedNormals expands the index buffer without changing triangle order.
  // Reapply element ranges explicitly, now indexing the non-indexed vertices.
  geometry.clearGroups();if(grouped)for(const g of data.groups!)geometry.addGroup(g.start,g.count,g.materialIndex);
  geometry.computeBoundingBox();
  const materials=specs.map(s=>new T.MeshStandardMaterial({name:s.name??part.name,color:s.color,roughness:s.roughness??.5,metalness:s.metalness??0,side:T.FrontSide}));
  return new T.Mesh(geometry,grouped?materials:materials[0]);
}
export function cadMaterials(mesh:T.Mesh):T.MeshStandardMaterial[] {
  return (Array.isArray(mesh.material)?mesh.material:[mesh.material]) as T.MeshStandardMaterial[];
}
export function highlightCadMesh(mesh:T.Mesh,selected:boolean) {
  for(const material of cadMaterials(mesh)){material.emissive.set(selected?0x914215:0);material.emissiveIntensity=.5;}
}
export function disposeCadMesh(mesh:T.Mesh) {
  mesh.geometry.dispose();for(const material of cadMaterials(mesh))material.dispose();
}
export function updateCameraClipping(camera:T.PerspectiveCamera,bounds:T.Box3):void {
  if(bounds.isEmpty())return;
  camera.updateMatrixWorld();
  let closest=Infinity,farthest=-Infinity;
  const point=new T.Vector3();
  for(const x of [bounds.min.x,bounds.max.x])for(const y of [bounds.min.y,bounds.max.y])for(const z of [bounds.min.z,bounds.max.z]){
    const depth=-point.set(x,y,z).applyMatrix4(camera.matrixWorldInverse).z;
    closest=Math.min(closest,depth);farthest=Math.max(farthest,depth);
  }
  // Keep the visible CAD inside the depth interval as users orbit/zoom. A fixed
  // 0.1..5000mm range loses precision on thin foil, pads and closely fitted faces.
  const near=Math.max(.02,closest*.75),far=Math.max(near+1,farthest*1.25);
  if(Math.abs(camera.near-near)>1e-5||Math.abs(camera.far-far)>1e-5){camera.near=near;camera.far=far;camera.updateProjectionMatrix();}
}
const componentNames:Record<string,string>={ESP32CAM:'ESP32-CAM controller',OV2640Camera:'OV2640 camera on flex',CameraCradle:'Adjustable camera cradle',CameraBoardClamp:'Camera board clamp',Buck_0:'Shared 5 V regulator · Pololu D24V50F5',Buck0:'Shared 5 V regulator · Pololu D24V50F5'};
export const friendlyName=(part:Pick<Part,'name'|'label'>)=>componentNames[part.name]??part.label;

export const vector = (v:number[]) => new T.Vector3(v[0],v[1],v[2]);
export function jointMatrix(id:string, joints:Assembly['joints'], angles:Record<string,number>):T.Matrix4 {
  const j=joints[id],p=vector(j.origin);
  const angle=T.MathUtils.clamp(angles[id]??0,j.limits[0],j.limits[1]);
  const m=new T.Matrix4().makeTranslation(p.x,p.y,p.z)
    .multiply(new T.Matrix4().makeRotationAxis(vector(j.axis).normalize(),T.MathUtils.degToRad(angle)))
    .multiply(new T.Matrix4().makeTranslation(-p.x,-p.y,-p.z));
  return j.parent?jointMatrix(j.parent,joints,angles).multiply(m):m;
}
export function separation(p:Part):T.Vector3 {
  const c=vector(p.bbox.slice(0,3)).add(vector(p.bbox.slice(3))).multiplyScalar(.5);
  if(p.link==='left_leg')return new T.Vector3(0,44,-8);
  if(p.link==='right_leg')return new T.Vector3(0,-44,-8);
  if(p.link==='jaw')return new T.Vector3(36,0,34);
  if(p.name==='HeadHood')return new T.Vector3(-10,0,90);
  if(['FacePanel','CameraRing'].includes(p.name)||p.name.startsWith('FaceScrew'))return new T.Vector3(60,0,50);
  if(p.name==='OV2640Camera')return new T.Vector3(82,0,55);
  if(p.name==='CameraCradle'||p.name.startsWith('CameraCradleScrew'))return new T.Vector3(48,0,68);
  if(p.name==='CameraBoardClamp'||p.name.startsWith('CameraClampScrew'))return new T.Vector3(36,-24,82);
  if(p.name==='ESP32CAM')return new T.Vector3(26,-38,68);
  if(p.name.startsWith('ServoController'))return new T.Vector3(70,0,10);
  if(/^Buck_?0/.test(p.name))return new T.Vector3(-12,30,65);
  if(/^Buck_?1/.test(p.name))return new T.Vector3(0,-55,0);
  if(p.link==='head')return new T.Vector3(0,Math.sign(c.y)*8,46);
  if(p.name.startsWith('BodyShell'))return new T.Vector3(0,Math.sign(c.y)*58,0);
  if(p.name==='Battery')return new T.Vector3(-44,0,0);
  if(p.name==='ServoLeft')return new T.Vector3(0,24,0);
  if(p.name==='ServoRight')return new T.Vector3(0,-24,0);
  if(p.name.includes('Neck')||p.name==='IMU'||p.name==='ThrustShim')return new T.Vector3(0,0,24);
  if(p.kind==='hardware')return new T.Vector3(Math.sign(c.x)*14,Math.sign(c.y)*18,4);
  return new T.Vector3();
}
export const isPrintable=(p:Part)=>p.kind==='print'||p.kind==='coupon';
export const isShell=(p:Part)=>p.name.startsWith('BodyShell')||['HeadHood','FacePanel','CameraRing','UpperBill','Jaw'].includes(p.name)||['BodyScrew','BodyNut','HoodScrew','FaceScrew'].some(prefix=>p.name.startsWith(prefix));
export function isVisible(p:Part,view:{mode:Mode;hidden:string[];onlyPrint:boolean;internals:boolean}) {
  return !view.hidden.includes(p.name)&&(!view.onlyPrint||isPrintable(p))&&(!view.internals||!isShell(p))&&(view.mode==='grid'?isPrintable(p):p.kind!=='coupon');
}
export function gridMatrix(p:Part,index:number):T.Matrix4 {
  const low=vector(p.bbox.slice(0,3)),high=vector(p.bbox.slice(3)),center=low.clone().add(high).multiplyScalar(.5);
  return new T.Matrix4().makeTranslation((index%4-1.5)*132-center.x,-Math.floor(index/4)*145-center.y,-low.z);
}
export type ViewRequest={mode?:Mode;part?:string;angles?:Record<string,number>;internals?:boolean};
export function validateViewRequest(input:unknown,data:Assembly):ViewRequest {
  if(!input||typeof input!=='object'||Array.isArray(input))throw Error('Expected an object');
  const q=input as ViewRequest;
  if(Object.keys(q).some(k=>!['mode','part','angles','internals'].includes(k)))throw Error('Unknown field');
  if(q.mode!==undefined&&!['assembly','explode','grid'].includes(q.mode))throw Error('Invalid mode');
  if(q.part!==undefined&&(typeof q.part!=='string'||!data.parts.some(p=>p.name===q.part)))throw Error('Unknown part');
  if(q.internals!==undefined&&typeof q.internals!=='boolean')throw Error('Expected boolean internals');
  if(q.angles!==undefined){
    if(!q.angles||typeof q.angles!=='object'||Array.isArray(q.angles))throw Error('Invalid angles');
    for(const [id,value] of Object.entries(q.angles)){
      const j=data.joints[id];if(!j||!Number.isFinite(value)||value<j.limits[0]||value>j.limits[1])throw Error('Joint angle outside proposed travel');
    }
  }
  if(q.mode==='grid'&&q.part&&!isPrintable(data.parts.find(p=>p.name===q.part)!))throw Error('Parts grid contains printed parts and coupons');
  if(q.part&&q.internals&&isShell(data.parts.find(p=>p.name===q.part)!))throw Error('Inside view hides the selected shell');
  return q;
}
