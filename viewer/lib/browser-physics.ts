// SPDX-License-Identifier: Apache-2.0
// A browser/Node Rapier experiment. It is not an Isaac policy or hardware controller.
import RAPIER from '@dimforge/rapier3d-compat';

export type Vec3 = [number, number, number];
export type Quat = [number, number, number, number]; // x, y, z, w
export type LinkName = 'body' | 'left_leg' | 'right_leg' | 'head' | 'jaw';
export type JointName = 'left_hip' | 'right_hip' | 'neck_yaw' | 'jaw_pitch';
export type JointAngles = Record<JointName, number>; // radians
export type LinkPose = {position: Vec3; quaternion: Quat};
export type PhysicsAsset = {
  schemaVersion: number; units: string; totalMassKg: number;
  cadZeroOriginsM: Record<LinkName, Vec3>;
  links: {name: LinkName; massKg: number; comM: Vec3; principalInertiaKgM2: Vec3; inertiaFrame: Quat;
    colliders: {name: string; halfExtentsM: Vec3; positionM: Vec3; quaternion: Quat}[]}[];
  joints: {name: JointName; parent: LinkName; child: LinkName; parentAnchorM: Vec3; childAnchorM: Vec3;
    axis: Vec3; limitsRad: [number, number]; motor: {stiffnessNmPerRad: number; dampingNmsPerRad: number;
      maxTorqueNm: number; noLoadSpeedRadS: number; commandRateRadS: number}}[];
  contactModel: {friction: number};
};
export type Metrics = {distanceM: number; lateralM: number; headingRad: number; tiltRad: number;
  fall: boolean; reward: number; maxTiltRad: number; maxJointLimitViolationRad: number};
export type SimulationFrame = {
  time: number; links: Record<LinkName, LinkPose>; jointAngles: JointAngles; targets: JointAngles;
  metrics: Metrics; estimatedMotorTorquesNm: JointAngles;
};
export type PhysicsOptions = {fixedDt?: number; gravityMps2?: number; friction?: number; motorsEnabled?: boolean};
export type ResetOptions = {seed?: number; dropHeightM?: number; baseRotation?: Quat; perturbationRad?: number};
export type Gait = {frequencyHz: number; leftAmplitudeRad: number; rightAmplitudeRad: number;
  phaseRad: number; leftBiasRad: number; rightBiasRad: number; neckAmplitudeRad: number; neckPhaseRad: number};
export type EpisodeOptions = {seconds?: number; settleSeconds?: number; seed?: number; frameIntervalSeconds?: number;
  onFrame?: (frame: SimulationFrame) => void};
export type EpisodeResult = {gait: Gait; seed: number; durationSeconds: number; score: number; distanceM: number;
  lateralM: number; fall: boolean; maxTiltRad: number; maxJointLimitViolationRad: number; finalFrame: SimulationFrame};

const JOINTS: JointName[] = ['left_hip', 'right_hip', 'neck_yaw', 'jaw_pitch'];
const LINKS: LinkName[] = ['body', 'left_leg', 'right_leg', 'head', 'jaw'];
const HIP = Math.PI / 15;
const ZERO: JointAngles = {left_hip: 0, right_hip: 0, neck_yaw: 0, jaw_pitch: 0};
export const DEFAULT_GAIT: Gait = {frequencyHz: 1.6, leftAmplitudeRad: .13, rightAmplitudeRad: .13,
  phaseRad: Math.PI, leftBiasRad: 0, rightBiasRad: 0, neckAmplitudeRad: 0, neckPhaseRad: 0};
