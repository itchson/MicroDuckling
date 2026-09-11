// SPDX-License-Identifier: Apache-2.0
import {useEffect,useRef,useState} from 'react';
import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {Button} from './ui/button';
import {Slider} from './ui/slider';
import {Play,Pause,RotateCcw,Download,ScanEye,FlaskConical} from 'lucide-react';
import {createCadMesh,disposeCadMesh,type Assembly,type CadMeshData} from '../lib/robot';
import type {LinkName,PhysicsAsset,SimulationFrame,Vec3} from '../lib/browser-physics';
import type {LocomotionGait} from '../lib/locomotion-controller';
import type {RockingProgress} from '../lib/rocking-trainer';
import type {GoalDisplay} from '../lib/approach';
import {detectTarget,type VisionParameters} from '../lib/vision';
import type {RunMode,SimulationCommand,SimulationEvent,VisionProgress,EnvironmentSettings} from '../lib/simulation-protocol';

const CAMERA_WIDTH=96,CAMERA_HEIGHT=72,CAMERA_FOV=50;
const descriptions:Record<RunMode,string>={paused:'Paused',pose:'Servo pose',gait:'Gait playback','walk-learning':'Searching gaits',camera:'Camera approach','camera-learning':'Learning camera control'};
type Policy={gait:LocomotionGait;vision:VisionParameters};

