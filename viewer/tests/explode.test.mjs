import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {explodedLayout,posedBox} from '../lib/explode.ts';
const data=JSON.parse(readFileSync(new URL('../public/cad/assembly.json',import.meta.url)));
test('100% explosion separates every assembled mesh at neutral and all joint extremes',()=>{
  const poses=[{}];
  for(const left of [-12,12])for(const right of [-12,12])for(const neck of [-45,45])for(const jaw of [0,12])poses.push({left_hip:left,right_hip:right,neck_yaw:neck,jaw_pitch:jaw});
  for(const angles of poses){
    const layout=explodedLayout(data,angles),parts=data.parts.filter(p=>p.kind!=='coupon');
    const boxes=parts.map(p=>posedBox(p,data,angles).translate(layout.get(p.name)));
    for(let i=0;i<boxes.length;i++)for(let j=0;j<i;j++)assert.equal(boxes[i].intersectsBox(boxes[j]),false,`${parts[i].name} / ${parts[j].name}`);
    assert.equal(layout.size,parts.length);
  }
});
