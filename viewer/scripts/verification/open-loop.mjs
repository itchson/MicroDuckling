// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {asset,BrowserPhysics,CAMERA_WADDLE_GAIT,locomotionTargets,ZERO,com,slope,save} from './common.mjs';
const seeds=[2026,42,99],seconds=30,warmupSeconds=5,results=[];
const startWall=performance.now();
for(const hz of [600,1000])for(const solverIterations of [16,24])for(const seed of seeds) {
  const engine=await BrowserPhysics.create(asset,{fixedDt:1/hz,solverIterations});
  try {
    engine.reset({seed,perturbationRad:.002});
    for(let i=0;i<60;i++)engine.step(1/60,ZERO);
    const start=engine.frame(),initial=com(start),bodyStart=start.links.body.position;
    let frame=start,maxTilt=0,tiltSum=0,headingSum=0,count=0;
    const samples=[];
    for(let i=0;i<seconds*60&&!frame.metrics.fall;i++) {
      frame=engine.step(1/60,locomotionTargets(CAMERA_WADDLE_GAIT,i/60));
      const t=(i+1)/60;maxTilt=Math.max(maxTilt,frame.metrics.tiltRad);
      if(t>=warmupSeconds){tiltSum+=frame.metrics.tiltRad**2;headingSum+=frame.metrics.headingRad**2;count++;}
      if((i+1)%15===0&&t>=warmupSeconds)samples.push({t,com:com(frame)});
    }
    const final=com(frame);
    const row={physicsHz:hz,solverIterations,seed,durationSeconds:frame.time-start.time,
      controlHz:60,settleSeconds:1,lateWindowSeconds:[warmupSeconds,seconds],
      comDisplacementM:final.map((v,i)=>v-initial[i]),bodyOriginDisplacementM:frame.links.body.position.map((v,i)=>v-bodyStart[i]),
      lateForwardSpeedMps:slope(samples,0),lateLateralSpeedMps:slope(samples,1),
      last15sForwardSpeedMps:slope(samples.filter(s=>s.t>=15),0),finalHeadingRad:frame.metrics.headingRad,
      maxTiltRad:maxTilt,rmsTiltRad:Math.sqrt(tiltSum/Math.max(1,count)),rmsHeadingRad:Math.sqrt(headingSum/Math.max(1,count)),
      maxJointLimitViolationRad:frame.metrics.maxJointLimitViolationRad,fall:frame.metrics.fall,
      lateSampleCount:samples.length,diagnostics:engine.diagnostics()};
    assert.ok(Object.values(row).filter(v=>typeof v==='number').every(Number.isFinite));
    results.push(row);
    console.log(JSON.stringify({completed:results.length,hz,solverIterations,seed,distanceM:row.comDisplacementM[0],lateMps:row.lateForwardSpeedMps,fall:row.fall}));
  } finally {engine.dispose();}
}
const groups=[];
for(const hz of [600,1000])for(const solver of [16,24]) {
  const rows=results.filter(r=>r.physicsHz===hz&&r.solverIterations===solver);
  groups.push({physicsHz:hz,solverIterations:solver,episodes:rows.length,falls:rows.filter(r=>r.fall).length,
    meanForwardM:rows.reduce((s,r)=>s+r.comDisplacementM[0],0)/rows.length,
    meanLateForwardMps:rows.reduce((s,r)=>s+r.lateForwardSpeedMps,0)/rows.length,
    forwardRangeM:[Math.min(...rows.map(r=>r.comDisplacementM[0])),Math.max(...rows.map(r=>r.comDisplacementM[0]))]});
}
await save('open-loop-results.json',{experiment:'final asset open-loop CAMERA_WADDLE_GAIT',seeds,gait:CAMERA_WADDLE_GAIT,
  rawEpisodeCount:results.length,expectedEpisodeCount:12,wallSeconds:(performance.now()-startWall)/1000,groups,results});
console.log(JSON.stringify({finished:true,groups}));
