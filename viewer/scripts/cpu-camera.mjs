// SPDX-License-Identifier: Apache-2.0
// Geometric reference camera: actual CAD triangle occlusion, no lighting approximation
// used by the controller. The target is unlit magenta in the WebGL scene too.
import {readFileSync} from 'node:fs';
import * as T from 'three';
import {MeshBVH,acceleratedRaycast} from 'three-mesh-bvh';
export const WIDTH=96,HEIGHT=72,FOV=50;
export class CpuCamera {
  constructor(asset){
    this.asset=asset;
    const assembly=JSON.parse(readFileSync(new URL('../public/cad/assembly.json',import.meta.url)));
    this.meshes=assembly.parts.filter(p=>p.kind!=='coupon').map(part=>{
      const source=JSON.parse(readFileSync(new URL(`../public/cad/meshes/${part.name}.json`,import.meta.url)));
      const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.Float32BufferAttribute(source.positions,3));geometry.setIndex(source.indices);geometry.computeBoundingBox();geometry.computeBoundingSphere();
      // The integrated face surrounds the lens's bounding box. Accelerate exact
      // triangle queries without changing its topology or source index order.
      geometry.boundsTree=new MeshBVH(geometry,{indirect:true});
      const mesh=new T.Mesh(geometry,new T.MeshBasicMaterial({side:T.FrontSide}));mesh.raycast=acceleratedRaycast;mesh.name=part.name;mesh.userData.link=part.link;mesh.matrixAutoUpdate=false;return mesh;
    });
    this.target=new T.Mesh(new T.BoxGeometry(50,50,100),new T.MeshBasicMaterial());
    this.sensor=new T.PerspectiveCamera(FOV,WIDTH/HEIGHT,.1,5000);this.sensor.up.set(0,0,1);
    this.ray=new T.Raycaster();this.ray.near=.1;this.ray.firstHitOnly=true;this.pixels=new Uint8Array(WIDTH*HEIGHT*4);
  }
  capture(frame,targetPosition){
    const matrices={};
    for(const [name,pose] of Object.entries(frame.links)){
      const zero=this.asset.cadZeroOriginsM[name];
      matrices[name]=new T.Matrix4().compose(new T.Vector3(...pose.position).multiplyScalar(1000),new T.Quaternion(...pose.quaternion),new T.Vector3(1,1,1))
        .multiply(new T.Matrix4().makeTranslation(...zero.map(v=>-v*1000)));
    }
    for(const mesh of this.meshes){mesh.matrix.copy(matrices[mesh.userData.link]);mesh.updateMatrixWorld(true);}
    const sensor=this.sensor,head=matrices.head,position=new T.Vector3(34.8,0,111).applyMatrix4(head);
    sensor.position.copy(position);sensor.up.set(0,0,1).transformDirection(head);sensor.lookAt(position.clone().add(new T.Vector3(1,0,0).transformDirection(head)));sensor.updateMatrixWorld(true);
    this.target.position.fromArray(targetPosition).multiplyScalar(1000);this.target.updateMatrixWorld(true);
    const frustum=new T.Frustum().setFromProjectionMatrix(new T.Matrix4().multiplyMatrices(sensor.projectionMatrix,sensor.matrixWorldInverse));
    const candidates=this.meshes.filter(m=>frustum.intersectsObject(m));
    const boxes=candidates.map(m=>m.geometry.boundingBox.clone().applyMatrix4(m.matrixWorld));
    const pixels=this.pixels;pixels.fill(0);const ndc=new T.Vector2(),hitPoint=new T.Vector3();
    for(let y=0;y<HEIGHT;y++)for(let x=0;x<WIDTH;x++){
      ndc.set((x+.5)/WIDTH*2-1,(y+.5)/HEIGHT*2-1);this.ray.far=5000;this.ray.setFromCamera(ndc,sensor);
      const targetHits=this.ray.intersectObject(this.target,false);if(!targetHits.length)continue;
      this.ray.far=targetHits[0].distance-.001;let blocked=false;
      for(let i=0;i<candidates.length;i++){
        if(!this.ray.ray.intersectBox(boxes[i],hitPoint)||hitPoint.distanceTo(sensor.position)>this.ray.far)continue;
        if(this.ray.intersectObject(candidates[i],false).length){blocked=true;break;}
      }
      if(!blocked){const p=(y*WIDTH+x)*4;pixels[p]=236;pixels[p+1]=25;pixels[p+2]=223;pixels[p+3]=255;}
    }
    return pixels;
  }
  dispose(){for(const mesh of [...this.meshes,this.target]){mesh.geometry.dispose();mesh.material.dispose();}}
}
