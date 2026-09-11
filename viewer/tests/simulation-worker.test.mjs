import test from 'node:test';
import assert from 'node:assert/strict';
import {Worker} from 'node:worker_threads';
import {readFileSync} from 'node:fs';
const asset=JSON.parse(readFileSync(new URL('../../simulation/browser/robot-physics.json',import.meta.url)));

test('worker transports physics, pauses without images and scores physical progress',async()=>{
  const worker=new Worker(new URL('./helpers/physics-worker.mjs',import.meta.url));
  const pending=[];let currentMode='paused',images=false,lastFrame;
  const next=(predicate,timeout=120000)=>new Promise((resolve,reject)=>{
    const entry={predicate,resolve,reject};pending.push(entry);
    const timer=setTimeout(()=>{pending.splice(pending.indexOf(entry),1);reject(Error('Worker response timed out'));},timeout);
    entry.resolve=value=>{clearTimeout(timer);resolve(value);};entry.reject=error=>{clearTimeout(timer);reject(error);};
  });
  worker.on('error',error=>{for(const entry of pending.splice(0))entry.reject(error);});
  worker.on('message',message=>{
    if(message.type==='mode')currentMode=message.mode;
    if(message.type==='error'){for(const entry of pending.splice(0))entry.reject(Error(message.message));return;}
    if(message.type==='frame'){
      lastFrame=message;
      if(currentMode==='camera-learning'&&images){
        // Deliberately saturated image fixture: transport works but looking alone must not score success.
        worker.postMessage({type:'observation',runId:message.runId,frameTime:message.frame.time,observation:{visible:true,bearingRad:0,areaFraction:1,widthFraction:1}});
        worker.postMessage({type:'observation',runId:message.runId-1,frameTime:message.frame.time,observation:{visible:false,bearingRad:1,areaFraction:0}});
      }
    }
    for(const entry of [...pending])if(entry.predicate(message)){pending.splice(pending.indexOf(entry),1);entry.resolve(message);}
  });
  try{
    const initialized=next(m=>m.type==='ready');worker.postMessage({type:'init',asset});await initialized;
    worker.postMessage({type:'pose',angles:{left_hip:0,right_hip:0,neck_yaw:.4,jaw_pitch:.1}});
    const moved=next(m=>m.type==='frame'&&m.frame.time>.6);worker.postMessage({type:'run',mode:'pose'});
    const pose=await moved;assert.ok(pose.frame.jointAngles.neck_yaw>.2);assert.ok(pose.frame.jointAngles.jaw_pitch>.05);
    const reset=next(m=>m.type==='frame'&&m.runId>pose.runId);worker.postMessage({type:'reset'});
    const zero=await reset;assert.equal(zero.frame.time,0);assert.ok(Math.abs(zero.frame.jointAngles.neck_yaw)<1e-8);
    const relocated=next(m=>m.type==='frame'&&m.runId>zero.runId);worker.postMessage({type:'target',position:[.35,.1,.05]});
    const relocatedFrame=await relocated;assert.equal(relocatedFrame.frame.time,0);
    const custom=next(m=>m.type==='policy');worker.postMessage({type:'gait',settings:{swingDeg:6,leanDeg:2,frequencyHz:1.5,phaseDeg:180,duty:.5,headSwayDeg:0}});
    const chosen=await custom;assert.equal(chosen.gait.frequencyHz,1.5);assert.ok(Math.abs(chosen.gait.leftAmplitudeRad-6*Math.PI/180)<1e-10);
    const restored=next(m=>m.type==='policy');worker.postMessage({type:'reference'});assert.notEqual((await restored).gait.frequencyHz,1.5);
    const configured=next(m=>m.type==='frame');worker.postMessage({type:'experiment',settings:{cameraSeconds:15,scanAmplitudeDeg:20,scanPeriodSeconds:4}});await configured;
    const cameraStart=next(m=>m.type==='frame'&&m.goal);worker.postMessage({type:'run',mode:'camera-learning'});
    const start=await cameraStart;
    assert.ok(start.goal.initialDistanceM>.3,'Episode must use the relocated physical target');
    worker.postMessage({type:'observation',runId:start.runId-1,frameTime:start.frame.time,observation:{visible:true,bearingRad:0,areaFraction:1}});
    await new Promise(resolve=>setTimeout(resolve,150));assert.equal(lastFrame.frame.time,start.frame.time,'No current image means no physics progress');
    images=true;const trial=next(m=>m.type==='vision-training');
    worker.postMessage({type:'observation',runId:start.runId,frameTime:start.frame.time,observation:{visible:true,bearingRad:0,areaFraction:1,widthFraction:1}});
    const result=(await trial).progress;images=false;
    assert.equal(result.trial,1);assert.equal(result.eligible,true);assert.equal(result.goal.success,false);
    assert.ok(result.goal.elapsedSeconds>=15&&result.goal.elapsedSeconds<15.1,'Configured trial duration must stop the physical episode');
    assert.ok(Math.abs(result.goal.progressM)<.005);assert.ok(result.score<1,'Image area cannot manufacture locomotion reward');
    const generation=next(m=>m.type==='training');worker.postMessage({type:'run',mode:'walk-learning'});
    const learned=(await generation).progress;assert.equal(learned.episodesEvaluated,14);assert.equal(learned.generation,1);
    assert.ok(learned.candidates.some(c=>c.score!==learned.candidates[0].score));
    assert.ok(['search','provided-seed','neutral'].includes(learned.bestOrigin));
    assert.equal(learned.improvementOverSeedM,learned.best.distanceM-learned.seed.distanceM);
  }finally{await worker.terminate();for(const entry of pending.splice(0))entry.reject(Error('Worker terminated'));}
});
