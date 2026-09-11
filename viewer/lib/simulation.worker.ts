// SPDX-License-Identifier: Apache-2.0
import {BrowserPhysics,type JointAngles,type Vec3,type PhysicsAsset} from './browser-physics.ts';
import {DEFAULT_VISION_PARAMETERS,proposeVisionParameters} from './vision.ts';
import {CAMERA_WADDLE_GAIT,locomotionTargets,type LocomotionGait} from './locomotion-controller.ts';
import {RockingTrainer} from './rocking-trainer.ts';
import {ApproachEpisode,type ApproachResult} from './approach.ts';
import type {RunMode,SimulationCommand,SimulationEvent,EnvironmentSettings} from './simulation-protocol';
import {manualGait,validateTarget,validateExperiment,DEFAULT_EXPERIMENT} from './experiment-settings.ts';

const send=(event:SimulationEvent)=>postMessage(event);
let engine:BrowserPhysics|undefined,trainer:RockingTrainer|undefined,approach:ApproachEpisode|undefined,mode:RunMode='paused',runId=0,configuration=0;
let physicsAsset:PhysicsAsset|undefined,environment:EnvironmentSettings={groundFriction:.7,massScale:1};
let gait:LocomotionGait=structuredClone(CAMERA_WADDLE_GAIT),vision={...DEFAULT_VISION_PARAMETERS},candidate={...vision};
let pose:JointAngles={left_hip:0,right_hip:0,neck_yaw:0,jaw_pitch:0};
let target:Vec3=[.18,0,.05],trial=0,bestScore:number|null=null;
let searchTimer:ReturnType<typeof setTimeout>|undefined;
let experiment={...DEFAULT_EXPERIMENT};
const frame=(result?:ApproachResult)=>{if(engine)send({type:'frame',frame:result?.frame??engine.frame(),runId,goal:result?.goal});};
const setMode=(value:RunMode)=>{mode=value;send({type:'mode',mode});};
function reset(){runId++;approach=undefined;engine!.reset({seed:2026});engine!.setTarget(target,[.025,.025,.05]);frame();}
function policy(){send({type:'policy',gait,vision});}
function learnGeneration(){
  if(mode!=='walk-learning'||!trainer)return;
  try{
    const progress=trainer.stepGeneration();gait=structuredClone(progress.bestGait);send({type:'training',progress});policy();
    if(progress.generation>=12){setMode('paused');return;}
    searchTimer=setTimeout(learnGeneration,20);
  }catch(error){fail(error);}
}
function startCameraTrial(){
  runId++;candidate=mode==='camera-learning'?proposeVisionParameters(vision,trial):{...vision};
  approach=new ApproachEpisode(engine!,physicsAsset!,gait,candidate,target,{seed:2026,seconds:experiment.cameraSeconds,search:experiment});frame(approach.current());
}
function finishCameraTrial(result:ApproachResult){
  if(mode==='camera-learning'){
    if(result.eligible&&(bestScore===null||result.score>bestScore)){bestScore=result.score;vision={...candidate};policy();}
    trial++;send({type:'vision-training',progress:{trial,score:result.score,bestScore,parameters:{...vision},visibleFraction:result.visibleFraction,
      coverageFraction:result.coverageFraction,eligible:result.eligible,fall:result.goal.fallen,goal:result.goal}});
    if(trial>=12)setMode('paused');else startCameraTrial();
  }else setMode('paused');
}
function fail(error:unknown){clearTimeout(searchTimer);setMode('paused');send({type:'error',message:error instanceof Error?error.message:String(error)});}
async function configurePhysics(){
  if(!physicsAsset)return;
  const ticket=++configuration;clearTimeout(searchTimer);setMode('paused');engine?.dispose();engine=undefined;approach=undefined;
  const created=await BrowserPhysics.create(physicsAsset,{...environment,footFriction:environment.footFriction??.9,bodyFriction:.35});
  if(ticket!==configuration){created.dispose();return;}engine=created;
  trainer=undefined;vision={...DEFAULT_VISION_PARAMETERS};reset();
  send({type:'ready',frame:engine.frame(),runId});policy();
}

onmessage=async(event:MessageEvent<SimulationCommand>)=>{
  const message=event.data;
  try{
    if(message.type==='init'){physicsAsset=message.asset;await configurePhysics();return;}
    if(message.type==='environment'){environment=message.settings;await configurePhysics();return;}
    if(!engine)return;
    if(message.type==='observation'){
      if((mode!=='camera'&&mode!=='camera-learning')||!approach||message.runId!==runId)return;
      if(!Number.isFinite(message.frameTime)||Math.abs(message.frameTime-engine.frame().time)>1e-6)return;
      const result=approach.observe(message.observation,message.frameTime);frame(result);
      if(result.finished)finishCameraTrial(result);
      return;
    }
    if(message.type==='pose'){pose=message.angles;return;}
    if(message.type==='gait'||message.type==='reference'){
      const next=message.type==='gait'?manualGait(message.settings):structuredClone(CAMERA_WADDLE_GAIT);
      clearTimeout(searchTimer);gait=next;trainer=undefined;vision={...DEFAULT_VISION_PARAMETERS};setMode('paused');reset();policy();return;
    }
    if(message.type==='experiment'){experiment=validateExperiment(message.settings);clearTimeout(searchTimer);setMode('paused');reset();return;}
    if(message.type==='target'){const next=validateTarget(message.position);clearTimeout(searchTimer);target=next;setMode('paused');reset();return;}
    if(message.type==='reset'){clearTimeout(searchTimer);setMode('paused');reset();return;}
    if(message.type==='run'){
      clearTimeout(searchTimer);setMode(message.mode);
      if(mode==='paused')return;
      if(mode==='walk-learning'){
        runId++;approach=undefined;let lastFrame=0;
        trainer=new RockingTrainer(engine,{seed:2026,population:12,elite:3,episodeSeconds:14,seedGait:gait,
          onFrame:f=>{if(performance.now()-lastFrame>80){send({type:'frame',frame:f,runId});lastFrame=performance.now();}}});
        searchTimer=setTimeout(learnGeneration,0);
      }else if(mode==='camera-learning'||mode==='camera'){trial=0;bestScore=null;startCameraTrial();}
      else {
        reset();
        if(mode==='gait')for(let i=0;i<60;i++)engine.step(1/60,{left_hip:0,right_hip:0,neck_yaw:0,jaw_pitch:0});
      }
    }
  }catch(error){fail(error);}
};

// Camera episodes advance only on a matching image. Hidden tabs and missing
// camera frames cannot accrue simulation time, coverage, dwell or training reward.
setInterval(()=>{
  if(!engine||(mode!=='pose'&&mode!=='gait'))return;
  try{
    const current=engine.step(1/60,mode==='gait'?locomotionTargets(gait,Math.max(0,engine.frame().time-1)):pose);
    send({type:'frame',frame:current,runId});if(current.metrics.fall)setMode('paused');
  }catch(error){fail(error);}
},1000/60);
