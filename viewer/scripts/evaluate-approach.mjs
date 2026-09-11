// SPDX-License-Identifier: Apache-2.0
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {BrowserPhysics} from '../lib/browser-physics.ts';
import {ApproachEpisode} from '../lib/approach.ts';
import {CAMERA_WADDLE_GAIT} from '../lib/locomotion-controller.ts';
import {detectTarget,DEFAULT_VISION_PARAMETERS} from '../lib/vision.ts';
import {CpuCamera,WIDTH,HEIGHT,FOV} from './cpu-camera.mjs';
const bytes=readFileSync(new URL('../../simulation/browser/robot-physics.json',import.meta.url)),asset=JSON.parse(bytes);
const overrides=JSON.parse(process.env.APPROACH_OPTIONS??'{}');
const engine=await BrowserPhysics.create(asset,overrides.physics??{}),camera=new CpuCamera(asset);
const report={assetSha256:createHash('sha256').update(bytes).digest('hex'),physics:engine.options,gait:CAMERA_WADDLE_GAIT,parameters:{...DEFAULT_VISION_PARAMETERS,...overrides.parameters},episodes:[]};
try{
  for(const target of overrides.targets??[[.18,0,.05]])for(const seed of overrides.seeds??[2026]){
    const episode=new ApproachEpisode(engine,asset,CAMERA_WADDLE_GAIT,report.parameters,target,{seed,seconds:overrides.seconds??60});let result=episode.current();const trace=[];
    while(!result.finished){
      const image=camera.capture(result.frame,target),observation=detectTarget(image,WIDTH,HEIGHT,FOV*Math.PI/180);
      result=episode.observe(observation,result.frame.time);
      if(result.observations%10===0||result.finished)trace.push({time:result.goal.elapsedSeconds,distanceM:result.goal.distanceM,heading:result.goal.headingErrorRad,tilt:result.goal.tiltRad,observation,neck:result.frame.jointAngles.neck_yaw});
    }
    const {frame,...measured}=result;report.episodes.push({seed,target,...measured,trace});
    console.log(JSON.stringify({seed,target,success:result.goal.success,progressM:result.goal.progressM,distanceM:result.goal.distanceM,fall:result.goal.fallen,seconds:result.goal.elapsedSeconds,visibleFraction:result.visibleFraction}));
  }
}finally{engine.dispose();camera.dispose();}
mkdirSync(new URL('../../work/',import.meta.url),{recursive:true});
writeFileSync(new URL(`../../work/${overrides.output??'approach-evaluation.json'}`,import.meta.url),JSON.stringify(report,null,2)+'\n');
