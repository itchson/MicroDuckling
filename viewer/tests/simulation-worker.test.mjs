import test from 'node:test';
import assert from 'node:assert/strict';
import {Worker} from 'node:worker_threads';
import {readFileSync} from 'node:fs';
const asset=JSON.parse(readFileSync(new URL('../../simulation/browser/robot-physics.json',import.meta.url)));

test('worker runs physical poses, pauses, resets and scores camera trials from current observations',async()=>{
  const worker=new Worker(new URL('./helpers/physics-worker.mjs',import.meta.url));
  const pending=[];let currentMode='paused',lastObservation=-1,sendFreshImages=true,staleTrialRun=-1;
  const next=(predicate,timeout=20000)=>new Promise((resolve,reject)=>{
    const entry={predicate,resolve,reject};pending.push(entry);
    const timer=setTimeout(()=>{pending.splice(pending.indexOf(entry),1);reject(Error('Worker response timed out'));},timeout);
    entry.resolve=value=>{clearTimeout(timer);resolve(value);};entry.reject=error=>{clearTimeout(timer);reject(error);};
  });
  worker.on('error',error=>{for(const entry of pending.splice(0))entry.reject(error);});
  worker.on('message',message=>{
    if(message.type==='mode'){currentMode=message.mode;lastObservation=-1;}
    if(message.type==='error'){for(const entry of pending.splice(0))entry.reject(Error(message.message));return;}
    if(message.type==='frame'&&currentMode==='camera-learning'&&message.frame.time-lastObservation>=.09){
      lastObservation=message.frame.time;
      // Deterministic sensor fixture exercises transport/scoring; image formation is tested separately.
      if(sendFreshImages||staleTrialRun!==message.runId){
        worker.postMessage({type:'observation',runId:message.runId,frameTime:message.frame.time,observation:{visible:true,bearingRad:0,areaFraction:.01}});
        staleTrialRun=message.runId;
      }
      worker.postMessage({type:'observation',runId:message.runId-1,frameTime:message.frame.time,observation:{visible:false,bearingRad:1,areaFraction:0}});
    }
    for(const entry of [...pending])if(entry.predicate(message)){pending.splice(pending.indexOf(entry),1);entry.resolve(message);}
  });
  try{
    const initialized=next(m=>m.type==='ready');worker.postMessage({type:'init',asset});await initialized;
    worker.postMessage({type:'pose',angles:{left_hip:0,right_hip:0,neck_yaw:.4,jaw_pitch:.1}});
    const moved=next(m=>m.type==='frame'&&m.frame.time>.6);worker.postMessage({type:'run',mode:'pose'});
    const pose=await moved;assert.ok(pose.frame.jointAngles.neck_yaw>.2);assert.ok(pose.frame.jointAngles.jaw_pitch>.05);
    const paused=next(m=>m.type==='mode'&&m.mode==='paused');worker.postMessage({type:'run',mode:'paused'});await paused;
    const reset=next(m=>m.type==='frame'&&m.runId>pose.runId);worker.postMessage({type:'reset'});
    const zero=await reset;assert.equal(zero.frame.time,0);assert.ok(Math.abs(zero.frame.jointAngles.neck_yaw)<1e-8);
    const trial=next(m=>m.type==='vision-training');worker.postMessage({type:'run',mode:'camera-learning'});
    const result=(await trial).progress;
    assert.equal(result.trial,1);assert.ok(result.visibleFraction>.8&&result.visibleFraction<=1);assert.equal(result.fall,false);
    assert.equal(result.eligible,true);assert.ok(Math.abs(result.score-2*result.visibleFraction)<1e-9,'Only current, centered pixel observations should score');
    assert.equal(result.bestScore,result.score);
    sendFreshImages=false;staleTrialRun=-1;
    const staleTrial=next(m=>m.type==='vision-training');worker.postMessage({type:'run',mode:'camera-learning'});
    const stale=(await staleTrial).progress;assert.equal(stale.eligible,false);assert.equal(stale.bestScore,null);
    assert.ok(stale.coverageFraction<.1,'A single stale frame cannot qualify a six-second trial');
    const generation=next(m=>m.type==='training');worker.postMessage({type:'run',mode:'walk-learning'});
    const learned=(await generation).progress;assert.equal(learned.episodesEvaluated,9);assert.equal(learned.generation,1);
    assert.ok(learned.candidates.some(c=>c.score!==learned.candidates[0].score));
  }finally{await worker.terminate();for(const entry of pending.splice(0))entry.reject(Error('Worker terminated'));}
});
