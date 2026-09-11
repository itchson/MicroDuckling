// SPDX-License-Identifier: Apache-2.0
import {BrowserPhysics,NEUTRAL_GAIT} from './browser-physics.ts';
import type {EpisodeResult,SimulationFrame,TrainingProgress,TrainerOptions,Vec3} from './browser-physics.ts';
import {locomotionTargets,CAMERA_WADDLE_GAIT} from './locomotion-controller.ts';
import type {LocomotionGait} from './locomotion-controller.ts';

export type RockingEpisode = EpisodeResult & {lateForwardSpeedMps:number;lateLateralSpeedMps:number;rmsHeadingRad:number;rmsTiltRad:number};
export type RockingProgress = TrainingProgress & {baseline:RockingEpisode;best:RockingEpisode;seed:RockingEpisode;
  bestGait:LocomotionGait;seedGait:LocomotionGait;improvedOverSeed:boolean;scoreImprovementOverSeed:number;
  improvementOverSeedM:number;bestOrigin:'provided-seed'|'search'|'neutral'};
export type RockingTrainerOptions = TrainerOptions & {seedGait?:LocomotionGait};
const LIMIT=Math.PI/15;
const BOUNDS:[number,number][]=[[.3,4.5],[-.18,.18],[.08,.36],[-Math.PI,Math.PI],[.08,.92],[-1,1],[-Math.PI,Math.PI],[0,LIMIT],[-Math.PI,Math.PI]];
const clip=(x:number,a:number,b:number)=>Math.max(a,Math.min(b,x));
const vector=(g:LocomotionGait)=>[g.frequencyHz,g.leftBiasRad,g.leftAmplitudeRad,g.phaseRad,g.waveform?.leftDuty??.5,g.waveform?.secondHarmonic??0,
  g.waveform?.secondHarmonicPhaseRad??0,g.waveform?.jawAmplitudeRad??0,g.waveform?.jawPhaseRad??0];
function fromVector(p:number[]):LocomotionGait {return {frequencyHz:p[0],leftBiasRad:p[1],rightBiasRad:p[1],leftAmplitudeRad:p[2],rightAmplitudeRad:p[2],
  phaseRad:p[3],neckAmplitudeRad:0,neckPhaseRad:0,waveform:{kind:'rocking',leftDuty:p[4],rightDuty:p[4],secondHarmonic:p[5],secondHarmonicPhaseRad:p[6],
    neckBiasRad:0,neckSecondHarmonic:0,neckHarmonicPhaseRad:0,jawAmplitudeRad:p[7],jawPhaseRad:p[8]}};}
function seeded(seed:number):()=>number {let s=seed>>>0;return()=>{s=(s+0x6d2b79f5)|0;let t=Math.imul(s^(s>>>15),1|s);t^=t+Math.imul(t^(t>>>7),61|t);return((t^(t>>>14))>>>0)/4294967296;};}
function rotated(q:number[],v:Vec3):Vec3 {const[x,y,z,w]=q,[a,b,c]=v;const ix=w*a+y*c-z*b,iy=w*b+z*a-x*c,iz=w*c+x*b-y*a,iw=-x*a-y*b-z*c;return[ix*w-iw*x-iy*z+iz*y,iy*w-iw*y-iz*x+ix*z,iz*w-iw*z-ix*y+iy*x];}
function centerOfMass(engine:BrowserPhysics,frame:SimulationFrame):Vec3 {const result:Vec3=[0,0,0];for(const link of engine.asset.links){const pose=frame.links[link.name],offset=rotated(pose.quaternion,link.comM);for(let a=0;a<3;a++)result[a]+=(pose.position[a]+offset[a])*link.massKg/engine.asset.totalMassKg;}return result;}
function slope(samples:{t:number;com:Vec3}[],axis:number):number {if(samples.length<2)return 0;const mt=samples.reduce((s,r)=>s+r.t,0)/samples.length,mx=samples.reduce((s,r)=>s+r.com[axis],0)/samples.length;let a=0,b=0;for(const r of samples){a+=(r.t-mt)*(r.com[axis]-mx);b+=(r.t-mt)**2;}return b?a/b:0;}

/** Evaluates neutral and the supplied seed explicitly, then searches real physical
 * episodes. "improvedOverSeed" remains false unless a newly evaluated candidate
 * beats the seed; merely replaying a bundled candidate is not labeled learning.
 */
