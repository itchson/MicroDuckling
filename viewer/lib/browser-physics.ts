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
    soleConvexHullM?:number[];
    colliders: {name: string; halfExtentsM: Vec3; positionM: Vec3; quaternion: Quat}[]}[];
  joints: {name: JointName; parent: LinkName; child: LinkName; parentAnchorM: Vec3; childAnchorM: Vec3;
    axis: Vec3; limitsRad: [number, number]; motor: {stiffnessNmPerRad: number; dampingNmsPerRad: number;
      maxTorqueNm: number; noLoadSpeedRadS: number; commandRateRadS: number}}[];
  contactModel: {friction: number};
};
export type Metrics = {distanceM: number; lateralM: number; headingRad: number; tiltRad: number;
  fall: boolean; reward: number; maxTiltRad: number; maxJointLimitViolationRad: number};
export type ContactPointTelemetry = {link:LinkName;positionM:Vec3;normalWorld:Vec3;normalImpulseNs:number;
  tangentImpulseNs:[number,number];normalForceN:number|null;slipSpeedMps:number;friction:number};
export type FootContactTelemetry = {inContact:boolean;normalForceN:number|null;tangentForceMagnitudeN:null;
  slipSpeedMps:number;contactPoints:number};
export type ContactTelemetry = {sampleSeconds:number;sampledAtSeconds:number;totalMassKg:number;weightN:number;
  comWorldM:Vec3;groundNormalForceN:number|null;groundTangentForceMagnitudeN:null;
  environmentReactionWorldN:Vec3;rawGroundNormalImpulseNs:number;obstacleContact:boolean;
  forceMethod:'momentum-balance; foot and point loads use solver-impulse shares';
  feet:{left_leg:FootContactTelemetry;right_leg:FootContactTelemetry};points:ContactPointTelemetry[]};
