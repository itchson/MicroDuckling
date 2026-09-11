import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BrowserPhysics,CemTrainer,DEFAULT_GAIT,NEUTRAL_GAIT,gaitTargets} from '../lib/browser-physics.ts';
const asset=JSON.parse(readFileSync(new URL('../../simulation/browser/robot-physics.json',import.meta.url)));
const nearly=(a,b,tolerance)=>assert.ok(Math.abs(a-b)<tolerance,`${a} != ${b}`);

test('physical asset retains full CAD-estimated mass, nonzero inertia and five moving links',async()=>{
  const sim=await BrowserPhysics.create(asset);
  try{const d=sim.diagnostics();nearly(d.massKg,.257281065184,1e-6);assert.equal(d.bodies,5);assert.equal(d.joints,4);assert.ok(d.colliders>20);assert.ok(d.anchorErrorM<1e-6);
    for(const l of asset.links){assert.ok(l.massKg>0);assert.ok(l.principalInertiaKgM2.every(x=>x>0));}
  }finally{sim.dispose();}
});
test('unsupported robot falls under gravity and settles against the ground',async()=>{
  const sim=await BrowserPhysics.create(asset);
  try{const start=sim.reset({dropHeightM:.05});let f;
    for(let i=0;i<6;i++)f=sim.step(1/60);
    assert.ok(start.links.body.position[2]-f.links.body.position[2]>.025,'Gravity must cause real falling');
    for(let i=0;i<120;i++)f=sim.step(1/60);
    assert.ok(f.links.body.position[2]>.018&&f.links.body.position[2]<.06,'Ground contact must prevent falling through');
    assert.ok(sim.diagnostics().anchorErrorM<.002,'Articulation must remain coupled');
  }finally{sim.dispose();}
});
test('zero gravity and neutral commands do not manufacture forward translation',async()=>{
  const sim=await BrowserPhysics.create(asset,{gravityMps2:0});
  try{sim.reset({dropHeightM:.1});let frame;for(let i=0;i<120;i++)frame=sim.step(1/60);
    assert.ok(Math.abs(frame.metrics.distanceM)<1e-6);assert.ok(Math.abs(frame.metrics.lateralM)<1e-6);
  }finally{sim.dispose();}
});
test('joint motor moves the head relative to body; contacts and bounded coupling remain finite',async()=>{
  const sim=await BrowserPhysics.create(asset);
  try{let f;for(let i=0;i<90;i++)f=sim.step(1/60,{neck_yaw:.5,left_hip:.1,right_hip:.1,jaw_pitch:.12});
    assert.ok(f.jointAngles.neck_yaw>.25,'Physical neck joint should respond');
    assert.ok(f.jointAngles.jaw_pitch>.07,'Physical jaw should respond');
    assert.ok(sim.diagnostics().anchorErrorM<.002);
    for(const [name,value] of Object.entries(f.estimatedMotorTorquesNm))assert.ok(Math.abs(value)<=.090001,name);
    assert.ok(f.metrics.maxJointLimitViolationRad<.05);
  }finally{sim.dispose();}
});
test('same seed and timestep reproduce episode results; different commands produce different dynamics',async()=>{
  const sim=await BrowserPhysics.create(asset);
  try{const a=sim.runEpisode(DEFAULT_GAIT,{seconds:2,seed:17}),b=sim.runEpisode(DEFAULT_GAIT,{seconds:2,seed:17}),n=sim.runEpisode(NEUTRAL_GAIT,{seconds:2,seed:17});
    nearly(a.distanceM,b.distanceM,1e-9);nearly(a.score,b.score,1e-9);
    assert.ok(Math.abs(a.finalFrame.jointAngles.left_hip-n.finalFrame.jointAngles.left_hip)>.02);
    assert.ok(Math.abs(a.distanceM-n.distanceM)>1e-5,'Gait must affect physical displacement');
  }finally{sim.dispose();}
});
test('CEM evaluates real candidates, streams actual frames and reports honest improvement',async()=>{
  const sim=await BrowserPhysics.create(asset);let frames=0,episodes=0;
  try{const trainer=new CemTrainer(sim,{seed:33,population:4,elite:2,episodeSeconds:1,
      onFrame:f=>{frames++;assert.equal(Object.keys(f.links).length,5);assert.ok(Number.isFinite(f.metrics.distanceM));},onEpisode:()=>episodes++});
    const p=trainer.stepGeneration();assert.equal(p.generation,1);assert.equal(p.episodesEvaluated,5);assert.equal(episodes,5);assert.ok(frames>=10);
    assert.equal(p.candidates.length,4);assert.ok(new Set(p.candidates.map(c=>c.score.toFixed(5))).size>1,'Candidates must not use synthetic identical scores');
    nearly(p.improvementM,p.best.distanceM-p.baseline.distanceM,1e-12);
    nearly(p.bestDistanceM,p.best.distanceM,1e-12);
    assert.equal(p.improved,!p.best.fall&&p.improvementM>.002&&p.scoreImprovement>.01);
    for(let t=0;t<4;t+=.1){const x=gaitTargets(p.bestGait,t);assert.ok(Math.abs(x.left_hip)<=Math.PI/15);assert.ok(Math.abs(x.right_hip)<=Math.PI/15);}
  }finally{sim.dispose();}
});
test('a tipped robot reports a physical fall, and target is an environment collider only',async()=>{
  const sim=await BrowserPhysics.create(asset);
  try{const n=sim.diagnostics().colliders;sim.setTarget([.3,0,.025]);assert.equal(sim.diagnostics().colliders,n+1);
    sim.setTarget([.35,.02,.025]);assert.equal(sim.diagnostics().colliders,n+1);assert.equal('target' in sim.frame(),false);
    sim.reset({dropHeightM:.12,baseRotation:[Math.sin(.65),0,0,Math.cos(.65)]});assert.equal(sim.diagnostics().colliders,n);
    const f=sim.step(1/60);assert.equal(f.metrics.fall,true);assert.ok(f.metrics.reward< -3);
  }finally{sim.dispose();}
});
