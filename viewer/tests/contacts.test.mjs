import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import R from '@dimforge/rapier3d-compat';
import {BrowserPhysics,DEFAULT_GAIT,gaitTargets,motorEffortCeiling} from '../lib/browser-physics.ts';
const asset=JSON.parse(fs.readFileSync(new URL('../../simulation/browser/robot-physics.json',import.meta.url)));
const near=(a,b,e,message)=>assert.ok(Math.abs(a-b)<=e,`${message}: ${a} vs ${b} ±${e}`);
function settle(engine,n=120){for(let i=0;i<n;i++)engine.step(1/60);}

test('weight, COM and inertia scale physically; resting support follows momentum',async()=>{
 for(const massScale of [.5,1,1.5]){
  const e=await BrowserPhysics.create(asset,{massScale});
  try {
   near(e.diagnostics().massKg,asset.totalMassKg*massScale,1e-7,'mass');
   for(const link of asset.links){const inertia=e.bodies.get(link.name).principalInertia();
    [inertia.x,inertia.y,inertia.z].forEach((x,i)=>near(x,link.principalInertiaKgM2[i]*massScale,1e-9,'inertia'));
   }
   settle(e);let normal=0;
   for(let i=0;i<120;i++){const c=e.step(1/60).contacts;normal+=c.groundNormalForceN;
    assert.equal(c.groundTangentForceMagnitudeN,null);
    assert.equal(c.obstacleContact,false);
    near(c.feet.left_leg.normalForceN+c.feet.right_leg.normalForceN,c.groundNormalForceN,1e-7,'foot support sum');
    for(const p of c.points){assert.ok(Math.abs(p.positionM[2])<.001,'contact marker lies at ground');assert.ok(p.normalWorld[2]>.99);}
   }
   near(normal/120,e.frame().contacts.weightN,.01,'resting support');
   assert.equal(e.frame().metrics.fall,false);
  }finally{e.dispose();}
 }
});

test('Rapier 0.20 raw impulse and force-event overcount is recorded, never used as force',async()=>{
 await R.init();const w=new R.World({x:0,y:0,z:-9.81});w.timestep=1/300;w.numSolverIterations=8;
 const queue=new R.EventQueue(true);
 try {
  const g=w.createCollider(R.ColliderDesc.cuboid(1,1,.05).setTranslation(0,0,-.05).setActiveEvents(R.ActiveEvents.CONTACT_FORCE_EVENTS));
  const b=w.createRigidBody(R.RigidBodyDesc.dynamic().setTranslation(0,0,.05).setCanSleep(false));
  w.createCollider(R.ColliderDesc.cuboid(.05,.05,.05).setMass(1),b);
  let raw=0,event=0;
  for(let s=0;s<750;s++){w.step(queue);queue.drainContactForceEvents(e=>{if(s>=600)event+=e.totalForceMagnitude();});
   if(s>=600)w.contactPairsWith(g,c=>w.contactPair(g,c,m=>{for(let i=0;i<m.numContacts();i++)raw+=m.contactImpulse(i)/w.timestep;}));
  }
  near(b.linvel().z,0,1e-5,'resting velocity');
  near(raw/150,9.81*1.125,.002,'observed raw overcount');near(event/150,raw/150,.002,'event repeats overcount');
 }finally{queue.free();w.free();}
});

test('gravity and ground switches affect actual COM motion',async()=>{
 const free=await BrowserPhysics.create(asset,{gravityMps2:0,groundEnabled:false});
 const falling=await BrowserPhysics.create(asset,{groundEnabled:false});
 try {
  const origin=free.frame().contacts.comWorldM;
  for(let i=0;i<30;i++){free.step(1/60,gaitTargets(DEFAULT_GAIT,i/60));falling.step(1/60);}
  const c=free.frame().contacts;
  near(c.totalMassKg,asset.totalMassKg,1e-7,'free mass');
  c.comWorldM.forEach((x,i)=>near(x,origin[i],2e-6,'internal motors cannot translate COM'));
  assert.equal(c.weightN,0);assert.equal(c.groundNormalForceN,0);assert.equal(c.points.length,0);
  assert.ok(falling.frame().contacts.comWorldM[2]<origin[2]-.9);
  assert.equal(falling.frame().contacts.groundNormalForceN,0);
 }finally{free.dispose();falling.dispose();}
});

