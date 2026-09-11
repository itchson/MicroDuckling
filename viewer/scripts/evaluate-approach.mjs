// SPDX-License-Identifier: Apache-2.0
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {BrowserPhysics} from '../lib/browser-physics.ts';
import {ApproachEpisode} from '../lib/approach.ts';
import {CAMERA_WADDLE_GAIT} from '../lib/locomotion-controller.ts';
import {detectTarget,DEFAULT_VISION_PARAMETERS} from '../lib/vision.ts';
import {CpuCamera,WIDTH,HEIGHT,FOV} from './cpu-camera.mjs';
const root=new URL('../../',import.meta.url);
const hash=path=>createHash('sha256').update(readFileSync(new URL(path,root))).digest('hex');
const assembly=JSON.parse(readFileSync(new URL('cad/assembly.json',root)));
const components=JSON.parse(readFileSync(new URL('components/records.json',root)));
const cached=JSON.parse(readFileSync(new URL('viewer/public/cad/assembly.json',root)));
const expected=[...assembly.parts,...components.parts].filter(p=>p.kind!=='coupon');
const actual=cached.parts.filter(p=>p.kind!=='coupon');
if(JSON.stringify(actual.map(p=>[p.name,p.link]))!==JSON.stringify(expected.map(p=>[p.name,p.link])))throw Error('Stale camera part/link cache');
const paths=['simulation/browser/robot-physics.json','cad/assembly.json','components/records.json',
  'viewer/public/cad/assembly.json','viewer/lib/browser-physics.ts','viewer/lib/approach.ts',
  'viewer/lib/goal-metrics.ts','viewer/lib/vision.ts','viewer/lib/experiment-settings.ts',
  'viewer/lib/locomotion-controller.ts','viewer/scripts/cpu-camera.mjs',
  'viewer/scripts/evaluate-approach.mjs','viewer/package-lock.json'];
for(const part of actual){
  const canonical=`${components.parts.some(p=>p.name===part.name)?'components':'cad'}/meshes/${part.name}.json`;
  const cache=`viewer/public/cad/meshes/${part.name}.json`;
  if(hash(canonical)!==hash(cache))throw Error('Stale camera mesh: '+part.name);
  paths.push(canonical,cache);
}
const sourceHashes=Object.fromEntries(paths.map(path=>[path,hash(path)]));
const bytes=readFileSync(new URL('../../simulation/browser/robot-physics.json',import.meta.url)),asset=JSON.parse(bytes);
const overrides=JSON.parse(process.env.APPROACH_OPTIONS??'{}');
const engine=await BrowserPhysics.create(asset,overrides.physics??{}),camera=new CpuCamera(asset);
const report={schemaVersion:2,sourceHashes,cameraParts:actual.length,verificationScope:'CAD-occluded CPU reference camera and shared physics/controller; no browser interaction or physical hardware qualification.',assetSha256:createHash('sha256').update(bytes).digest('hex'),physics:engine.options,gait:CAMERA_WADDLE_GAIT,parameters:{...DEFAULT_VISION_PARAMETERS,...overrides.parameters},episodes:[]};
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
for(const [path,expectedHash] of Object.entries(sourceHashes))if(hash(path)!==expectedHash)throw Error('Input changed during evaluation: '+path);
mkdirSync(new URL('../../work/',import.meta.url),{recursive:true});
writeFileSync(new URL(`../../work/${overrides.output??'approach-evaluation.json'}`,import.meta.url),JSON.stringify(report,null,2)+'\n');
