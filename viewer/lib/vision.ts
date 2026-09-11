// SPDX-License-Identifier: Apache-2.0
// Image-only synthetic-camera experiment. No target world coordinates enter this API.
import {locomotionTargets} from './locomotion-controller.ts';
import type {Gait,JointAngles} from './browser-physics.ts';
import {DEFAULT_EXPERIMENT,type SearchSettings} from './experiment-settings.ts';

export type VisionObservation = {visible: boolean; bearingRad: number; areaFraction: number;widthFraction?:number};
export type VisionParameters = {headGain: number; turnGain: number; forwardScale: number;stopWidthFraction?:number};
export type CameraMetrics = {visibleFraction: number; meanAbsBearingRad: number; initialArea: number; finalArea: number; fall: boolean};
export const DEFAULT_VISION_PARAMETERS: VisionParameters = {headGain: 3.5,turnGain: -.08,forwardScale: 1,stopWidthFraction:.63};
const HIP_LIMIT=Math.PI/15,NECK_LIMIT=Math.PI/4;
const clamp=(x: number,a: number,b: number)=>Math.max(a,Math.min(b,x));
function finite(x: number,label: string): number {if(!Number.isFinite(x))throw Error(`${label} must be finite`);return x;}

/** Detect the largest four-connected magenta region in an RGBA camera image.
 * WebGL's bottom-up row order does not change the horizontal bearing or area.
 * A four-pixel minimum rejects isolated colored noise; this is a color heuristic,
 * not a learned object recognizer or a detector robust to arbitrary lighting.
 */
export function detectTarget(pixels: Uint8Array,width: number,height: number,verticalFovRad: number): VisionObservation {
  if(!Number.isSafeInteger(width)||!Number.isSafeInteger(height)||width<1||height<1||width*height>16_777_216)throw Error('Invalid image dimensions');
  if(pixels.length!==width*height*4)throw Error('Expected width * height * 4 RGBA bytes');
  if(!Number.isFinite(verticalFovRad)||verticalFovRad<=0||verticalFovRad>=Math.PI)throw Error('Vertical field of view must be between zero and pi');
  const count=width*height,mask=new Uint8Array(count),queue=new Int32Array(count);
  for(let i=0;i<count;i++){
    const red=pixels[i*4],green=pixels[i*4+1],blue=pixels[i*4+2],alpha=pixels[i*4+3];
    if(alpha>0&&red>=80&&blue>=100&&green<Math.min(red,blue)*.72&&blue>green*1.45&&red>green*1.3)mask[i]=1;
  }
  let largest=0,largestX=0,largestWidth=0;
  for(let i=0;i<count;i++){
    if(!mask[i])continue;
    let read=0,write=1,sumX=0,minX=width,maxX=0;queue[0]=i;mask[i]=0;
    while(read<write){
      const p=queue[read++],x=p%width;sumX+=x+.5;minX=Math.min(minX,x);maxX=Math.max(maxX,x);
      if(x>0&&mask[p-1]){mask[p-1]=0;queue[write++]=p-1;}
      if(x+1<width&&mask[p+1]){mask[p+1]=0;queue[write++]=p+1;}
      if(p>=width&&mask[p-width]){mask[p-width]=0;queue[write++]=p-width;}
      if(p+width<count&&mask[p+width]){mask[p+width]=0;queue[write++]=p+width;}
    }
    if(write>largest){largest=write;largestX=sumX;largestWidth=maxX-minX+1;}
  }
  if(largest<4)return {visible:false,bearingRad:0,areaFraction:0};
  const normalizedX=2*(largestX/largest)/width-1;
  const tanHalfHorizontalFov=Math.tan(verticalFovRad/2)*(width/height);
  return {visible:true,bearingRad:-Math.atan(normalizedX*tanHalfHorizontalFov),areaFraction:largest/count,widthFraction:largestWidth/width};
}

/** Bounded gaze and gait commands from image observations and command history only.
 * turnGain may have either sign: the effect of differential hip bias depends on
 * contact dynamics and must be evaluated rather than assumed to steer correctly.
 */