export class RockingTrainer {
  private engine:BrowserPhysics;
  private options:Required<Omit<RockingTrainerOptions,'onFrame'|'onEpisode'|'seedGait'>> & Pick<RockingTrainerOptions,'onFrame'|'onEpisode'>;
  private suppliedSeed:LocomotionGait;
  private random:()=>number;
  private mean:number[];
  private sigma=BOUNDS.map(([a,b])=>(b-a)*.09);
  private baseline?:RockingEpisode;
  private seedResult?:RockingEpisode;
  private best?:RockingEpisode;
  private origin:'provided-seed'|'search'|'neutral'='neutral';
  private count=0;
  private generation=0;
  constructor(engine:BrowserPhysics,options:RockingTrainerOptions={}) {
    this.engine=engine;this.options={seed:options.seed??2026,population:options.population??12,elite:options.elite??3,
      episodeSeconds:options.episodeSeconds??14,onFrame:options.onFrame,onEpisode:options.onEpisode};
    if(!Number.isInteger(this.options.population)||this.options.population<3||this.options.population>64||!Number.isInteger(this.options.elite)||this.options.elite<2||this.options.elite>=this.options.population)throw Error('Invalid rocking population/elite counts');
    if(!Number.isFinite(this.options.episodeSeconds)||this.options.episodeSeconds<6||this.options.episodeSeconds>60)throw Error('Rocking evaluation requires6..60seconds');
    this.suppliedSeed=structuredClone(options.seedGait??CAMERA_WADDLE_GAIT);this.mean=vector(this.suppliedSeed);this.random=seeded(this.options.seed);
  }
  private normal():number {return Math.sqrt(-2*Math.log(Math.max(1e-12,this.random())))*Math.cos(2*Math.PI*this.random());}
  private evaluate(gait:LocomotionGait,index:number):RockingEpisode {
    this.engine.reset({seed:this.options.seed,perturbationRad:.002});
    for(let i=0;i<60;i++)this.engine.step(1/60,{left_hip:0,right_hip:0,neck_yaw:0,jaw_pitch:0});
    const start=this.engine.frame(),initial=centerOfMass(this.engine,start),seconds=this.options.episodeSeconds,warmup=Math.min(5,seconds/3);
    const samples:{t:number;com:Vec3}[]=[];let frame=start,maxTilt=0,tiltSum=0,headingSum=0,n=0,nextSample=0,nextEmit=0;
    for(let i=0;i<Math.round(seconds*60)&&!frame.metrics.fall;i++){
      const t=(i+1)/60;frame=this.engine.step(1/60,locomotionTargets(gait,i/60));maxTilt=Math.max(maxTilt,frame.metrics.tiltRad);
      if(t>=warmup){tiltSum+=frame.metrics.tiltRad**2;headingSum+=frame.metrics.headingRad**2;n++;}
      if(t>=nextSample){nextSample+=.25;if(t>=warmup)samples.push({t,com:centerOfMass(this.engine,frame)});}
      if(t>=nextEmit){nextEmit+=.15;this.options.onFrame?.(frame);}
    }
    this.options.onFrame?.(frame);
    const final=centerOfMass(this.engine,frame),vx=slope(samples,0),vy=slope(samples,1),rmsHeading=Math.sqrt(headingSum/Math.max(1,n)),rmsTilt=Math.sqrt(tiltSum/Math.max(1,n));
    const complete=!frame.metrics.fall&&frame.time-start.time>=seconds-.05&&samples.length>=8;
    const score=complete?1000*(.65*vx+.35*(final[0]-initial[0])/seconds-.5*Math.abs(vy))-.8*rmsTilt**2-25*rmsHeading**2:-1000;
    const result:RockingEpisode={gait,seed:this.options.seed,durationSeconds:frame.time-start.time,score,distanceM:final[0]-initial[0],lateralM:final[1]-initial[1],
      fall:frame.metrics.fall,maxTiltRad:maxTilt,maxJointLimitViolationRad:frame.metrics.maxJointLimitViolationRad,finalFrame:frame,
      lateForwardSpeedMps:vx,lateLateralSpeedMps:vy,rmsHeadingRad:rmsHeading,rmsTiltRad:rmsTilt};
    this.count++;this.options.onEpisode?.(result,index);return result;
  }
  stepGeneration():RockingProgress {
    if(!this.baseline){
      this.baseline=this.evaluate(NEUTRAL_GAIT,-2);this.seedResult=this.evaluate(this.suppliedSeed,-1);
      this.best=this.seedResult.score>this.baseline.score?this.seedResult:this.baseline;
      this.origin=this.best===this.seedResult?'provided-seed':'neutral';
    }
    const results:RockingEpisode[]=[];
    for(let n=0;n<this.options.population;n++){
      let gait:LocomotionGait;
      if(n===0)gait=fromVector(vector(this.best!.gait as LocomotionGait));
      else if(n===this.options.population-1)gait=fromVector(BOUNDS.map(([a,b])=>a+this.random()*(b-a)));
      else gait=fromVector(this.mean.map((m,i)=>clip(m+this.sigma[i]*this.normal(),...BOUNDS[i])));
      const result=this.evaluate(gait,n);results.push(result);
      if(result.score>this.best!.score+1e-9){this.best=result;this.origin='search';}
    }
    const sorted=[...results].sort((a,b)=>b.score-a.score),elites=sorted.slice(0,this.options.elite);
    for(let i=0;i<BOUNDS.length;i++){
      const values=elites.map(r=>vector(r.gait as LocomotionGait)[i]),mean=values.reduce((s,x)=>s+x,0)/values.length;
      const sd=Math.sqrt(values.reduce((s,x)=>s+(x-mean)**2,0)/values.length);
      this.mean[i]=.2*this.mean[i]+.8*mean;this.sigma[i]=Math.max((BOUNDS[i][1]-BOUNDS[i][0])*.018,.2*this.sigma[i]+.8*sd);
    }
    this.generation++;const best=this.best!,baseline=this.baseline!,seed=this.seedResult!;
    const improved=!best.fall&&best.distanceM-baseline.distanceM>.002&&best.score>baseline.score+.1;
    const improvedOverSeed=this.origin==='search'&&!best.fall&&best.score>seed.score+.1&&best.lateForwardSpeedMps>seed.lateForwardSpeedMps+.0001;
    return {generation:this.generation,episodesEvaluated:this.count,baseline,best,seed,bestGait:structuredClone(best.gait as LocomotionGait),
      seedGait:structuredClone(this.suppliedSeed),generationBest:sorted[0],meanScore:results.reduce((s,r)=>s+r.score,0)/results.length,
      bestDistanceM:best.distanceM,improvementM:best.distanceM-baseline.distanceM,scoreImprovement:best.score-baseline.score,
      improved,status:improved?'improved-in-this-model':'no-improvement',candidates:results.map(r=>({score:r.score,distanceM:r.distanceM,fall:r.fall})),
      improvedOverSeed,scoreImprovementOverSeed:best.score-seed.score,improvementOverSeedM:best.distanceM-seed.distanceM,bestOrigin:this.origin};
  }
}