export const NEUTRAL_GAIT: Gait = {...DEFAULT_GAIT, leftAmplitudeRad: 0, rightAmplitudeRad: 0};
const clamp = (x: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, x));
const v = (a: Vec3) => ({x: a[0], y: a[1], z: a[2]});
const q = (a: Quat) => ({x: a[0], y: a[1], z: a[2], w: a[3]});
const vec = (a: {x: number; y: number; z: number}): Vec3 => [a.x, a.y, a.z];
const quat = (a: {x: number; y: number; z: number; w: number}): Quat => [a.x, a.y, a.z, a.w];
const dot = (a: Vec3, b: Vec3) => a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const add = (a: Vec3, b: Vec3): Vec3 => [a[0]+b[0],a[1]+b[1],a[2]+b[2]];
const sub = (a: Vec3, b: Vec3): Vec3 => [a[0]-b[0],a[1]-b[1],a[2]-b[2]];
const inverse = (a: Quat): Quat => [-a[0],-a[1],-a[2],a[3]];
function mul(a: Quat,b: Quat): Quat {
  return [a[3]*b[0]+a[0]*b[3]+a[1]*b[2]-a[2]*b[1],a[3]*b[1]-a[0]*b[2]+a[1]*b[3]+a[2]*b[0],
    a[3]*b[2]+a[0]*b[1]-a[1]*b[0]+a[2]*b[3],a[3]*b[3]-a[0]*b[0]-a[1]*b[1]-a[2]*b[2]];
}
function rotate(a: Quat,b: Vec3): Vec3 {const r=mul(mul(a,[...b,0]),inverse(a));return [r[0],r[1],r[2]];}
const wrap = (a: number) => Math.atan2(Math.sin(a),Math.cos(a));
function rng(seed: number): () => number {
  let state=seed>>>0;
  return ()=>{state=(state+0x6D2B79F5)|0;let t=Math.imul(state^(state>>>15),1|state);t^=t+Math.imul(t^(t>>>7),61|t);return ((t^(t>>>14))>>>0)/4294967296;};
}
function finite(x: number,label: string): number {if(!Number.isFinite(x))throw Error(`${label} must be finite`);return x;}

export function gaitTargets(gait: Gait,time: number): JointAngles {
  finite(time,'time');
  for(const [key,value] of Object.entries(gait))finite(value,key);
  const phase=2*Math.PI*clamp(gait.frequencyHz,.2,3.5)*time;
  return {left_hip:clamp(gait.leftBiasRad+gait.leftAmplitudeRad*Math.sin(phase),-HIP,HIP),
    right_hip:clamp(gait.rightBiasRad+gait.rightAmplitudeRad*Math.sin(phase+gait.phaseRad),-HIP,HIP),
    neck_yaw:clamp(gait.neckAmplitudeRad*Math.sin(phase+gait.neckPhaseRad),-Math.PI/4,Math.PI/4),jaw_pitch:0};
}

let ready: Promise<void> | undefined;
export class BrowserPhysics {
  readonly asset: PhysicsAsset;
  readonly options: Required<PhysicsOptions>;
  private world!: RAPIER.World;
  private bodies=new Map<LinkName,RAPIER.RigidBody>();
  private joints=new Map<JointName,RAPIER.RevoluteImpulseJoint>();
  private targets={...ZERO};
  private requested={...ZERO};
  private effort={...ZERO};
  private elapsed=0;
  private accumulator=0;
  private start: Vec3=[0,0,0];
  private previous: Vec3=[0,0,0];
  private reward=0;
  private fallen=false;
  private maxTilt=0;
  private maxViolation=0;
  private seed=1;
  private freed=false;
  private targetCollider?: RAPIER.Collider;

