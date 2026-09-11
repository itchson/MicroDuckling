// SPDX-License-Identifier: Apache-2.0
import type {Gait,JointAngles,PhysicsAsset,SimulationFrame,TrainingProgress,Vec3} from './browser-physics';
import type {VisionObservation,VisionParameters} from './vision';
export type RunMode='paused'|'pose'|'gait'|'walk-learning'|'camera'|'camera-learning';
export type VisionProgress={trial:number;score:number;bestScore:number|null;parameters:VisionParameters;visibleFraction:number;coverageFraction:number;eligible:boolean;fall:boolean};
export type SimulationCommand=
 | {type:'init';asset:PhysicsAsset}
 | {type:'run';mode:RunMode}
 | {type:'reset'}
 | {type:'pose';angles:JointAngles}
 | {type:'target';position:Vec3}
 | {type:'observation';observation:VisionObservation;runId:number;frameTime:number};
export type SimulationEvent=
 | {type:'ready';frame:SimulationFrame;runId:number}
 | {type:'frame';frame:SimulationFrame;runId:number}
 | {type:'mode';mode:RunMode}
 | {type:'training';progress:TrainingProgress}
 | {type:'vision-training';progress:VisionProgress}
 | {type:'policy';gait:Gait;vision:VisionParameters}
 | {type:'error';message:string};