test('Coulomb sliding deceleration follows mu times gravity despite unavailable tangent readout',async()=>{
 await R.init();
 for(const friction of [0,.4,.7,.9]){
  const w=new R.World({x:0,y:0,z:-9.81});w.timestep=1/600;w.numSolverIterations=16;
  try {
   w.createCollider(R.ColliderDesc.cuboid(2,2,.05).setTranslation(0,0,-.05).setFriction(friction).setFrictionCombineRule(R.CoefficientCombineRule.Min));
   const b=w.createRigidBody(R.RigidBodyDesc.dynamic().setTranslation(0,0,.05).setCanSleep(false).lockRotations());
   w.createCollider(R.ColliderDesc.cuboid(.05,.05,.05).setMass(1).setFriction(.9).setFrictionCombineRule(R.CoefficientCombineRule.Min),b);
   for(let i=0;i<600;i++)w.step();b.setLinvel({x:.2,y:0,z:0},true);
   for(let i=0;i<6;i++)w.step();
   near((.2-b.linvel().x)/.01,friction*9.81,.001,'frictional deceleration');
  }finally{w.free();}
 }
});

test('independent material coefficients are applied and friction reduces measured slip',async()=>{
 const values=[];
 for(const groundFriction of [0,.7,1.2]){
  const e=await BrowserPhysics.create(asset,{groundFriction});
  try {
   settle(e);let slip=0;
   for(let i=0;i<120;i++){const c=e.step(1/60,gaitTargets(DEFAULT_GAIT,i/60)).contacts;
    slip+=(c.feet.left_leg.slipSpeedMps+c.feet.right_leg.slipSpeedMps)/2;
    for(const p of c.points)if(p.link.endsWith('_leg'))near(p.friction,Math.min(.9,groundFriction),1e-6,'Min material combine');
   }
   values.push(slip/120);
  }finally{e.dispose();}
 }
 assert.ok(values[0]>2*values[1],`zero-friction slip ${values} must exceed default`);
 assert.ok(values[2]<values[0]);
});

test('rectangular target works and obstacle contacts invalidate isolated ground force',async()=>{
 const e=await BrowserPhysics.create(asset);
 try {
  e.setTarget([.24,0,.05],[.025,.025,.05]);
  const h=e.targetCollider.halfExtents();near(h.x,.025,1e-8,'width');near(h.z,.05,1e-8,'height');
  e.setTarget([0,0,.045],[.03,.03,.03]);
  let seen=false;for(let i=0;i<30;i++){const c=e.step(1/300).contacts;if(c.obstacleContact){seen=true;assert.equal(c.groundNormalForceN,null);assert.equal(c.feet.left_leg.normalForceN,null);}}
  assert.ok(seen,'overlapping obstacle must be detected');
  e.reset();assert.equal(e.targetCollider,undefined);
 }finally{e.dispose();}
});

test('motor envelope preserves legacy and optional braking effort explicitly',()=>{
 near(motorEffortCeiling(.09,10,5,1),.045,1e-12,'legacy motoring');
 near(motorEffortCeiling(.09,10,5,-1),.045,1e-12,'legacy braking also derates');
 near(motorEffortCeiling(.09,10,5,-1,'driving-only'),.09,1e-12,'optional braking');
 assert.equal(motorEffortCeiling(.09,10,12,1),0);
});

test('reject unsupported physical settings and missing hull inputs',async()=>{
 for(const options of [{massScale:0},{groundFriction:-1},{fixedDt:1/30},{gravityMps2:Infinity},{solverIterations:2.5}])
  await assert.rejects(BrowserPhysics.create(asset,options));
 const missingHulls=structuredClone(asset);for(const link of missingHulls.links)delete link.soleConvexHullM;
 await assert.rejects(BrowserPhysics.create(missingHulls,{soleCollider:'convex'}));
});

test('continuous sole mode removes the tiled contact seams without adding mass',async()=>{
 const hull=await BrowserPhysics.create(asset),patches=await BrowserPhysics.create(asset,{soleCollider:'patches'});
 try {
  const expectedRobotHulls=asset.links.reduce((n,l)=>n+l.colliders.filter(c=>!c.name.startsWith('rocker_')).length+(l.soleConvexHullM?1:0),0);
  assert.equal(hull.diagnostics().colliders,expectedRobotHulls+1);
  assert.ok(patches.diagnostics().colliders>hull.diagnostics().colliders+50);
  near(hull.diagnostics().massKg,patches.diagnostics().massKg,1e-8,'shape choice does not alter mass');
  settle(hull);assert.equal(hull.frame().metrics.fall,false);
 }finally{hull.dispose();patches.dispose();}
});