  private constructor(asset: PhysicsAsset,options: PhysicsOptions) {
    this.asset=asset;
    this.options={fixedDt:options.fixedDt??1/300,gravityMps2:options.gravityMps2??9.81,
      friction:options.friction??asset.contactModel.friction,motorsEnabled:options.motorsEnabled??true};
    if(asset.schemaVersion!==1||asset.units!=='m-kg-s-rad'||asset.links.length!==5||asset.joints.length!==4)throw Error('Invalid five-link SI physics asset');
    if(this.options.fixedDt<=0||this.options.fixedDt>1/120||!Number.isFinite(this.options.fixedDt))throw Error('fixedDt must be positive and at most 1/120 second');
    if(this.options.friction<0||!Number.isFinite(this.options.friction))throw Error('Invalid friction');
    finite(this.options.gravityMps2,'gravity');
    for(const l of asset.links)if(!LINKS.includes(l.name)||l.massKg<=0||!l.principalInertiaKgM2.every(x=>Number.isFinite(x)&&x>0)||!l.colliders.length)throw Error('Invalid link mass/inertia/colliders');
  }
  static async create(asset: PhysicsAsset,options: PhysicsOptions={}): Promise<BrowserPhysics> {
    ready??=RAPIER.init();await ready;
    const engine=new BrowserPhysics(asset,options);engine.reset();return engine;
  }
  reset(options: ResetOptions={}): SimulationFrame {
    if(this.freed)throw Error('Engine has been disposed');
    this.world?.free();this.bodies.clear();this.joints.clear();this.targetCollider=undefined;
    this.seed=options.seed??1;const random=rng(this.seed),noise=options.perturbationRad??0;
    const a=(random()-.5)*noise,b=(random()-.5)*noise;
    const orientation=options.baseRotation??mul([Math.sin(a/2),0,0,Math.cos(a/2)],[0,Math.sin(b/2),0,Math.cos(b/2)]);
    if(orientation.some(x=>!Number.isFinite(x))||Math.abs(Math.hypot(...orientation)-1)>.0001)throw Error('baseRotation must be a unit quaternion');
    const drop=options.dropHeightM??.001;
    if(drop<0||!Number.isFinite(drop))throw Error('dropHeightM must be nonnegative');
    this.world=new RAPIER.World({x:0,y:0,z:-this.options.gravityMps2});
    this.world.timestep=this.options.fixedDt;
    this.world.numSolverIterations=8;
    this.world.integrationParameters.normalizedAllowedLinearError=.00005;
    this.world.integrationParameters.normalizedPredictionDistance=.0002;
    const ground=RAPIER.ColliderDesc.cuboid(10,10,.05).setTranslation(0,0,-.05)
      .setFriction(this.options.friction).setRestitution(0).setCollisionGroups(0x00010002);
    this.world.createCollider(ground);
    const baseOrigin=this.asset.cadZeroOriginsM.body;
    const basePosition: Vec3=[0,0,baseOrigin[2]+drop];
    for(const link of this.asset.links){
      const position=add(basePosition,rotate(orientation,sub(this.asset.cadZeroOriginsM[link.name],baseOrigin)));
      const desc=RAPIER.RigidBodyDesc.dynamic().setTranslation(...position).setRotation(q(orientation))
        .setAdditionalMassProperties(link.massKg,v(link.comM),v(link.principalInertiaKgM2),q(link.inertiaFrame))
        .setCanSleep(false).setCcdEnabled(true).setLinearDamping(.01).setAngularDamping(.015);
      const body=this.world.createRigidBody(desc);this.bodies.set(link.name,body);
      for(const c of link.colliders)this.world.createCollider(RAPIER.ColliderDesc.cuboid(...c.halfExtentsM)
        .setTranslation(...c.positionM).setRotation(q(c.quaternion)).setDensity(0)
        .setFriction(this.options.friction).setRestitution(0).setCollisionGroups(0x00020001),body);
      body.recomputeMassPropertiesFromColliders();
    }
    for(const j of this.asset.joints){
      const joint=this.world.createImpulseJoint(RAPIER.JointData.revolute(v(j.parentAnchorM),v(j.childAnchorM),v(j.axis)),
        this.bodies.get(j.parent)!,this.bodies.get(j.child)!,true) as RAPIER.RevoluteImpulseJoint;
      joint.setLimits(...j.limitsRad);joint.setContactsEnabled(false);
      joint.configureMotorModel(RAPIER.MotorModel.ForceBased);
      joint.setMotorMaxForce(this.options.motorsEnabled?j.motor.maxTorqueNm:0);
      joint.configureMotorPosition(0,j.motor.stiffnessNmPerRad,j.motor.dampingNmsPerRad);
      this.joints.set(j.name,joint);
    }
    this.targets={...ZERO};this.requested={...ZERO};this.effort={...ZERO};this.elapsed=0;this.accumulator=0;
    this.start=[...basePosition];this.previous=[...basePosition];this.reward=0;this.fallen=false;this.maxTilt=0;this.maxViolation=0;
    return this.frame();
  }
  private angle(j: PhysicsAsset['joints'][number]): number {
    const parent=quat(this.bodies.get(j.parent)!.rotation()),child=quat(this.bodies.get(j.child)!.rotation());
    const rel=mul(inverse(parent),child);
    return wrap(2*Math.atan2(dot([rel[0],rel[1],rel[2]],j.axis),rel[3]));
  }
  private substep(): void {
    const dt=this.options.fixedDt;
    for(const j of this.asset.joints){
      const parent=this.bodies.get(j.parent)!,child=this.bodies.get(j.child)!,angle=this.angle(j);
      const axis=rotate(quat(parent.rotation()),j.axis);
      const speed=dot(sub(vec(child.angvel()),vec(parent.angvel())),axis);
      const target=this.targets[j.name]+clamp(this.requested[j.name]-this.targets[j.name],-j.motor.commandRateRadS*dt,j.motor.commandRateRadS*dt);
      this.targets[j.name]=target;
      const ceiling=this.options.motorsEnabled?j.motor.maxTorqueNm*Math.max(0,1-Math.abs(speed)/j.motor.noLoadSpeedRadS):0;
      const joint=this.joints.get(j.name)!;
      joint.setMotorMaxForce(ceiling);
      joint.configureMotorPosition(target,j.motor.stiffnessNmPerRad,j.motor.dampingNmsPerRad);
      // This is a bounded PD estimate, not solver impulse telemetry.
      this.effort[j.name]=clamp(j.motor.stiffnessNmPerRad*(target-angle)-j.motor.dampingNmsPerRad*speed,-ceiling,ceiling);
    }
    this.world.step();this.elapsed+=dt;
    const body=this.bodies.get('body')!,position=vec(body.translation()),rotation=quat(body.rotation());
    const up=rotate(rotation,[0,0,1]),forward=rotate(rotation,[1,0,0]);
    const tilt=Math.acos(clamp(up[2],-1,1)),heading=Math.atan2(forward[1],forward[0]);
    const wasFallen=this.fallen;
    this.fallen ||= tilt>Math.PI*.31||position[2]<.019||position.some(x=>!Number.isFinite(x));
    this.maxTilt=Math.max(this.maxTilt,tilt);
    for(const j of this.asset.joints){const angle=this.angle(j);this.maxViolation=Math.max(this.maxViolation,j.limitsRad[0]-angle,angle-j.limitsRad[1]);}
    // The only positive locomotion term is measured world +X displacement.
    // Lateral/heading/tilt costs and a terminal fall penalty oppose tumbling/sliding exploits.
    this.reward+=25*(position[0]-this.previous[0])-8*Math.abs(position[1]-this.previous[1])
      +dt*(.12-1.2*tilt*tilt-.4*heading*heading);
    if(this.fallen&&!wasFallen)this.reward-=4;
    this.previous=position;
  }
  step(dtSeconds=1/60,targets?: Partial<JointAngles>): SimulationFrame {
    if(this.freed)throw Error('Engine has been disposed');
    if(!Number.isFinite(dtSeconds)||dtSeconds<0||dtSeconds>1)throw Error('step duration must be between zero and one second');
    if(targets)for(const [name,value] of Object.entries(targets)){
      const j=this.asset.joints.find(j=>j.name===name);if(!j)throw Error(`Unknown joint ${name}`);
      this.requested[j.name]=clamp(finite(value,name),...j.limitsRad);
    }
    this.accumulator+=dtSeconds;
    while(this.accumulator+1e-12>=this.options.fixedDt){this.substep();this.accumulator-=this.options.fixedDt;}
    return this.frame();
  }
  /** A fixed environment obstacle. Coordinates are deliberately absent from policy observations/frames. Reset removes it. */
  setTarget(position: Vec3,halfSizeM=.025): void {
    if(this.freed)throw Error('Engine has been disposed');
    if(position.length!==3||position.some(x=>!Number.isFinite(x))||!Number.isFinite(halfSizeM)||halfSizeM<=0)throw Error('Invalid target box');
    if(this.targetCollider)this.world.removeCollider(this.targetCollider,true);
    this.targetCollider=this.world.createCollider(RAPIER.ColliderDesc.cuboid(halfSizeM,halfSizeM,halfSizeM)
      .setTranslation(...position).setFriction(this.options.friction).setRestitution(0).setCollisionGroups(0x00010002));
  }
  frame(): SimulationFrame {
    if(this.freed)throw Error('Engine has been disposed');
    const links={} as Record<LinkName,LinkPose>;
    for(const name of LINKS){const body=this.bodies.get(name)!;links[name]={position:vec(body.translation()),quaternion:quat(body.rotation())};}
    const jointAngles={...ZERO};for(const j of this.asset.joints)jointAngles[j.name]=this.angle(j);
    const rotation=links.body.quaternion,up=rotate(rotation,[0,0,1]),forward=rotate(rotation,[1,0,0]);
    return {time:this.elapsed,links,jointAngles,targets:{...this.targets},estimatedMotorTorquesNm:{...this.effort},metrics:{
      distanceM:links.body.position[0]-this.start[0],lateralM:links.body.position[1]-this.start[1],
      headingRad:Math.atan2(forward[1],forward[0]),tiltRad:Math.acos(clamp(up[2],-1,1)),fall:this.fallen,
      reward:this.reward,maxTiltRad:this.maxTilt,maxJointLimitViolationRad:Math.max(0,this.maxViolation)}};
  }
  runEpisode(gait: Gait,options: EpisodeOptions={}): EpisodeResult {
    const seconds=options.seconds??5,settle=options.settleSeconds??.5,seed=options.seed??1,interval=options.frameIntervalSeconds??.15;
    if(!Number.isFinite(seconds)||seconds<=0||seconds>60||!Number.isFinite(settle)||settle<0||settle>5)throw Error('Invalid episode duration');
    if(!Number.isFinite(interval)||interval<=0)throw Error('Invalid frame interval');
    gaitTargets(gait,0);
    this.reset({seed,perturbationRad:.002});
    for(let t=0;t<settle-1e-10;t+=1/60)this.step(Math.min(1/60,settle-t),ZERO);
    this.start=vec(this.bodies.get('body')!.translation());this.previous=[...this.start];this.reward=this.fallen?-4:0;this.maxTilt=0;this.maxViolation=0;
    const startTime=this.elapsed;let lastEmit=-Infinity,frame=this.frame();
    for(let t=0;t<seconds-1e-10&&!this.fallen;t+=1/60){
      frame=this.step(Math.min(1/60,seconds-t),gaitTargets(gait,t));
      if(t-lastEmit>=interval){options.onFrame?.(frame);lastEmit=t;}
    }
    frame=this.frame();options.onFrame?.(frame);
    return {gait:{...gait},seed,durationSeconds:this.elapsed-startTime,score:frame.metrics.reward,distanceM:frame.metrics.distanceM,
      lateralM:frame.metrics.lateralM,fall:frame.metrics.fall,maxTiltRad:frame.metrics.maxTiltRad,
      maxJointLimitViolationRad:frame.metrics.maxJointLimitViolationRad,finalFrame:frame};
  }
  /** Read-only physical diagnostics used by sanity tests. */
  diagnostics(): {massKg: number; bodies: number; joints: number; colliders: number; anchorErrorM: number} {
    let anchorErrorM=0;
    for(const j of this.asset.joints){
      const p=this.bodies.get(j.parent)!,c=this.bodies.get(j.child)!;
      const a=add(vec(p.translation()),rotate(quat(p.rotation()),j.parentAnchorM));
      const b=add(vec(c.translation()),rotate(quat(c.rotation()),j.childAnchorM));
      anchorErrorM=Math.max(anchorErrorM,Math.hypot(...sub(a,b)));
    }
    return {massKg:[...this.bodies.values()].reduce((s,b)=>s+b.mass(),0),bodies:this.bodies.size,joints:this.joints.size,
      colliders:this.world.colliders.len(),anchorErrorM};
  }
  dispose(): void {if(!this.freed){this.world.free();this.bodies.clear();this.joints.clear();this.freed=true;}}
}

