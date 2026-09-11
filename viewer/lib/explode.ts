import * as T from 'three';
import {type Assembly,type Part,jointMatrix,separation} from './robot.ts';

const boxFor=(p:Part)=>new T.Box3(new T.Vector3(...p.bbox.slice(0,3)),new T.Vector3(...p.bbox.slice(3)));
export function posedBox(p:Part,data:Assembly,angles:Record<string,number>):T.Box3 {
  const box=boxFor(p);return p.joint?box.applyMatrix4(jointMatrix(p.joint,data.joints,angles)):box;
}

/** A fully exploded placement has separated conservative bounds for every mesh.
 * Interpolation is a display transition, not a physical disassembly path.
 */
export function explodedLayout(data:Assembly,angles:Record<string,number>,gap=5):Map<string,T.Vector3> {
  const items=data.parts.filter(p=>p.kind!=='coupon').map(p=>({p,box:posedBox(p,data,angles)}));
  items.sort((a,b)=>b.box.getSize(new T.Vector3()).lengthSq()-a.box.getSize(new T.Vector3()).lengthSq()||a.p.name.localeCompare(b.p.name));
  const placed:T.Box3[]=[],offsets=new Map<string,T.Vector3>();
  const directions=[new T.Vector3(0,0,1),new T.Vector3(1,0,0),new T.Vector3(-1,0,0),new T.Vector3(0,1,0),new T.Vector3(0,-1,0),new T.Vector3(0,0,-1)];
  for(const {p,box} of items){
    const desired=separation(p).multiplyScalar(1.8),center=box.getCenter(new T.Vector3());
    const outward=center.clone().add(desired).sub(new T.Vector3(0,0,60)).normalize();
    const axes=[outward,...directions];let offset=desired.clone(),candidate=box.clone().translate(offset),found=false;
    for(let ring=0;ring<=80&&!found;ring++)for(const direction of axes){
      offset=desired.clone().addScaledVector(direction,ring*8);
      candidate=box.clone().translate(offset);
      if(placed.every(other=>!other.intersectsBox(candidate.clone().expandByScalar(gap/2)))){found=true;break;}
    }
    if(!found){
      const right=Math.max(0,...placed.map(b=>b.max.x));
      offset=new T.Vector3(right+gap-box.min.x,desired.y,desired.z);candidate=box.clone().translate(offset);
    }
    // Stored bounds are already expanded by half the requested spacing.
    placed.push(candidate.clone().expandByScalar(gap/2));offsets.set(p.name,offset);
  }
  return offsets;
}
