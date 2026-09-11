import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import * as T from 'three';
import {CpuCamera} from '../scripts/cpu-camera.mjs';

test('accelerated camera queries preserve the integrated face triangles and match ordinary ray hits',()=>{
  const asset=JSON.parse(readFileSync(new URL('../../simulation/browser/robot-physics.json',import.meta.url))),camera=new CpuCamera(asset);
  try{
    const face=camera.meshes.find(mesh=>mesh.name==='FacePanel');
    const original=JSON.parse(readFileSync(new URL('../public/cad/meshes/FacePanel.json',import.meta.url)));
    assert.deepEqual([...face.geometry.index.array],original.indices);
    face.matrix.identity();face.updateMatrixWorld(true);
    for(const z of [86.5,87.5,90,100,110,120,130])for(const y of [-23,0,23]){
      const ray=new T.Raycaster(new T.Vector3(100,y,z),new T.Vector3(-1,0,0),.1,200);ray.firstHitOnly=true;
      const fast=[],ordinary=[];face.raycast(ray,fast);T.Mesh.prototype.raycast.call(face,ray,ordinary);
      ordinary.sort((a,b)=>a.distance-b.distance);assert.equal(fast.length>0,ordinary.length>0);
      if(fast.length)assert.ok(Math.abs(fast[0].distance-ordinary[0].distance)<1e-6);
    }
  }finally{camera.dispose();}
});
