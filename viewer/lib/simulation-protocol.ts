// SPDX-License-Identifier: Apache-2.0
import type {JointAngles,PhysicsAsset,SimulationFrame,Vec3} from './browser-physics';
import type {LocomotionGait} from './locomotion-controller';
import type {RockingProgress} from './rocking-trainer';
import type {GoalDisplay} from './approach';
import type {VisionObservation,VisionParameters} from './vision';
export type RunMode='paused'|'pose'|'gait'|'walk-learning'|'camera'|'camera-learning';
export type EnvironmentSettings={groundFriction:number;massScale:number};
export type VisionProgress={trial:number;score:number;bestScore:number|null;parameters:VisionParameters;visibleFraction:number;coverageFraction:number;eligible:boolean;fall:boolean;goal:GoalDisplay};
export type SimulationCommand=
 | {type:'init';asset:PhysicsAsset}
 | {type:'run';mode:RunMode}
 | {type:'reset'}
 | {type:'environment';settings:EnvironmentSettings}
 | {type:'pose';angles:JointAngles}
 | {type:'target';position:Vec3}
 | {type:'observation';observation:VisionObservation;runId:number;frameTime:number};
export type SimulationEvent=
 | {type:'ready';frame:SimulationFrame;runId:number;goal?:GoalDisplay}
 | {type:'frame';frame:SimulationFrame;runId:number;goal?:GoalDisplay}
 | {type:'mode';mode:RunMode}
 | {type:'training';progress:RockingProgress}
 | {type:'vision-training';progress:VisionProgress}
 | {type:'policy';gait:LocomotionGait;vision:VisionParameters}
 | {type:'error';message:string};
