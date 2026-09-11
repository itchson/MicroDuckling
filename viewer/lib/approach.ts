// SPDX-License-Identifier: Apache-2.0
import {BrowserPhysics,type PhysicsAsset,type SimulationFrame,type Vec3} from './browser-physics.ts';
import {createGoalState,goalMetrics,goalScore,type GoalState,type GoalMetrics} from './goal-metrics.ts';
import {visionTargets,type VisionObservation,type VisionParameters} from './vision.ts';
import type {LocomotionGait} from './locomotion-controller.ts';

export type GoalDisplay=Omit<GoalMetrics,'state'>;
export type ApproachResult={frame:SimulationFrame;goal:GoalDisplay;finished:boolean;score:number;observations:number;visibleFraction:number;coverageFraction:number;eligible:boolean};
const ZERO={left_hip:0,right_hip:0,neck_yaw:0,jaw_pitch:0};

/** One causal image/control loop, shared by the browser worker and offline evaluation.
 * The environment evaluates physical travel. The actor sees pixels and command history only.
 */
export class ApproachEpisode {
  readonly engine:BrowserPhysics;
  readonly gait:LocomotionGait;
  readonly parameters:VisionParameters;
  readonly target:Vec3;
  readonly maxSeconds:number;
  private state:GoalState;
  private neck=0;
  private width=0;
  private stopped=false;
  private observations=0;
  private visibleSeconds=0;
  private coveredSeconds=0;
  private result:ApproachResult;
  constructor(engine:BrowserPhysics,asset:PhysicsAsset,gait:LocomotionGait,parameters:VisionParameters,target:Vec3,options:{seed?:number;seconds?:number}={}){
    this.engine=engine;this.gait=gait;this.parameters=parameters;this.target=target;this.maxSeconds=options.seconds??60;
    engine.reset({seed:options.seed??2026,perturbationRad:.002});engine.setTarget(target,[.025,.025,.05]);
    for(let i=0;i<60;i++)engine.step(1/60,ZERO);
    const frame=engine.frame();this.state=createGoalState(frame,target,{rootLocalComM:asset.links.find(link=>link.name==='body')!.comM});
    const {state,...goal}=goalMetrics(frame,target,this.state.initialDistanceM,0,this.state);this.state=state;
    this.result={frame,goal,finished:false,score:0,observations:0,visibleFraction:0,coverageFraction:0,eligible:false};
  }
  current():ApproachResult{return this.result;}
  /** A missing or stale image cannot advance time or qualify a training episode. */
  observe(observation:VisionObservation,frameTime:number):ApproachResult {
    if(this.result.finished)return this.result;
    if(!Number.isFinite(frameTime)||Math.abs(frameTime-this.engine.frame().time)>1e-6)throw Error('Camera image must match the current physics frame');
    if(observation.widthFraction!==undefined&&(!Number.isFinite(observation.widthFraction)||observation.widthFraction<0||observation.widthFraction>1))throw Error('Invalid target width');
    this.observations++;
    if(observation.visible&&observation.widthFraction!==undefined){
      this.width=this.width===0?observation.widthFraction:.75*this.width+.25*observation.widthFraction;
      const threshold=this.parameters.stopWidthFraction??.6;
      if(this.width>=threshold)this.stopped=true;
      else if(this.width<threshold*.72)this.stopped=false;
    }
    const filtered={...observation,widthFraction:observation.widthFraction!==undefined?this.width:undefined};
    let frame=this.engine.frame(),goal=this.result.goal;
    // Keep 60 Hz actuator commands while holding the captured image for 100 ms.
    for(let i=0;i<6;i++){
      const time=frame.time-this.state.initialTime;
      const commands=visionTargets(filtered,this.parameters,this.gait,time,1/60,this.neck,this.stopped);this.neck=commands.neck_yaw;
      const before=frame.time;frame=this.engine.step(1/60,commands);const dt=frame.time-before;
      this.coveredSeconds+=dt;if(observation.visible)this.visibleSeconds+=dt;
      const measured=goalMetrics(frame,this.target,this.state.initialDistanceM,dt,this.state);this.state=measured.state;
      const {state:_,...display}=measured;goal=display;
      if(goal.success||goal.fallen||goal.elapsedSeconds>=this.maxSeconds)break;
    }
    const elapsed=goal.elapsedSeconds,coverageFraction=Math.min(1,this.coveredSeconds/Math.max(elapsed,1e-9));
    this.result={frame,goal,finished:goal.success||goal.fallen||elapsed>=this.maxSeconds,score:goalScore(goal),
      observations:this.observations,visibleFraction:Math.min(1,this.visibleSeconds/Math.max(elapsed,1e-9)),coverageFraction,
      eligible:coverageFraction>=.5&&this.observations>=10&&!goal.fallen};
    return this.result;
  }
}
