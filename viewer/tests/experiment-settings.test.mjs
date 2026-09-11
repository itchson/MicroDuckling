import test from 'node:test';
import assert from 'node:assert/strict';
import {manualGait,DEFAULT_MANUAL_GAIT,DEFAULT_EXPERIMENT,validateExperiment,validateTarget,targetFromGround} from '../lib/experiment-settings.ts';
import {locomotionTargets} from '../lib/locomotion-controller.ts';
import {visionTargets,DEFAULT_VISION_PARAMETERS} from '../lib/vision.ts';

test('custom gait exposes swing, lean, phase and pace while respecting the complete hip envelope',()=>{
  const settings={...DEFAULT_MANUAL_GAIT,swingDeg:8,leanDeg:3,frequencyHz:1,phaseDeg:180};
  const gait=manualGait(settings),degrees=180/Math.PI;
  const start=locomotionTargets(gait,0),half=locomotionTargets(gait,.5);
  assert.ok(Math.abs(start.left_hip*degrees-5)<1e-8);assert.ok(Math.abs(start.right_hip*degrees+11)<1e-8);
  assert.ok(Math.abs(half.left_hip-start.right_hip)<1e-8);
  const fast=manualGait({...settings,frequencyHz:2});assert.deepEqual(locomotionTargets(fast,.25),half);
  for(const leanDeg of [-12,-10,0,10,12]){
    const limited=manualGait({...settings,swingDeg:12,leanDeg});
    assert.ok(Math.abs(limited.leftAmplitudeRad*degrees-(12-Math.abs(leanDeg)))<1e-8);
    for(let i=0;i<200;i++){const a=locomotionTargets(limited,i/100);assert.ok(Math.abs(a.left_hip)<=Math.PI/15+1e-10);assert.ok(Math.abs(a.right_hip)<=Math.PI/15+1e-10);}
  }
  const together=manualGait({...settings,phaseDeg:0});for(let i=0;i<40;i++){const a=locomotionTargets(together,i/40);assert.equal(a.left_hip,a.right_hip);}
});
test('ground placement uses metres once, stays on the floor and rejects invalid target or gait settings',()=>{
  assert.deepEqual(targetFromGround(320,-175),[.32,-.175,.05]);assert.deepEqual(targetFromGround(-300,900),[.16,.4,.05]);
  assert.deepEqual(validateTarget([.32,-.175,.05]),[.32,-.175,.05]);
  for(const target of [[NaN,0,.05],[.18,0,1],[.1,0,.05],[.18,.5,.05]])assert.throws(()=>validateTarget(target));
  for(const patch of [{swingDeg:13},{leanDeg:NaN},{frequencyHz:0},{duty:1},{headSwayDeg:46}])assert.throws(()=>manualGait({...DEFAULT_MANUAL_GAIT,...patch}));
  assert.throws(()=>validateExperiment({...DEFAULT_EXPERIMENT,cameraSeconds:Infinity}));
});
test('lost-target search uses the selected neck sweep without moving the hips',()=>{
  const gait=manualGait(DEFAULT_MANUAL_GAIT),image={visible:false,bearingRad:0,areaFraction:0};let previous=0,max=0;
  for(let i=0;i<360;i++){const a=visionTargets(image,DEFAULT_VISION_PARAMETERS,gait,i/60,1/60,previous,false,{scanAmplitudeDeg:10,scanPeriodSeconds:4});
    assert.equal(a.left_hip,0);assert.equal(a.right_hip,0);assert.ok(Math.abs(a.neck_yaw-previous)<=.8/60+1e-9);previous=a.neck_yaw;max=Math.max(max,Math.abs(previous));}
  assert.ok(max>.16&&max<=10*Math.PI/180+1e-8);
  const stopped=visionTargets(image,DEFAULT_VISION_PARAMETERS,gait,2,1/60,0,false,{scanAmplitudeDeg:0,scanPeriodSeconds:6});assert.equal(stopped.neck_yaw,0);
});