export function SimulationWorkspace({data,visible}:{data:Assembly;visible:boolean}){
  const host=useRef<HTMLDivElement>(null),preview=useRef<HTMLCanvasElement>(null),worker=useRef<Worker|null>(null);
  const latest=useRef<{frame:SimulationFrame;runId:number}|null>(null),asset=useRef<PhysicsAsset|null>(null);
  const targetPosition=useRef<Vec3>([180,0,50]),active=useRef<RunMode>('paused');
  const [physicsReady,setPhysicsReady]=useState(false),[graphicsReady,setGraphicsReady]=useState(false),[error,setError]=useState(''),[mode,setMode]=useState<RunMode>('paused');
  const ready=physicsReady&&graphicsReady;
  const [stats,setStats]=useState<SimulationFrame|null>(null),[progress,setProgress]=useState<RockingProgress|null>(null),[goal,setGoal]=useState<GoalDisplay|null>(null);
  const [history,setHistory]=useState<number[]>([]),[visionProgress,setVisionProgress]=useState<VisionProgress|null>(null);
  const [policy,setPolicy]=useState<Policy|null>(null),[seen,setSeen]=useState(false),[targetSide,setTargetSide]=useState(0);
  const [bow,setBow]=useState(0),[neck,setNeck]=useState(0),[jaw,setJaw]=useState(0);
  const [environment,setEnvironment]=useState<EnvironmentSettings>({groundFriction:.7,massScale:1});
  const contactsVisible=useRef(true),[showContacts,setShowContacts]=useState(true);
  const send=(command:SimulationCommand)=>worker.current?.postMessage(command);
  useEffect(()=>{if(!visible)worker.current?.postMessage({type:'run',mode:'paused'} satisfies SimulationCommand);},[visible]);
  const run=(next:RunMode)=>{
    if(next==='walk-learning'){setHistory([]);setProgress(null);}
    if(next==='camera-learning')setVisionProgress(null);
    send({type:'run',mode:next});
  };

  useEffect(()=>{
    const controller=new AbortController(),w=new Worker(new URL('../lib/simulation.worker.ts',import.meta.url),{type:'module'});
    worker.current=w;let alive=true,lastStats=0;
    w.onmessage=(event:MessageEvent<SimulationEvent>)=>{
      if(!alive)return;const message=event.data;
      if(message.type==='ready'||message.type==='frame'){
        latest.current={frame:message.frame,runId:message.runId};
        setGoal(message.goal??null);
        if(message.type==='ready')setPhysicsReady(true);
        if(performance.now()-lastStats>120||message.type==='ready'){
          setStats(message.frame);lastStats=performance.now();
        }
      }else if(message.type==='mode'){active.current=message.mode;setMode(message.mode);}
      else if(message.type==='training'){setProgress(message.progress);setHistory(values=>[...values,message.progress.best.score]);}
      else if(message.type==='vision-training')setVisionProgress(message.progress);
      else if(message.type==='policy')setPolicy({gait:message.gait,vision:message.vision});
      else if(message.type==='error')setError(message.message);
    };
    w.onerror=event=>setError(event.message||'The physics worker could not start.');
    void(async()=>{try{
      const response=await fetch('/simulation/robot-physics.json',{signal:controller.signal});
      if(!response.ok)throw Error('Physics asset is unavailable.');
      const physics:PhysicsAsset=await response.json();asset.current=physics;w.postMessage({type:'init',asset:physics} satisfies SimulationCommand);
    }catch(e){if(alive)setError(e instanceof Error?e.message:String(e));}})();
    return()=>{alive=false;controller.abort();w.terminate();worker.current=null;latest.current=null;};
  },[]);

  useEffect(()=>{
    const radians=Math.PI/180;
    send({type:'pose',angles:{left_hip:-bow*radians,right_hip:-bow*radians,neck_yaw:neck*radians,jaw_pitch:jaw*radians}});
  },[bow,neck,jaw]);

  useEffect(()=>{
    const mount=host.current!;let disposed=false,animation=0,lastVision=0,lastCapture='';
    const controller=new AbortController();let renderer:T.WebGLRenderer;
    try{renderer=new T.WebGLRenderer({antialias:true});}catch{setError('WebGL is required to display this experiment.');return;}
    renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=T.SRGBColorSpace;
    renderer.domElement.setAttribute('aria-label','Physical MicroDuckling simulation. Drag to orbit and scroll to zoom.');
    mount.appendChild(renderer.domElement);
    const scene=new T.Scene();scene.background=new T.Color('#101923');
    const camera=new T.PerspectiveCamera(43,1,1,8000);camera.up.set(0,0,1);camera.position.set(590,-720,410);
    const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(120,0,60);controls.enableDamping=true;controls.minDistance=130;controls.maxDistance=2500;
    scene.add(new T.HemisphereLight(0xe6f1ff,0x354353,2.4));
    const sun=new T.DirectionalLight(0xffffff,3);sun.position.set(80,-140,240);scene.add(sun);
    const floor=new T.Mesh(new T.PlaneGeometry(6000,6000),new T.MeshStandardMaterial({color:0x192837,roughness:1}));floor.position.z=-.3;scene.add(floor);
    const grid=new T.GridHelper(3000,60,0x405465,0x273a4b);grid.rotation.x=Math.PI/2;scene.add(grid);
    const target=new T.Mesh(new T.BoxGeometry(50,50,100),new T.MeshBasicMaterial({color:0xec19df}));scene.add(target);
    const comMarker=new T.Mesh(new T.SphereGeometry(2.3,12,8),new T.MeshBasicMaterial({color:0x7be1e3,depthTest:false}));comMarker.renderOrder=10;comMarker.visible=false;scene.add(comMarker);
    const contactGeometry=new T.SphereGeometry(1.5,8,6),contactMaterial=new T.MeshBasicMaterial({color:0xffc476,depthTest:false});
    const contactMarkers=new T.InstancedMesh(contactGeometry,contactMaterial,128);contactMarkers.count=0;contactMarkers.renderOrder=11;contactMarkers.frustumCulled=false;scene.add(contactMarkers);
    const meshes=new Map<LinkName,T.Mesh[]>();
    const sensor=new T.PerspectiveCamera(CAMERA_FOV,CAMERA_WIDTH/CAMERA_HEIGHT,.1,5000);sensor.up.set(0,0,1);
    const renderTarget=new T.WebGLRenderTarget(CAMERA_WIDTH,CAMERA_HEIGHT,{depthBuffer:true});
    const pixels=new Uint8Array(CAMERA_WIDTH*CAMERA_HEIGHT*4),flipped=new Uint8ClampedArray(pixels.length);
    const scale=new T.Vector3(1,1,1),matrix=new T.Matrix4(),origin=new T.Matrix4(),rotation=new T.Quaternion(),position=new T.Vector3();
    const headMatrix=new T.Matrix4(),sensorPosition=new T.Vector3(),sensorForward=new T.Vector3(),sensorUp=new T.Vector3();
    const resize=()=>{const width=mount.clientWidth,height=mount.clientHeight;if(!width||!height)return;renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();};
    const observer=new ResizeObserver(resize);observer.observe(mount);resize();
    void Promise.all(data.parts.filter(p=>p.kind!=='coupon').map(async part=>{
      const response=await fetch(`/cad/meshes/${part.name}.json?v=${data.cad_sha256}`,{signal:controller.signal});
      if(!response.ok)throw Error(`Missing geometry: ${part.label}`);
      const geometry:CadMeshData=await response.json();if(disposed)return;
      const mesh=createCadMesh(geometry,part);mesh.matrixAutoUpdate=false;scene.add(mesh);
      const link=part.link as LinkName;meshes.set(link,[...(meshes.get(link)??[]),mesh]);
    })).then(()=>{if(!disposed)setGraphicsReady(true);}).catch(e=>{if(!disposed)setError(e instanceof Error?e.message:String(e));});
    const draw=(now:number)=>{
      if(!mount.clientWidth){animation=requestAnimationFrame(draw);return;}
      const current=latest.current,physics=asset.current;
      if(current&&physics){
        for(const [link,pose] of Object.entries(current.frame.links)){
          position.fromArray(pose.position).multiplyScalar(1000);rotation.fromArray(pose.quaternion);
          const zero=physics.cadZeroOriginsM[link as LinkName];origin.makeTranslation(-zero[0]*1000,-zero[1]*1000,-zero[2]*1000);
          matrix.compose(position,rotation,scale).multiply(origin);
          for(const mesh of meshes.get(link as LinkName)??[]){mesh.matrix.copy(matrix);mesh.matrixWorldNeedsUpdate=true;}
          if(link==='head')headMatrix.copy(matrix);
        }
      }
      target.position.fromArray(targetPosition.current);controls.update();
      const contact=current?.frame.contacts;
      comMarker.visible=!!contact&&contactsVisible.current;contactMarkers.visible=contactsVisible.current;
      if(contact){
        comMarker.position.fromArray(contact.comWorldM).multiplyScalar(1000);
        const points=contact.points.filter(point=>(point.normalForceN??0)>.001).slice(0,128);contactMarkers.count=points.length;
        points.forEach((point,index)=>{matrix.makeTranslation(point.positionM[0]*1000,point.positionM[1]*1000,point.positionM[2]*1000+.5);contactMarkers.setMatrixAt(index,matrix);});contactMarkers.instanceMatrix.needsUpdate=true;
      }
      renderer.setRenderTarget(null);renderer.render(scene,camera);
      const captureKey=current?`${current.runId}:${current.frame.time}`:'';
      if(current&&physics&&(active.current==='camera-learning'?captureKey!==lastCapture:now-lastVision>=100)){
        // The camera sits at the front lens opening. The policy receives only these rendered pixels.
        sensorPosition.set(34.8,0,111).applyMatrix4(headMatrix);
        sensorForward.set(1,0,0).transformDirection(headMatrix);sensorUp.set(0,0,1).transformDirection(headMatrix);
        sensor.position.copy(sensorPosition);sensor.up.copy(sensorUp);sensor.lookAt(sensorPosition.clone().add(sensorForward));
        const savedComVisibility=comMarker.visible,savedContactVisibility=contactMarkers.visible;
        comMarker.visible=false;contactMarkers.visible=false;
        renderer.setRenderTarget(renderTarget);renderer.render(scene,sensor);
        renderer.readRenderTargetPixels(renderTarget,0,0,CAMERA_WIDTH,CAMERA_HEIGHT,pixels);renderer.setRenderTarget(null);
        comMarker.visible=savedComVisibility;contactMarkers.visible=savedContactVisibility;
        const observation=detectTarget(pixels,CAMERA_WIDTH,CAMERA_HEIGHT,CAMERA_FOV*Math.PI/180);setSeen(observation.visible);
        if(captureKey!==lastCapture&&(active.current==='camera'||active.current==='camera-learning'))worker.current?.postMessage({type:'observation',observation,runId:current.runId,frameTime:current.frame.time} satisfies SimulationCommand);
        for(let row=0;row<CAMERA_HEIGHT;row++)flipped.set(pixels.subarray(row*CAMERA_WIDTH*4,(row+1)*CAMERA_WIDTH*4),(CAMERA_HEIGHT-1-row)*CAMERA_WIDTH*4);
        preview.current?.getContext('2d')?.putImageData(new ImageData(flipped,CAMERA_WIDTH,CAMERA_HEIGHT),0,0);lastVision=now;lastCapture=captureKey;
      }
      animation=requestAnimationFrame(draw);
    };
    animation=requestAnimationFrame(draw);
    return()=>{
      disposed=true;controller.abort();cancelAnimationFrame(animation);observer.disconnect();controls.dispose();
      for(const group of meshes.values())group.forEach(disposeCadMesh);
      for(const mesh of [floor,grid,target,comMarker]){mesh.geometry.dispose();(mesh.material as T.Material).dispose();}
      contactGeometry.dispose();contactMaterial.dispose();contactMarkers.dispose();
      renderTarget.dispose();renderer.dispose();mount.removeChild(renderer.domElement);
    };
  },[data]);

  const moveTarget=(side:number)=>{
    setTargetSide(side);setVisionProgress(null);targetPosition.current=[180,side,50];send({type:'target',position:[.18,side/1000,.05]});
  };
  const changeEnvironment=(settings:EnvironmentSettings)=>{
    setEnvironment(settings);setPhysicsReady(false);setProgress(null);setHistory([]);setVisionProgress(null);
    send({type:'environment',settings});
  };
  const download=()=>{
    const blob=new Blob([JSON.stringify({schemaVersion:1,createdAt:new Date().toISOString(),scope:'Browser experiment only; not a hardware or Isaac policy',asset:asset.current,environment,policy,walkTraining:progress,cameraTraining:visionProgress},null,2)],{type:'application/json'});
    const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='microduckling-experiment.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  const chart=history.length>1?history.map((value,index)=>{
    const low=Math.min(...history),high=Math.max(...history);return `${8+index/(history.length-1)*234},${57-(value-low)/Math.max(.001,high-low)*48}`;
  }).join(' '):'';

  return <section className="simulation-workspace" aria-label="Simulation experiment">
    <div className="viewport-wrap"><div className="viewport" ref={host}/>
      <div className="view-caption"><span className="live-dot"/>PHYSICS LAB<span>Gravity · ground contact · four bounded servo motors</span></div>
      {(!ready||error)&&<div className="loading" role={error?'alert':'status'}>{error||'Starting the physics engine…'}</div>}
      <div className="simulation-telemetry"><span className="badge">{descriptions[mode]}</span><span>{((stats?.metrics.distanceM??0)*1000).toFixed(1)} mm forward</span><span>{((stats?.metrics.tiltRad??0)*180/Math.PI).toFixed(1)}° tilt</span><span>{stats?.metrics.fall?'Fall detected':`${(stats?.time??0).toFixed(1)} s simulated`}</span></div>
      <div className="sensor-preview"><div><ScanEye size={15}/><strong>Synthetic camera</strong><span>{seen?'Target visible':'Searching'}</span></div><canvas ref={preview} width={CAMERA_WIDTH} height={CAMERA_HEIGHT}/><p>96 × 72 pixels · magenta target detection</p></div>
    </div>
    <aside className="controls-panel simulation-controls">
      <div className="simulation-actions"><Button disabled={!ready} variant="outline" onClick={()=>run('paused')}><Pause size={15}/>Pause</Button><Button disabled={!ready} variant="outline" onClick={()=>send({type:'reset'})}><RotateCcw size={15}/>Reset</Button></div>
      <section className="contact-readout"><div className="section-heading"><h2>Weight & traction</h2><span>{((stats?.contacts?.totalMassKg??data.mass_g/1000)*1000).toFixed(0)} g</span></div>
        <div className="foot-loads">{(['left_leg','right_leg'] as const).map((leg,index)=>{const foot=stats?.contacts?.feet[leg];return <div key={leg} className={foot?.inContact?'loaded':''}><strong>{index===0?'Left foot':'Right foot'}</strong><span>{foot?.inContact?`${foot.normalForceN?.toFixed(2)??'—'} N estimated`:'No contact'}</span><small>{((foot?.slipSpeedMps??0)*1000).toFixed(1)} mm/s slip</small></div>;})}</div>
        <p className="help">Ground support {stats?.contacts?.groundNormalForceN?.toFixed(2)??'—'} N · weight {(stats?.contacts?.weightN??data.mass_g/1000*9.81).toFixed(2)} N</p>
        <Button variant="outline" aria-pressed={showContacts} onClick={()=>{contactsVisible.current=!showContacts;setShowContacts(!showContacts);}}>{showContacts?'Hide':'Show'} contact markers</Button><small className="contact-legend">Cyan: centre of mass · amber: loaded contacts</small>
        <details className="environment-settings"><summary>Surface & mass settings</summary><div className="joint"><div><label>Ground friction μ</label><output>{environment.groundFriction.toFixed(2)}</output></div><Slider aria-label="Ground friction coefficient" min={0} max={1.2} step={.05} value={[environment.groundFriction]} onValueChange={value=>changeEnvironment({...environment,groundFriction:Array.isArray(value)?value[0]:value})}/></div><div className="joint"><div><label>Mass scale</label><output>{Math.round(environment.massScale*100)}%</output></div><Slider aria-label="Simulation mass scale" min={.5} max={1.5} step={.05} value={[environment.massScale]} onValueChange={value=>changeEnvironment({...environment,massScale:Array.isArray(value)?value[0]:value})}/></div><p className="help">Gravity 9.81 m/s² · tread μ 0.90 · effective foot–floor μ {Math.min(.9,environment.groundFriction).toFixed(2)}. Coefficients are starting estimates. Changing settings resets training scores.</p></details>
      </section>
      <section><div className="section-heading"><h2>Learn a gait</h2><FlaskConical size={17}/></div><p className="help">Search 14-second physical trials for sustained forward travel and balance. The bundled gait is evaluated alongside neutral before searching.</p>
        <Button disabled={!ready||mode==='walk-learning'} onClick={()=>run('walk-learning')}>Start gait search</Button><Button variant="outline" disabled={!ready} onClick={()=>run('gait')}><Play size={15}/>{progress?'Play best gait':'Try reference gait'}</Button>
        {progress&&<div className="experiment-result" aria-live="polite"><strong>Generation {progress.generation} / 12</strong><span>{progress.episodesEvaluated} measured episodes</span><span>{(progress.bestDistanceM*1000).toFixed(2)} mm best · {progress.best.fall?'fell':'upright'}</span><span>{(progress.improvementM*1000).toFixed(2)} mm gain over neutral</span>{chart&&<svg viewBox="0 0 250 65" role="img" aria-label="Best episode reward by generation"><polyline points={chart} fill="none" stroke="#ffa660" strokeWidth="2"/></svg>}<span>{(progress.best.lateForwardSpeedMps*1000).toFixed(1)} mm/s sustained speed</span><small>{progress.bestOrigin==='search'?(progress.improvedOverSeed?'Search improved on the supplied gait.':'Search candidate leads the score; speed improvement is not established.'):'The supplied reference or neutral still leads; no new improvement yet.'}</small></div>}
      </section>
      <section><h2>See and approach</h2><p className="help">Use camera pixels to steer and stop. Training compares 12 settings in trials of up to 60 simulated seconds, scored by actual approach and balance.</p><div className="target-options" aria-label="Target position">{[40,0,-40].map((side,i)=><Button key={side} variant={side===targetSide?'default':'outline'} disabled={!ready} onClick={()=>moveTarget(side)}>{['Left','Ahead','Right'][i]}</Button>)}</div>
        <Button disabled={!ready||mode==='camera-learning'} onClick={()=>run('camera-learning')}>Train to target</Button><Button variant="outline" disabled={!ready} onClick={()=>run('camera')}>Try approach</Button>
        {goal&&<div className="experiment-result" aria-live="polite"><strong>{goal.success?'Target reached':goal.fallen?'Trial ended: fall':goal.nearTarget?'Holding near target':'Approaching target'}</strong><span>{(goal.progressM*1000).toFixed(1)} mm closer · {(goal.distanceM*1000).toFixed(0)} mm remaining centre distance</span><span>{goal.holdSeconds.toFixed(1)} / 1.5 s stable in the stopping zone</span><small>Success requires physical travel, an upright body and alignment with the target. Looking at it alone earns no progress.</small></div>}
        {visionProgress&&<div className="experiment-result" aria-live="polite"><strong>Trial {visionProgress.trial} / 12</strong><span>Score {visionProgress.score.toFixed(2)} · best {visionProgress.bestScore?.toFixed(2)??'—'}</span><span>{visionProgress.goal.success?'Reached target':visionProgress.fall?'Fell':'Target not reached'} · {(visionProgress.goal.progressM*1000).toFixed(1)} mm closer</span><span>Target visible {(visionProgress.visibleFraction*100).toFixed(0)}% of trial</span><span>Camera coverage {(visionProgress.coverageFraction*100).toFixed(0)}%{visionProgress.fall?' · fell':''}</span>{!visionProgress.eligible&&<span>Trial excluded: a fall or insufficient fresh camera frames.</span>}</div>}
      </section>
      <details className="pose-controls"><summary>Pose & forward lean</summary>{[{label:'Forward lean command',value:bow,set:setBow,min:-12,max:12},{label:'Neck',value:neck,set:setNeck,min:-45,max:45},{label:'Mouth',value:jaw,set:setJaw,min:0,max:12}].map(control=><div className="joint" key={control.label}><div><label>{control.label}</label><output>{control.value}°</output></div><Slider aria-label={control.label} min={control.min} max={control.max} step={1} value={[control.value]} onValueChange={value=>control.set(Array.isArray(value)?value[0]:value)}/></div>)}<Button disabled={!ready} onClick={()=>run('pose')}>Run servo pose</Button><p className="help">Both hips share the lean command. Actual body tilt depends on contact and balance; deeper bows need clearance tests.</p></details>
      <p className="help simulation-note">Experimental contact and servo models. Self-collision is omitted. A successful trial here does not establish physical walking or Isaac Sim transfer.</p>
      <Button variant="outline" disabled={!policy} onClick={download}><Download size={15}/>Save experiment</Button>
    </aside>
  </section>;
}
