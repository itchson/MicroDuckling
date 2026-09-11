import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import * as T from 'three';
import {jointMatrix,gridMatrix,isPrintable,isVisible,validateViewRequest} from '../lib/robot.ts';
const data=JSON.parse(readFileSync(new URL('../public/cad/assembly.json',import.meta.url)));
const get=name=>data.parts.find(p=>p.name===name);
const close=(a,b)=>assert.ok(a.distanceTo(b)<1e-8,`${a.toArray()} != ${b.toArray()}`);
test('zero pose preserves CAD coordinates and hip origins stay fixed',()=>{
  for(const [id,j] of Object.entries(data.joints)){
    const p=new T.Vector3(15,-19,91);close(p.clone().applyMatrix4(jointMatrix(id,data.joints,{})),p);
    if(!j.parent){const pivot=new T.Vector3(...j.origin);close(pivot.clone().applyMatrix4(jointMatrix(id,data.joints,{[id]:j.limits[1]})),pivot);}
  }
});
test('jaw follows neck yaw after rotation about its own hinge',()=>{
  const j=data.joints.jaw_pitch,n=data.joints.neck_yaw,p=new T.Vector3(34,11,80),a=12*Math.PI/180,b=45*Math.PI/180;
  const x=p.x-j.origin[0],z=p.z-j.origin[2];
  const pitched=new T.Vector3(j.origin[0]+x*Math.cos(a)+z*Math.sin(a),p.y,j.origin[2]-x*Math.sin(a)+z*Math.cos(a));
  const xx=pitched.x-n.origin[0],yy=pitched.y-n.origin[1];
  const expected=new T.Vector3(n.origin[0]+xx*Math.cos(b)-yy*Math.sin(b),n.origin[1]+xx*Math.sin(b)+yy*Math.cos(b),pitched.z);
  close(p.clone().applyMatrix4(jointMatrix('jaw_pitch',data.joints,{neck_yaw:45,jaw_pitch:12})),expected);
});
test('servo case stays on body while its leg follows the hip; commands are bounded',()=>{
  assert.equal(get('ServoLeft').joint,null);assert.equal(get('LegFootLeft').joint,'left_hip');
  const low=new T.Vector3(24,30,2),m=jointMatrix('left_hip',data.joints,{left_hip:999});
  close(low.clone().applyMatrix4(m),low.clone().applyMatrix4(jointMatrix('left_hip',data.joints,{left_hip:12})));
  assert.ok(low.distanceTo(low.clone().applyMatrix4(m))>1);
});
test('parts grid places every declared print mesh above the floor without overlapping neighbors',()=>{
  const parts=data.parts.filter(isPrintable);assert.ok(parts.length>0);
  const boxes=parts.map((p,i)=>new T.Box3(new T.Vector3(...p.bbox.slice(0,3)),new T.Vector3(...p.bbox.slice(3))).applyMatrix4(gridMatrix(p,i)));
  for(let i=0;i<boxes.length;i++){assert.ok(Math.abs(boxes[i].min.z)<1e-8);for(let j=0;j<i;j++)assert.equal(boxes[i].intersectsBox(boxes[j]),false);}
});
test('inside, grid and explicit visibility filters expose the intended parts',()=>{
  const view={mode:'assembly',hidden:[],onlyPrint:false,internals:true};
  assert.equal(isVisible(get('BodyShellLeft'),view),false);assert.equal(isVisible(get('ServoLeft'),view),true);
  assert.equal(isVisible(get('ClearanceCoupon'),view),false);
  assert.equal(isVisible(get('ClearanceCoupon'),{...view,mode:'grid',internals:false}),true);
  assert.equal(isVisible(get('ServoLeft'),{...view,hidden:['ServoLeft']}),false);
});
test('view request validation rejects impossible or conflicting requests before changing state',()=>{
  assert.deepEqual(validateViewRequest({part:'Jaw',angles:{jaw_pitch:12,neck_yaw:-45}},data),{part:'Jaw',angles:{jaw_pitch:12,neck_yaw:-45}});
  for(const q of [{angles:{neck_yaw:46}},{angles:{jaw_pitch:NaN}},{angles:{fake:0}},{part:'missing'},{mode:'grid',part:'ServoLeft'},{part:'HeadHood',internals:true},{secret:1}])assert.throws(()=>validateViewRequest(q,data));
});
