import test from 'node:test';
import assert from 'node:assert/strict';
import * as T from 'three';
import {updateCameraClipping} from '../lib/robot.ts';

test('clipping retains CAD corners with submillimetre depth resolution during zoom and orbit',()=>{
  const bounds=new T.Box3(new T.Vector3(-35,-56,0),new T.Vector3(41,56,136));
  for(const position of [[225,-280,180],[0,3000,1500],[-180,0,100],[0,0,500]]){
    const camera=new T.PerspectiveCamera(36,1,.1,5000);camera.up.set(0,0,1);
    camera.position.set(...position);camera.lookAt(0,0,76);updateCameraClipping(camera,bounds);
    for(const x of [bounds.min.x,bounds.max.x])for(const y of [bounds.min.y,bounds.max.y])for(const z of [bounds.min.z,bounds.max.z]){
      const point=new T.Vector3(x,y,z),depth=-point.clone().applyMatrix4(camera.matrixWorldInverse).z;
      assert.ok(depth>camera.near&&depth<camera.far);
      const projected=point.project(camera);assert.ok(projected.z>-1&&projected.z<1);
      const quantum=depth*depth*(camera.far-camera.near)/(camera.far*camera.near*(2**24-1));
      assert.ok(quantum<.001,`Insufficient precision at ${position}: ${quantum}mm`);
    }
  }
});

test('clipping remains finite inside a part and tolerates an empty view',()=>{
  const camera=new T.PerspectiveCamera(36,1,.1,5000);
  updateCameraClipping(camera,new T.Box3());assert.equal(camera.near,.1);
  updateCameraClipping(camera,new T.Box3(new T.Vector3(-10,-10,-10),new T.Vector3(10,10,10)));
  assert.ok(camera.near>0&&camera.far>camera.near&&Number.isFinite(camera.far));
});