export type TrainerOptions = {seed?: number; population?: number; elite?: number; episodeSeconds?: number;
  onFrame?: (frame: SimulationFrame) => void; onEpisode?: (result: EpisodeResult,candidateIndex: number) => void};
export type TrainingProgress = {generation: number; episodesEvaluated: number; baseline: EpisodeResult;
  best: EpisodeResult; bestGait: Gait; generationBest: EpisodeResult; meanScore: number;
  bestDistanceM: number; improvementM: number; scoreImprovement: number; improved: boolean;
  status: 'no-improvement' | 'improved-in-this-model'; candidates: {score: number; distanceM: number; fall: boolean}[]};
const KEYS: (keyof Gait)[]=['frequencyHz','leftAmplitudeRad','rightAmplitudeRad','phaseRad','leftBiasRad','rightBiasRad','neckAmplitudeRad','neckPhaseRad'];
const BOUNDS: [number,number][]=[[.5,3],[0,HIP],[0,HIP],[-Math.PI,Math.PI],[-.07,.07],[-.07,.07],[0,.55],[-Math.PI,Math.PI]];

/** Cross-entropy search over a bounded open-loop sine gait, using actual episodic simulation scores. */
export class CemTrainer {
  private engine: BrowserPhysics;
  private options: Required<Omit<TrainerOptions,'onFrame'|'onEpisode'>> & Pick<TrainerOptions,'onFrame'|'onEpisode'>;
  private random: () => number;
  private mean=KEYS.map(k=>DEFAULT_GAIT[k]);
  private sigma=[.65,.065,.065,1.3,.035,.035,.18,1.4];
  private generation=0;
  private count=0;
  private baseline?: EpisodeResult;
  private best?: EpisodeResult;
  constructor(engine: BrowserPhysics,options: TrainerOptions={}) {
    this.engine=engine;this.options={seed:options.seed??2026,population:options.population??10,elite:options.elite??3,
      episodeSeconds:options.episodeSeconds??5,onFrame:options.onFrame,onEpisode:options.onEpisode};
    const {population,elite}=this.options;
    if(!Number.isInteger(population)||population<3||population>64||!Number.isInteger(elite)||elite<2||elite>=population)throw Error('Use 3..64 candidates and 2..population-1 elites');
    this.random=rng(this.options.seed);
  }
  private normal(): number {return Math.sqrt(-2*Math.log(Math.max(1e-12,this.random())))*Math.cos(2*Math.PI*this.random());}
  private evaluate(gait: Gait,index: number): EpisodeResult {
    const result=this.engine.runEpisode(gait,{seconds:this.options.episodeSeconds,seed:this.options.seed,onFrame:this.options.onFrame});
    this.count++;this.options.onEpisode?.(result,index);return result;
  }
  stepGeneration(): TrainingProgress {
    if(!this.baseline){this.baseline=this.evaluate(NEUTRAL_GAIT,-1);this.best=this.baseline;}
    const results: EpisodeResult[]=[];
    for(let n=0;n<this.options.population;n++){
      const gait=n===0&&this.generation>0?{...this.best!.gait}:Object.fromEntries(KEYS.map((key,i)=>[key,n===0?this.mean[i]:clamp(this.mean[i]+this.sigma[i]*this.normal(),...BOUNDS[i])])) as Gait;
      const result=this.evaluate(gait,n);results.push(result);
      if(result.score>this.best!.score)this.best=result;
    }
    const sorted=[...results].sort((a,b)=>b.score-a.score),elites=sorted.slice(0,this.options.elite);
    for(let i=0;i<KEYS.length;i++){
      const values=elites.map(r=>r.gait[KEYS[i]]),mean=values.reduce((s,x)=>s+x,0)/values.length;
      this.mean[i]=.25*this.mean[i]+.75*mean;
      const deviation=Math.sqrt(values.reduce((s,x)=>s+(x-mean)**2,0)/values.length);
      this.sigma[i]=Math.max((BOUNDS[i][1]-BOUNDS[i][0])*.035,.25*this.sigma[i]+.75*deviation);
    }
    this.generation++;
    const best=this.best!,baseline=this.baseline,improvement=best.distanceM-baseline.distanceM;
    const improved=!best.fall&&improvement>.002&&best.score>baseline.score+.01;
    return {generation:this.generation,episodesEvaluated:this.count,baseline,best,bestGait:{...best.gait},generationBest:sorted[0],
      // "Best" always denotes the same highest-score candidate as bestGait/best.fall,
      // rather than mixing a farther but lower-quality/fallen candidate into its stats.
      meanScore:results.reduce((s,r)=>s+r.score,0)/results.length,bestDistanceM:best.distanceM,
      improvementM:improvement,scoreImprovement:best.score-baseline.score,improved,status:improved?'improved-in-this-model':'no-improvement',
      candidates:results.map(r=>({score:r.score,distanceM:r.distanceM,fall:r.fall}))};
  }
}
