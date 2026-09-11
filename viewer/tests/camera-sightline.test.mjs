import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import * as T from 'three';
const data=JSON.parse(readFileSync(new URL('../public/cad/assembly.json',import.meta.url)));

test('assembled lens sightline reaches all three target positions through the actual CAD meshes',()=>{
  const meshes=data.parts.filter(p=>p.kind!=='coupon').map(part=>{
    const source=JSON.parse(readFileSync(new URL(`../public/cad/meshes/${part.name}.json`,import.meta.url)));
    const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.Float32BufferAttribute(source.positions,3));geometry.setIndex(source.indices);
    const mesh=new T.Mesh(geometry,new T.MeshBasicMaterial({side:T.FrontSide}));mesh.name=part.name;mesh.updateMatrixWorld(true);return mesh;
  });
  try{
    assert.equal(meshes.length,82);
    assert.ok(meshes.every(mesh=>!mesh.name.includes('Horn')&&!mesh.name.startsWith('UpperBill')),'Design must not retain horn arms or the retired upper-bill mounting');
    assert.equal(data.parts.find(part=>part.name==='UpperMouthBase')?.link,'head','Upper mouth base moves with the top shell');
    for(const [name,link] of [['OutputSplineLeft','left_leg'],['OutputSplineRight','right_leg'],['OutputSplineNeck','head'],['OutputSplineMouth','jaw']]){
      assert.equal(data.parts.find(part=>part.name===name)?.link,link,'Output teeth must rotate with their driven socket');
    }
    const camera=new T.PerspectiveCamera(50,96/72,.1,5000);camera.up.set(0,0,1);camera.position.set(34.8,0,111);camera.lookAt(35.8,0,111);camera.updateMatrixWorld(true);
    for(const side of [-100,0,100])for(const y of [-24,-12,0,12,24])for(const z of [1,13,25,37,49]){
      const point=new T.Vector3(355,side+y,z),delta=point.clone().sub(camera.position),distance=delta.length(),projected=point.clone().project(camera);
      assert.ok(Math.abs(projected.x)<=1&&Math.abs(projected.y)<=1&&Math.abs(projected.z)<=1,'Target must be in the sensor frustum');
      const ray=new T.Raycaster(camera.position,delta.normalize(),.1,distance-.001),hits=ray.intersectObjects(meshes,false);
      assert.equal(hits.length,0,`Camera ray blocked by ${hits[0]?.object.name}`);
    }
  }finally{for(const mesh of meshes){mesh.geometry.dispose();mesh.material.dispose();}}
});
