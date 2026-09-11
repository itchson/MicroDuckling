import test from 'node:test';
import assert from 'node:assert/strict';
import {detectTarget,visionTargets,cameraScore,proposeVisionParameters,DEFAULT_VISION_PARAMETERS} from '../lib/vision.ts';
import {DEFAULT_GAIT} from '../lib/browser-physics.ts';
const image=(w=20,h=10)=>({w,h,pixels:new Uint8Array(w*h*4)});
function box(im,x,y,w,h,color=[180,55,220,255]){for(let iy=y;iy<y+h;iy++)for(let ix=x;ix<x+w;ix++)im.pixels.set(color,(iy*im.w+ix)*4);return im;}
const detect=im=>detectTarget(im.pixels,im.w,im.h,Math.PI/3);
const visible={visible:true,bearingRad:.2,areaFraction:.01};

test('pixel centroid maps center, left and right to correct signed camera bearings',()=>{
  const center=detect(box(image(),8,3,4,4));assert.equal(center.visible,true);assert.ok(Math.abs(center.bearingRad)<1e-12);assert.equal(center.areaFraction,.08);
  const left=detect(box(image(),1,3,4,4)),right=detect(box(image(),15,3,4,4));
  assert.ok(left.bearingRad>0);assert.ok(right.bearingRad<0);assert.ok(Math.abs(left.bearingRad+right.bearingRad)<1e-12);
  const expected=Math.atan(.7*Math.tan(Math.PI/6)*2);assert.ok(Math.abs(left.bearingRad-expected)<1e-12);
});
test('occlusion reduces measured area, largest blob wins, and empty/isolated noise is invisible',()=>{
  assert.deepEqual(detect(image()),{visible:false,bearingRad:0,areaFraction:0});
  assert.equal(detect(box(image(),2,2,1,1)).visible,false);
  const im=box(image(),1,2,4,4);box(im,15,3,2,2);
  const full=detect(im);assert.ok(full.bearingRad>0);assert.equal(full.areaFraction,.08);
  box(im,1,2,4,2,[0,0,0,255]);const partial=detect(im);assert.equal(partial.areaFraction,.04);assert.ok(partial.bearingRad>0);
  assert.equal(detect(box(image(),1,1,5,5,[245,120,20,255])).visible,false,'Orange feet must not be a target');
  assert.equal(detect(box(image(),1,1,5,5,[130,150,180,255])).visible,false,'Gray-blue CAD must not be a target');
});
test('vertical WebGL row flip preserves bearing and detector validates data dimensions',()=>{
  const a=detect(box(image(),1,1,4,3)),b=detect(box(image(),1,6,4,3));assert.deepEqual(a,b);
  assert.throws(()=>detectTarget(new Uint8Array(4),2,2,1));assert.throws(()=>detectTarget(new Uint8Array(4),1,1,Math.PI));
});
test('image controller bounds joints, steers opposite signs, scans only when lost and stops when close',()=>{
  for(let t=0;t<5;t+=.1){const p=visionTargets({...visible,bearingRad:1},DEFAULT_VISION_PARAMETERS,DEFAULT_GAIT,t,.1,.75);
    assert.ok(Math.abs(p.left_hip)<=Math.PI/15);assert.ok(Math.abs(p.right_hip)<=Math.PI/15);assert.ok(Math.abs(p.neck_yaw)<=Math.PI/4);}
  const left=visionTargets(visible,DEFAULT_VISION_PARAMETERS,DEFAULT_GAIT,0,.1,0);
  const right=visionTargets({...visible,bearingRad:-.2},DEFAULT_VISION_PARAMETERS,DEFAULT_GAIT,0,.1,0);
  assert.ok(left.neck_yaw>0&&right.neck_yaw<0);assert.ok(left.left_hip<left.right_hip);assert.ok(right.left_hip>right.right_hip);
  const close=visionTargets({...visible,areaFraction:.2},DEFAULT_VISION_PARAMETERS,DEFAULT_GAIT,.2,.1,0);assert.equal(close.left_hip,0);assert.equal(close.right_hip,0);
  const lost=visionTargets({visible:false,bearingRad:0,areaFraction:0},DEFAULT_VISION_PARAMETERS,DEFAULT_GAIT,1,.1,0);assert.equal(lost.left_hip,0);assert.equal(lost.right_hip,0);assert.ok(lost.neck_yaw>0&&lost.neck_yaw<=.08+1e-12);
});
test('pixel reward favors centered visible approach and penalizes falls without world-distance inputs',()=>{
  const base={visibleFraction:1,meanAbsBearingRad:.2,initialArea:.01,finalArea:.01,fall:false};
  const stationary=cameraScore(base),approach=cameraScore({...base,finalArea:.04});assert.ok(approach>stationary);
  assert.ok(cameraScore({...base,meanAbsBearingRad:0})>stationary);
  assert.ok(cameraScore({...base,visibleFraction:0})<stationary);
  assert.ok(cameraScore({...base,finalArea:.09,fall:true})<cameraScore({...base,visibleFraction:0}));
  assert.equal(cameraScore({...base,finalArea:.09}),cameraScore({...base,finalArea:.9}));
  assert.throws(()=>cameraScore({...base,visibleFraction:NaN}));
});
test('parameter proposals reproduce seeds, stay bounded, leave best unchanged and explore either turn sign',()=>{
  const best={...DEFAULT_VISION_PARAMETERS},before={...best};
  assert.deepEqual(proposeVisionParameters(best,0),best);
  assert.deepEqual(proposeVisionParameters(best,3),proposeVisionParameters(best,3));
  const candidates=Array.from({length:80},(_,i)=>proposeVisionParameters(best,i));
  assert.ok(candidates.some(p=>p.turnGain<0)&&candidates.some(p=>p.turnGain>0));
  for(const p of candidates){assert.ok(p.headGain>0&&p.headGain<=12);assert.ok(Math.abs(p.turnGain)<=.6);assert.ok(p.forwardScale>=0&&p.forwardScale<=1.5);}
  assert.deepEqual(best,before);assert.throws(()=>proposeVisionParameters(best,-1));
});
