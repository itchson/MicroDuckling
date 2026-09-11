// SPDX-License-Identifier: Apache-2.0
// Bounded, open-loop contact-driven rocking. Browser experiment, not a hardware policy.
import {gaitTargets as sineTargets} from './browser-physics.ts';
import type {Gait,JointAngles} from './browser-physics.ts';

export type LocomotionGait = Gait & {
  waveform?: {kind:'rocking';leftDuty:number;rightDuty:number;secondHarmonic:number;secondHarmonicPhaseRad:number;
    neckBiasRad:number;neckSecondHarmonic:number;neckHarmonicPhaseRad:number;jawAmplitudeRad:number;jawPhaseRad:number};
};
export const SUSTAINED_ROCKING_GAIT: LocomotionGait = {
  frequencyHz:2.310670318909374,leftBiasRad:.15970037935726408,rightBiasRad:.15970037935726408,
  leftAmplitudeRad:.31062621767741105,rightAmplitudeRad:.31062621767741105,phaseRad:0,
  neckAmplitudeRad:0,neckPhaseRad:0,
  waveform:{kind:'rocking',leftDuty:.19389274847242277,rightDuty:.19389274847242277,
    secondHarmonic:.8,secondHarmonicPhaseRad:.8355450655217753,neckBiasRad:0,neckSecondHarmonic:0,
    neckHarmonicPhaseRad:0,jawAmplitudeRad:.04394034303838219,jawPhaseRad:-Math.PI},
};
/** Offline candidate evaluated with convex soles, 600 Hz, 16 solver iterations.
 * Neck is reserved for the image controller. Open-loop heading still drifts.
 * Bundling this candidate is a warm start, not evidence of a new training run.
 */
export const CAMERA_WADDLE_GAIT: LocomotionGait = {
  frequencyHz:3.8304913002694954,leftBiasRad:-.1108688045712188,rightBiasRad:-.1108688045712188,
  leftAmplitudeRad:.3316799990083091,rightAmplitudeRad:.3316799990083091,phaseRad:-Math.PI,
  neckAmplitudeRad:0,neckPhaseRad:0,
  waveform:{kind:'rocking',leftDuty:.8228959879353177,rightDuty:.8228959879353177,
    secondHarmonic:.8855480271391571,secondHarmonicPhaseRad:Math.PI,neckBiasRad:0,neckSecondHarmonic:0,
    neckHarmonicPhaseRad:0,jawAmplitudeRad:0,jawPhaseRad:0},
};
const HIP=Math.PI/15,NECK=Math.PI/4;
const clip=(x:number,min:number,max:number)=>Math.max(min,Math.min(max,x));
function wave(phase:number,duty:number):number {
  const f=((phase/(2*Math.PI))%1+1)%1;
  const angle=f<duty?Math.PI*f/duty:Math.PI+Math.PI*(f-duty)/(1-duty);
  return Math.cos(angle);
}
/** Existing sine gaits remain compatible. Bias/amplitude are waveform parameters;
 * final motor commands always respect the mechanical joint limits.
 * Evaluate at 50–60 Hz even when a camera observation is held for 100 ms.
 */
export function locomotionTargets(gait:LocomotionGait,time:number,steerRad=0):JointAngles {
  if(!gait.waveform)return sineTargets(gait,time);
  const w=gait.waveform;
  if(!Number.isFinite(time)||!Number.isFinite(steerRad)||Object.values(gait).some(v=>typeof v==='number'&&!Number.isFinite(v))||Object.values(w).some(v=>typeof v==='number'&&!Number.isFinite(v)))throw Error('Nonfinite rocking command');
  if(w.leftDuty<=0||w.leftDuty>=1||w.rightDuty<=0||w.rightDuty>=1)throw Error('Duty cycle must be inside (0,1)');
  const phase=2*Math.PI*gait.frequencyHz*time;
  const left=wave(phase,w.leftDuty)+w.secondHarmonic*Math.sin(2*phase+w.secondHarmonicPhaseRad);
  const right=wave(phase+gait.phaseRad,w.rightDuty)+w.secondHarmonic*Math.sin(2*(phase+gait.phaseRad)+w.secondHarmonicPhaseRad);
  return {left_hip:clip(gait.leftBiasRad+gait.leftAmplitudeRad*left+steerRad,-HIP,HIP),
    right_hip:clip(gait.rightBiasRad+gait.rightAmplitudeRad*right-steerRad,-HIP,HIP),
    neck_yaw:clip(w.neckBiasRad+gait.neckAmplitudeRad*(Math.sin(phase+gait.neckPhaseRad)+w.neckSecondHarmonic*Math.sin(2*phase+w.neckHarmonicPhaseRad)),-NECK,NECK),
    jaw_pitch:clip(w.jawAmplitudeRad*(.5+.5*Math.sin(phase+w.jawPhaseRad)),0,HIP)};
}