export type SimulationFrame = {
  time: number; links: Record<LinkName, LinkPose>; jointAngles: JointAngles; targets: JointAngles;
  metrics: Metrics; estimatedMotorTorquesNm: JointAngles; contacts:ContactTelemetry;
};
export type PhysicsOptions = {fixedDt?: number; gravityMps2?: number; friction?: number; motorsEnabled?: boolean;
  footFriction?:number;groundFriction?:number;bodyFriction?:number;massScale?:number;groundEnabled?:boolean;
  solverIterations?:number;allowedLinearErrorM?:number;predictionDistanceM?:number;motorDerating?:'legacy'|'driving-only';
  soleCollider?:'patches'|'convex'};
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
const scale = (a:Vec3,s:number):Vec3 => [a[0]*s,a[1]*s,a[2]*s];
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
function bounded(x:number,lo:number,hi:number,label:string):number {
  finite(x,label);if(x<lo||x>hi)throw Error(`${label} must be in [${lo}, ${hi}]`);return x;
}
const emptyFoot = ():FootContactTelemetry => ({inContact:false,normalForceN:0,tangentForceMagnitudeN:null,slipSpeedMps:0,contactPoints:0});
/** A prior, not a measured servo curve. Driving-only retains braking effort at high speed. */
export function motorEffortCeiling(maxTorque:number,noLoadSpeed:number,speed:number,requestedTorque:number,mode:'legacy'|'driving-only'='legacy'):number {
  if(mode==='driving-only'&&speed*requestedTorque<=0)return maxTorque;
  return maxTorque*Math.max(0,1-Math.abs(speed)/noLoadSpeed);
}

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
  private groundCollider?:RAPIER.Collider;
  private colliderLinks=new Map<number,{link:LinkName;sole:boolean}>();
  private contacts!:ContactTelemetry;
  private environmentImpulse:Vec3=[0,0,0];

  private constructor(asset: PhysicsAsset,options: PhysicsOptions) {
    this.asset=asset;
    const friction=options.friction??asset.contactModel.friction;
    this.options={fixedDt:options.fixedDt??1/600,gravityMps2:options.gravityMps2??9.81,
      friction,motorsEnabled:options.motorsEnabled??true,
      footFriction:options.footFriction??options.friction??.9,groundFriction:options.groundFriction??friction,
      bodyFriction:options.bodyFriction??options.friction??.35,massScale:options.massScale??1,
      groundEnabled:options.groundEnabled??true,solverIterations:options.solverIterations??16,
      allowedLinearErrorM:options.allowedLinearErrorM??.00005,predictionDistanceM:options.predictionDistanceM??.0002,
      motorDerating:options.motorDerating??'legacy',soleCollider:options.soleCollider??'convex'};
    if(asset.schemaVersion!==1||asset.units!=='m-kg-s-rad'||asset.links.length!==5||asset.joints.length!==4)throw Error('Invalid five-link SI physics asset');
    bounded(this.options.fixedDt,1/1200,1/120,'fixedDt');
    for(const name of ['friction','footFriction','groundFriction','bodyFriction'] as const)bounded(this.options[name],0,2,name);
    bounded(this.options.gravityMps2,0,20,'gravity');bounded(this.options.massScale,.5,2,'massScale');
    bounded(this.options.solverIterations,4,32,'solverIterations');if(!Number.isInteger(this.options.solverIterations))throw Error('solverIterations must be integer');
    bounded(this.options.allowedLinearErrorM,.000001,.0005,'allowedLinearErrorM');
    bounded(this.options.predictionDistanceM,0,.002,'predictionDistanceM');
    if(!['legacy','driving-only'].includes(this.options.motorDerating))throw Error('Invalid motorDerating');
    for(const l of asset.links)if(!LINKS.includes(l.name)||l.massKg<=0||!l.principalInertiaKgM2.every(x=>Number.isFinite(x)&&x>0)||!l.colliders.length)throw Error('Invalid link mass/inertia/colliders');
    if(!['patches','convex'].includes(this.options.soleCollider))throw Error('Invalid soleCollider');
    if(this.options.soleCollider==='convex')for(const name of ['left_leg','right_leg']){
      const points=asset.links.find(l=>l.name===name)?.soleConvexHullM;
      if(!points||points.length<12||points.length%3||points.some(x=>!Number.isFinite(x)))throw Error(`Missing valid soleConvexHullM: ${name}`);
    }
  }
  static async create(asset: PhysicsAsset,options: PhysicsOptions={}): Promise<BrowserPhysics> {
    ready??=RAPIER.init();await ready;
    const engine=new BrowserPhysics(asset,options);engine.reset();return engine;
  }
  reset(options: ResetOptions={}): SimulationFrame {
    if(this.freed)throw Error('Engine has been disposed');
    this.world?.free();this.bodies.clear();this.joints.clear();this.colliderLinks.clear();this.targetCollider=undefined;this.groundCollider=undefined;
    this.seed=options.seed??1;const random=rng(this.seed),noise=options.perturbationRad??0;
    const a=(random()-.5)*noise,b=(random()-.5)*noise;
    const orientation=options.baseRotation??mul([Math.sin(a/2),0,0,Math.cos(a/2)],[0,Math.sin(b/2),0,Math.cos(b/2)]);
    if(orientation.some(x=>!Number.isFinite(x))||Math.abs(Math.hypot(...orientation)-1)>.0001)throw Error('baseRotation must be a unit quaternion');
    const drop=options.dropHeightM??.001;
    if(drop<0||!Number.isFinite(drop))throw Error('dropHeightM must be nonnegative');
    this.world=new RAPIER.World({x:0,y:0,z:-this.options.gravityMps2});
    this.world.timestep=this.options.fixedDt;
    this.world.numSolverIterations=this.options.solverIterations;
    this.world.integrationParameters.lengthUnit=1; // SI metres; normalized distances below are metres.
    this.world.integrationParameters.normalizedAllowedLinearError=this.options.allowedLinearErrorM;
    this.world.integrationParameters.normalizedPredictionDistance=this.options.predictionDistanceM;
    const ground=RAPIER.ColliderDesc.cuboid(10,10,.05).setTranslation(0,0,-.05)
      .setFriction(this.options.groundFriction).setFrictionCombineRule(RAPIER.CoefficientCombineRule.Min)
      .setRestitution(0).setCollisionGroups(0x00010002);
    if(this.options.groundEnabled)this.groundCollider=this.world.createCollider(ground);
    const baseOrigin=this.asset.cadZeroOriginsM.body;
    const basePosition: Vec3=[0,0,baseOrigin[2]+drop];
    for(const link of this.asset.links){
      const position=add(basePosition,rotate(orientation,sub(this.asset.cadZeroOriginsM[link.name],baseOrigin)));
      const desc=RAPIER.RigidBodyDesc.dynamic().setTranslation(...position).setRotation(q(orientation))
        .setAdditionalMassProperties(link.massKg*this.options.massScale,v(link.comM),v(scale(link.principalInertiaKgM2,this.options.massScale)),q(link.inertiaFrame))
        .setCanSleep(false).setCcdEnabled(true).setLinearDamping(.01).setAngularDamping(.015);
      const body=this.world.createRigidBody(desc);this.bodies.set(link.name,body);
      for(const c of link.colliders){
        const sole=(link.name==='left_leg'||link.name==='right_leg')&&c.name.startsWith('rocker_');
        if(sole&&this.options.soleCollider==='convex')continue;
        const collider=this.world.createCollider(RAPIER.ColliderDesc.cuboid(...c.halfExtentsM)
          .setTranslation(...c.positionM).setRotation(q(c.quaternion)).setDensity(0)
          .setFriction(sole?this.options.footFriction:this.options.bodyFriction)
          .setFrictionCombineRule(RAPIER.CoefficientCombineRule.Min).setRestitution(0).setCollisionGroups(0x00020001),body);
        this.colliderLinks.set(collider.handle,{link:link.name,sole});
      }
      if(this.options.soleCollider==='convex'&&(link.name==='left_leg'||link.name==='right_leg')){
        const hull=RAPIER.ColliderDesc.convexHull(new Float32Array(link.soleConvexHullM!));
        if(!hull)throw Error(`Cannot construct convex sole: ${link.name}`);
        const collider=this.world.createCollider(hull.setDensity(0).setFriction(this.options.footFriction)
          .setFrictionCombineRule(RAPIER.CoefficientCombineRule.Min).setRestitution(0).setCollisionGroups(0x00020001),body);
        this.colliderLinks.set(collider.handle,{link:link.name,sole:true});
      }
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
    this.contacts=this.emptyContacts();
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
      const pd=j.motor.stiffnessNmPerRad*(target-angle)-j.motor.dampingNmsPerRad*speed;
      const ceiling=this.options.motorsEnabled?motorEffortCeiling(j.motor.maxTorqueNm,j.motor.noLoadSpeedRadS,speed,pd,this.options.motorDerating):0;
      const joint=this.joints.get(j.name)!;
      joint.setMotorMaxForce(ceiling);
      joint.configureMotorPosition(target,j.motor.stiffnessNmPerRad,j.motor.dampingNmsPerRad);
      // This is a bounded PD estimate, not solver impulse telemetry.
      this.effort[j.name]=clamp(pd,-ceiling,ceiling);
    }
    const momentumBefore=this.totalMomentum();
    this.world.step();this.elapsed+=dt;
    const momentumAfter=this.totalMomentum(),mass=[...this.bodies.values()].reduce((sum,b)=>sum+b.mass(),0);
    // Net external contact impulse follows measured momentum change minus gravity and drag.
    // Linear drag is 0.01/s on every link; trapezoidal compensation is an approximation.
    // Internal joint/motor impulses cancel across all five bodies.
    this.environmentImpulse=add(sub(momentumAfter,momentumBefore),
      add([0,0,mass*this.options.gravityMps2*dt],scale(add(momentumBefore,momentumAfter),.005*dt)));
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
    const contactSample=this.emptyContacts();
    while(this.accumulator+1e-12>=this.options.fixedDt){
      this.substep();this.accumulator-=this.options.fixedDt;this.sampleGroundContacts(contactSample);
    }
    if(contactSample.sampleSeconds>0){
      const seconds=contactSample.sampleSeconds;
      contactSample.environmentReactionWorldN=scale(contactSample.environmentReactionWorldN,1/seconds);
      const rawImpulse=contactSample.rawGroundNormalImpulseNs;
      // Rapier 0.20 contactImpulse()/dt overcounts a resting load by (1+1/iterations).
      // Never calibrate it to mg. Total support instead follows momentum balance; shares are estimates.
      contactSample.groundNormalForceN=contactSample.obstacleContact?null:rawImpulse>0?
        Math.max(0,contactSample.environmentReactionWorldN[2]):0;
      for(const foot of Object.values(contactSample.feet)){
        // During accumulation normalForceN holds impulse and slipSpeedMps holds impulse-weighted slip.
        const footImpulse=foot.normalForceN??0;
        foot.slipSpeedMps=footImpulse>0?foot.slipSpeedMps/footImpulse:0;
        foot.normalForceN=contactSample.groundNormalForceN===null?null:rawImpulse>0?
          contactSample.groundNormalForceN*footImpulse/rawImpulse:0;
      }
      contactSample.sampledAtSeconds=this.elapsed;contactSample.comWorldM=this.worldCom();this.contacts=contactSample;
    }
    return this.frame();
  }
  private worldCom():Vec3 {
    let mass=0,weighted:Vec3=[0,0,0];
    for(const body of this.bodies.values()){const m=body.mass();mass+=m;weighted=add(weighted,scale(vec(body.worldCom()),m));}
    return scale(weighted,1/mass);
  }
  private totalMomentum():Vec3 {
    let momentum:Vec3=[0,0,0];
    for(const body of this.bodies.values())momentum=add(momentum,scale(vec(body.linvel()),body.mass()));
    return momentum;
  }
  private emptyContacts():ContactTelemetry {
    const totalMassKg=[...this.bodies.values()].reduce((sum,body)=>sum+body.mass(),0);
    return {sampleSeconds:0,sampledAtSeconds:this.elapsed,totalMassKg,weightN:totalMassKg*this.options.gravityMps2,
      comWorldM:this.worldCom(),groundNormalForceN:0,groundTangentForceMagnitudeN:null,
      environmentReactionWorldN:[0,0,0],rawGroundNormalImpulseNs:0,obstacleContact:false,
      forceMethod:'momentum-balance; foot and point loads use solver-impulse shares',
      feet:{left_leg:emptyFoot(),right_leg:emptyFoot()},points:[]};
  }
  private sampleGroundContacts(sample:ContactTelemetry):void {
    sample.sampleSeconds+=this.options.fixedDt;sample.points=[];
    sample.environmentReactionWorldN=add(sample.environmentReactionWorldN,this.environmentImpulse);
    let obstacleContact=false;
    if(this.targetCollider)this.world.contactPairsWith(this.targetCollider,c=>{
      if(this.colliderLinks.has(c.handle))this.world.contactPair(this.targetCollider!,c,m=>{
        for(let i=0;i<m.numContacts();i++)if(m.contactImpulse(i)>1e-12)obstacleContact=true;
      });
    });
    sample.obstacleContact ||= obstacleContact;
    for(const foot of Object.values(sample.feet)){foot.contactPoints=0;foot.inContact=false;}
    if(!this.groundCollider)return;
    this.world.contactPairsWith(this.groundCollider,collider=>{
      const info=this.colliderLinks.get(collider.handle);if(!info)return;
      const body=this.bodies.get(info.link)!;
      this.world.contactPair(this.groundCollider!,collider,(manifold,flipped)=>{
        // The callback may reverse the pair. Orient the normal from ground into the robot.
        const normal=scale(vec(manifold.normal()),flipped?-1:1);
        for(let i=0;i<manifold.numContacts();i++){
          const impulse=manifold.contactImpulse(i);if(impulse<=1e-12)continue;
          const local=flipped?manifold.localContactPoint1(i):manifold.localContactPoint2(i);if(!local)continue;
          const position=add(vec(collider.translation()),rotate(quat(collider.rotation()),vec(local)));
          const velocity=vec(body.velocityAtPoint(v(position)));
          const slip=Math.hypot(...sub(velocity,scale(normal,dot(velocity,normal))));
          const tangent:[number,number]=[manifold.contactTangentImpulseX(i),manifold.contactTangentImpulseY(i)];
          sample.rawGroundNormalImpulseNs+=impulse;
          sample.points.push({link:info.link,positionM:position,normalWorld:normal,normalImpulseNs:impulse,
            tangentImpulseNs:tangent,normalForceN:null,slipSpeedMps:slip,friction:manifold.friction()});
          if(info.sole&&(info.link==='left_leg'||info.link==='right_leg')){
            const foot=sample.feet[info.link];foot.inContact=true;foot.contactPoints++;
            foot.normalForceN=(foot.normalForceN??0)+impulse;foot.slipSpeedMps+=impulse*slip;
          }
        }
      });
    });
    const impulseSum=sample.points.reduce((sum,p)=>sum+p.normalImpulseNs,0);
    for(const point of sample.points)point.normalForceN=obstacleContact?null:impulseSum>0?
      Math.max(0,this.environmentImpulse[2])/this.options.fixedDt*point.normalImpulseNs/impulseSum:0;
  }
  /** A fixed environment obstacle. Coordinates are deliberately absent from policy observations/frames. Reset removes it. */
  setTarget(position: Vec3,halfSizeM:number|Vec3=.025): void {
    if(this.freed)throw Error('Engine has been disposed');
    const extents:Vec3=typeof halfSizeM==='number'?[halfSizeM,halfSizeM,halfSizeM]:halfSizeM;
    if(position.length!==3||position.some(x=>!Number.isFinite(x))||extents.length!==3||extents.some(x=>!Number.isFinite(x)||x<=0))throw Error('Invalid target box');
    if(this.targetCollider)this.world.removeCollider(this.targetCollider,true);
    this.targetCollider=this.world.createCollider(RAPIER.ColliderDesc.cuboid(...extents)
      .setTranslation(...position).setFriction(this.options.groundFriction).setFrictionCombineRule(RAPIER.CoefficientCombineRule.Min)
      .setRestitution(0).setCollisionGroups(0x00010002));
  }
  frame(): SimulationFrame {
    if(this.freed)throw Error('Engine has been disposed');
    const links={} as Record<LinkName,LinkPose>;
    for(const name of LINKS){const body=this.bodies.get(name)!;links[name]={position:vec(body.translation()),quaternion:quat(body.rotation())};}
    const jointAngles={...ZERO};for(const j of this.asset.joints)jointAngles[j.name]=this.angle(j);
    const rotation=links.body.quaternion,up=rotate(rotation,[0,0,1]),forward=rotate(rotation,[1,0,0]);
    return {time:this.elapsed,links,jointAngles,targets:{...this.targets},estimatedMotorTorquesNm:{...this.effort},contacts:this.contacts,metrics:{
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
