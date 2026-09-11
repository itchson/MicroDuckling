// SPDX-License-Identifier: Apache-2.0
import {BrowserPhysics,CemTrainer,DEFAULT_GAIT,gaitTargets,type JointAngles,type Vec3} from './browser-physics.ts';
import {DEFAULT_VISION_PARAMETERS,visionTargets,cameraScore,proposeVisionParameters,type VisionObservation} from './vision.ts';
import type {RunMode,SimulationCommand,SimulationEvent} from './simulation-protocol';

const send=(event:SimulationEvent)=>postMessage(event);
let engine:BrowserPhysics|undefined,trainer:CemTrainer|undefined,mode:RunMode='paused',runId=0;
let gait={...DEFAULT_GAIT},vision={...DEFAULT_VISION_PARAMETERS},candidate={...vision};
let pose:JointAngles={left_hip:0,right_hip:0,neck_yaw:0,jaw_pitch:0};
let observation:VisionObservation={visible:false,bearingRad:0,areaFraction:0};
let target:Vec3=[.38,0,.025],neck=0,trial=0,bestScore:number|null=null,visible=0,samples=0,bearingSum=0,coverage=0,initialArea=0,finalArea=0,lastObservationTime=-Infinity;
let searchTimer:ReturnType<typeof setTimeout>|undefined;
const frame=()=>{if(engine)send({type:'frame',frame:engine.frame(),runId});};
const setMode=(value:RunMode)=>{mode=value;send({type:'mode',mode});};
function reset(){
  runId++;neck=0;lastObservationTime=-Infinity;observation={visible:false,bearingRad:0,areaFraction:0};
  engine!.reset({seed:2026});engine!.setTarget(target);frame();
}
function policy(){send({type:'policy',gait,vision});}
function learnGeneration(){
  if(mode!=='walk-learning'||!trainer)return;
  try{
    const progress=trainer.stepGeneration();gait={...progress.bestGait};send({type:'training',progress});policy();
    if(progress.generation>=30){setMode('paused');return;}
    searchTimer=setTimeout(learnGeneration,50);
  }catch(error){fail(error);}
}
function startCameraTrial(){
  reset();candidate=trial===0?{...vision}:proposeVisionParameters(vision,trial);
  visible=0;samples=0;bearingSum=0;coverage=0;initialArea=0;finalArea=0;
}
function fail(error:unknown){setMode('paused');send({type:'error',message:error instanceof Error?error.message:String(error)});}

onmessage=async(event:MessageEvent<SimulationCommand>)=>{
  const message=event.data;
  try{
    if(message.type==='init'){
      engine?.dispose();engine=await BrowserPhysics.create(message.asset);engine.setTarget(target);
      send({type:'ready',frame:engine.frame(),runId});policy();return;
    }
    if(!engine)return;
    if(message.type==='observation'){
      if(message.runId!==runId)return;
      const time=engine.frame().time;
      if(!Number.isFinite(message.frameTime)||message.frameTime<0||message.frameTime>time+.02||time-message.frameTime>.3||message.frameTime<=lastObservationTime)return;
      const covered=Number.isFinite(lastObservationTime)?Math.min(.15,message.frameTime-lastObservationTime):0;
      lastObservationTime=message.frameTime;
      observation=message.observation;
      if(mode==='camera-learning'){
        samples++;coverage+=covered;if(observation.visible){visible+=covered;bearingSum+=Math.abs(observation.bearingRad)*covered;}
        if(samples===1)initialArea=observation.areaFraction;
        finalArea=observation.areaFraction;
      }
      return;
    }
    if(message.type==='pose'){pose=message.angles;return;}
    if(message.type==='target'){target=message.position;setMode('paused');reset();return;}
    if(message.type==='reset'){clearTimeout(searchTimer);setMode('paused');reset();return;}
    if(message.type==='run'){
      clearTimeout(searchTimer);setMode(message.mode);
      if(mode==='paused')return;
      if(mode==='walk-learning'){
        runId++;
        trainer=new CemTrainer(engine,{seed:2026,population:8,elite:3,episodeSeconds:4,
          onFrame:f=>send({type:'frame',frame:f,runId})});
        searchTimer=setTimeout(learnGeneration,0);
      }else if(mode==='camera-learning'){
        trial=0;bestScore=null;startCameraTrial();
      }else reset();
    }
  }catch(error){fail(error);}
};

setInterval(()=>{
  if(!engine||mode==='paused'||mode==='walk-learning')return;
  try{
    const time=engine.frame().time;
    let commands=pose;
    if(mode==='gait')commands=gaitTargets(gait,time);
    if(mode==='camera'||mode==='camera-learning'){
      const fresh=time-lastObservationTime<=.3?observation:{visible:false,bearingRad:0,areaFraction:0};
      commands=visionTargets(fresh,mode==='camera-learning'?candidate:vision,gait,time,1/60,neck);
      neck=commands.neck_yaw;
    }
    const current=engine.step(1/60,commands);send({type:'frame',frame:current,runId});
    if(mode==='camera-learning'&&(current.time>=6||current.metrics.fall)){
      const visibleFraction=Math.min(1,visible/current.time),coverageFraction=Math.min(1,coverage/current.time);
      const score=cameraScore({visibleFraction,meanAbsBearingRad:visible?bearingSum/visible:Math.PI,initialArea,
        finalArea:current.time-lastObservationTime<=.3?finalArea:0,fall:current.metrics.fall});
      const eligible=coverageFraction>=.5&&samples>=10&&!current.metrics.fall;
      if(eligible&&(bestScore===null||score>bestScore)){bestScore=score;vision={...candidate};policy();}
      trial++;send({type:'vision-training',progress:{trial,score,bestScore,parameters:{...vision},visibleFraction,coverageFraction,eligible,fall:current.metrics.fall}});
      if(trial>=12)setMode('paused');else startCameraTrial();
    }else if(current.metrics.fall)setMode('paused');
  }catch(error){fail(error);}
},1000/60);
