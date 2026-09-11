// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve} from 'node:path';
import {pathToFileURL, fileURLToPath} from 'node:url';

export const repo = resolve(process.argv[2] ?? fileURLToPath(new URL('../../../',import.meta.url)));
export const files = ['simulation/browser/robot-physics.json','viewer/lib/browser-physics.ts',
  'viewer/lib/locomotion-controller.ts','viewer/lib/rocking-trainer.ts'];
export const hash = data => createHash('sha256').update(data).digest('hex');
export async function fingerprints() {
  return Object.fromEntries(await Promise.all(files.map(async file => [file, hash(await readFile(resolve(repo,file)))])));
}
export const startingHashes = await fingerprints();
if(process.env.EXPECTED_ASSET_SHA256)assert.equal(startingHashes[files[0]],process.env.EXPECTED_ASSET_SHA256,'Unexpected physics asset');
export const asset = JSON.parse(await readFile(resolve(repo, files[0]), 'utf8'));
export const {BrowserPhysics} = await import(pathToFileURL(resolve(repo, files[1])).href);
export const {CAMERA_WADDLE_GAIT, locomotionTargets} = await import(pathToFileURL(resolve(repo, files[2])).href);
export const {RockingTrainer} = await import(pathToFileURL(resolve(repo, files[3])).href);
export const ZERO = {left_hip:0,right_hip:0,neck_yaw:0,jaw_pitch:0};
export function com(frame) {
  const result=[0,0,0];
  for(const link of asset.links) {
    const pose=frame.links[link.name], [x,y,z,w]=pose.quaternion, [a,b,c]=link.comM;
    const tx=2*(y*c-z*b),ty=2*(z*a-x*c),tz=2*(x*b-y*a);
    const offset=[a+w*tx+y*tz-z*ty,b+w*ty+z*tx-x*tz,c+w*tz+x*ty-y*tx];
    for(let axis=0;axis<3;axis++)result[axis]+=(pose.position[axis]+offset[axis])*link.massKg/asset.totalMassKg;
  }
  return result;
}
export function slope(samples, axis) {
  if(samples.length<2)return 0;
  const mt=samples.reduce((s,r)=>s+r.t,0)/samples.length;
  const mx=samples.reduce((s,r)=>s+r.com[axis],0)/samples.length;
  let top=0,bottom=0;
  for(const r of samples){top+=(r.t-mt)*(r.com[axis]-mx);bottom+=(r.t-mt)**2;}
  return bottom?top/bottom:0;
}
export function compactEpisode(result) {
  return {seed:result.seed,durationSeconds:result.durationSeconds,score:result.score,distanceM:result.distanceM,
    lateralM:result.lateralM,fall:result.fall,maxTiltRad:result.maxTiltRad,
    maxJointLimitViolationRad:result.maxJointLimitViolationRad,lateForwardSpeedMps:result.lateForwardSpeedMps,
    lateLateralSpeedMps:result.lateLateralSpeedMps,rmsHeadingRad:result.rmsHeadingRad,rmsTiltRad:result.rmsTiltRad};
}
export async function save(name, report) {
  const endingHashes=await fingerprints();
  assert.deepEqual(endingHashes,startingHashes,'Canonical inputs changed during evaluation');
  const result={assetSha256:startingHashes[files[0]],moduleSha256:startingHashes,
    totalMassKg:asset.totalMassKg,inputHashesUnchanged:true,...report};
  const output=resolve(repo,'work/locomotion-verification');await mkdir(output,{recursive:true});
  await writeFile(resolve(output,name),JSON.stringify(result,null,2)+'\n');
  return result;
}
