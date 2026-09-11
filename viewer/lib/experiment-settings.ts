// SPDX-License-Identifier: Apache-2.0
import type {LocomotionGait} from './locomotion-controller';
import type {Vec3} from './browser-physics';

export type ManualGaitSettings={swingDeg:number;leanDeg:number;frequencyHz:number;phaseDeg:number;duty:number;headSwayDeg:number};
export const DEFAULT_MANUAL_GAIT:ManualGaitSettings={swingDeg:10,leanDeg:3,frequencyHz:2,phaseDeg:180,duty:.5,headSwayDeg:0};
export type SearchSettings={scanAmplitudeDeg:number;scanPeriodSeconds:number};
export type ExperimentSettings=SearchSettings&{cameraSeconds:number};
export const DEFAULT_EXPERIMENT:ExperimentSettings={cameraSeconds:60,scanAmplitudeDeg:45,scanPeriodSeconds:6};
function range(value:number,min:number,max:number,label:string){if(!Number.isFinite(value)||value<min||value>max)throw Error(`${label} must be between ${min} and ${max}`);}
export function manualGait(settings:ManualGaitSettings):LocomotionGait{
  const s=settings;range(s.swingDeg,0,12,'Step swing');range(s.leanDeg,-12,12,'Lean');range(s.frequencyHz,.3,4.5,'Pace');
  range(s.phaseDeg,0,360,'Leg phase');range(s.duty,.1,.9,'Step timing');range(s.headSwayDeg,0,45,'Head sway');
  const rad=Math.PI/180,amplitude=Math.min(s.swingDeg,12-Math.abs(s.leanDeg))*rad;
  return {frequencyHz:s.frequencyHz,leftBiasRad:-s.leanDeg*rad,rightBiasRad:-s.leanDeg*rad,
    leftAmplitudeRad:amplitude,rightAmplitudeRad:amplitude,phaseRad:-s.phaseDeg*rad,neckAmplitudeRad:s.headSwayDeg*rad,neckPhaseRad:0,
    waveform:{kind:'rocking',leftDuty:s.duty,rightDuty:s.duty,secondHarmonic:0,secondHarmonicPhaseRad:0,
      neckBiasRad:0,neckSecondHarmonic:0,neckHarmonicPhaseRad:0,jawAmplitudeRad:0,jawPhaseRad:0}};
}
export function validateExperiment(settings:ExperimentSettings):ExperimentSettings{
  range(settings.cameraSeconds,15,120,'Camera trial duration');range(settings.scanAmplitudeDeg,0,45,'Search sweep');range(settings.scanPeriodSeconds,2,12,'Search period');
  return {...settings};
}
/** Ground-level target in the editable forward training area, in metres. */
export function validateTarget(position:Vec3):Vec3{
  if(!Array.isArray(position)||position.length!==3)throw Error('Expected three target coordinates');
  range(position[0],.16,.6,'Forward target position');range(position[1],-.4,.4,'Side target position');
  if(position[2]!==.05)throw Error('Target must rest on the ground');return [...position];
}
export function targetFromGround(xMm:number,yMm:number):Vec3{
  if(!Number.isFinite(xMm)||!Number.isFinite(yMm))throw Error('Invalid ground position');
  return [Math.max(.16,Math.min(.6,Math.round(xMm)/1000)),Math.max(-.4,Math.min(.4,Math.round(yMm)/1000)),.05];
}