export function visionTargets(observation: VisionObservation,params: VisionParameters,gait: Gait,time: number,dt: number,previousNeckRad: number,stopLatch=false,search:SearchSettings=DEFAULT_EXPERIMENT): JointAngles {
  finite(time,'time');finite(previousNeckRad,'previousNeckRad');finite(dt,'dt');
  if(dt<0||dt>1)throw Error('dt must be between zero and one second');
  for(const [key,value] of Object.entries(params))finite(value,key);
  finite(observation.bearingRad,'bearingRad');finite(observation.areaFraction,'areaFraction');
  if(observation.areaFraction<0||observation.areaFraction>1)throw Error('areaFraction must be in [0, 1]');
  const previous=clamp(previousNeckRad,-NECK_LIMIT,NECK_LIMIT);
  if(!observation.visible){
    if(!Number.isFinite(search.scanAmplitudeDeg)||search.scanAmplitudeDeg<0||search.scanAmplitudeDeg>45||!Number.isFinite(search.scanPeriodSeconds)||search.scanPeriodSeconds<2||search.scanPeriodSeconds>12)throw Error('Invalid camera search sweep');
    const scan=search.scanAmplitudeDeg*Math.PI/180*Math.sin(2*Math.PI*time/search.scanPeriodSeconds);
    return {left_hip:0,right_hip:0,neck_yaw:clamp(previous+clamp(scan-previous,-.8*dt,.8*dt),-NECK_LIMIT,NECK_LIMIT),jaw_pitch:0};
  }
  const bearing=clamp(observation.bearingRad,-Math.PI/2,Math.PI/2);
  const neck=clamp(previous+clamp(params.headGain,.1,12)*bearing*dt,-NECK_LIMIT,NECK_LIMIT);
  const close=observation.widthFraction!==undefined?observation.widthFraction>=(params.stopWidthFraction??.6):observation.areaFraction>=.16;
  if(stopLatch||close)return {left_hip:0,right_hip:0,neck_yaw:neck,jaw_pitch:0};
  const base=locomotionTargets(gait,time),scale=clamp(params.forwardScale,0,1.5);
  // Neck command + camera-relative bearing is a command-based body bearing estimate.
  // It uses no ground-truth robot yaw, target coordinate or measured joint angle.
  const bodyBearing=clamp(previous+bearing,-Math.PI/2,Math.PI/2);
  const turn=clamp(clamp(params.turnGain,-.6,.6)*bodyBearing,-.11,.11);
  return {left_hip:clamp(base.left_hip*scale+turn,-HIP_LIMIT,HIP_LIMIT),
    right_hip:clamp(base.right_hip*scale-turn,-HIP_LIMIT,HIP_LIMIT),neck_yaw:neck,jaw_pitch:base.jaw_pitch};
}

/** Pixel-only episode score. The caller must accumulate visibility and bearing
 * from observed camera frames; target world-distance must not be substituted.
 * Area growth is an apparent-size proxy, so this is not a distance estimator.
 */
export function cameraScore(metrics: CameraMetrics): number {
  const {visibleFraction,meanAbsBearingRad,initialArea,finalArea,fall}=metrics;
  for(const [label,value] of Object.entries({visibleFraction,meanAbsBearingRad,initialArea,finalArea}))finite(value,label);
  if(visibleFraction<0||visibleFraction>1||initialArea<0||initialArea>1||finalArea<0||finalArea>1||meanAbsBearingRad<0)throw Error('Invalid camera metrics');
  const visibility=visibleFraction;
  // Cap apparent-size reward at the stop threshold so filling the view cannot
  // indefinitely improve reward. Loss of visibility removes area/centering gains.
  const growth=clamp(finalArea,0,.09)-clamp(initialArea,0,.09);
  return 2*visibility-1.5*visibility*Math.min(meanAbsBearingRad,Math.PI/2)+20*visibility*growth-(fall?6:0);
}

/** Deterministic bounded perturbation for a caller-owned best-score search.
 * Trial zero reproduces the default/best candidate. This function does not
 * choose a winner, fabricate a score or modify the previous parameter object.
 */
export function proposeVisionParameters(best: VisionParameters,trial: number): VisionParameters {
  if(!Number.isSafeInteger(trial)||trial<0)throw Error('trial must be a nonnegative integer');
  for(const [key,value] of Object.entries(best))finite(value,key);
  let state=((trial+1)*0x9E3779B1)>>>0;
  const random=()=>{state=(state+0x6D2B79F5)|0;let t=Math.imul(state^(state>>>15),1|state);t^=t+Math.imul(t^(t>>>7),61|t);return ((t^(t>>>14))>>>0)/4294967296;};
  const spread=Math.max(.35,1/Math.sqrt(1+trial/12));
  const headGain=clamp(best.headGain,.1,12),turnGain=clamp(best.turnGain,-.6,.6),forwardScale=clamp(best.forwardScale,0,1.5);
  const stopWidthFraction=clamp(best.stopWidthFraction??.6,.4,.85);
  if(trial===0)return {headGain,turnGain,forwardScale,stopWidthFraction};
  // Periodically explore the opposite steering sign rather than locking in an
  // unverified contact-to-turn mapping from the default parameters.
  const turnCenter=trial%4===0?-turnGain:turnGain;
  return {headGain:clamp(headGain*Math.exp((random()-.5)*1.2*spread),.1,12),
    turnGain:clamp(turnCenter+(random()-.5)*.5*spread,-.6,.6),
    forwardScale:clamp(forwardScale+(random()-.5)*.12*spread,.9,1.1),
    stopWidthFraction:clamp(stopWidthFraction+(random()-.5)*.15*spread,.4,.85)};
}
