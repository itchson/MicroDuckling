"use client";

import {lazy,Suspense,useEffect,useMemo,useRef,useState} from 'react';

import * as T from 'three';

import {OrbitControls} from 'three/addons/controls/OrbitControls.js';

import {Slider} from '@/components/ui/slider';

import {Checkbox} from '@/components/ui/checkbox';

import {Button} from '@/components/ui/button';

import {DownloadLink} from '@/components/download-link';
import {updateCameraClipping} from '@/lib/robot';
import {explodedLayout} from '@/lib/explode';
import {PartsTree} from '@/components/parts-tree';
import {Box,Grid2X2,RotateCcw,Download,Focus,Layers3,PanelLeft,FlaskConical} from 'lucide-react';

import {type Assembly,type Mode,type Part,type CadMeshData,createCadMesh,highlightCadMesh,disposeCadMesh,friendlyName,jointMatrix,isPrintable,isShell,isVisible,gridMatrix,validateViewRequest} from '@/lib/robot';

type Engine={scene:T.Scene; camera:T.PerspectiveCamera; controls:OrbitControls; renderer:T.WebGLRenderer; meshes:Map<string,T.Mesh>; grid:T.GridHelper; bounds:T.Box3; updateBounds:()=>void; fit:()=>void};

const modes:{id:Mode;label:string;Icon:typeof Box}[]=[{id:'assembly',label:'Model',Icon:Box},{id:'grid',label:'Print parts',Icon:Grid2X2}];

const initialAngles={left_hip:0,right_hip:0,neck_yaw:0,jaw_pitch:0};
const SimulationWorkspace=lazy(()=>import('@/components/simulation-workspace').then(module=>({default:module.SimulationWorkspace})));

export default function Home(){

  const host=useRef<HTMLDivElement>(null),engine=useRef<Engine|null>(null);

  const [data,setData]=useState<Assembly|null>(null),[status,setStatus]=useState('Loading MicroDuckling…');

  const [mode,setMode]=useState<Mode>('assembly'),[amount,setAmount]=useState(0);

  const [angles,setAngles]=useState<Record<string,number>>({...initialAngles});

  const [hidden,setHidden]=useState<string[]>([]),[selected,setSelected]=useState<string|null>(null);

  const [onlyPrint,setOnlyPrint]=useState(false),[internals,setInternals]=useState(false);

  const [partsOpen,setPartsOpen]=useState(false);
  const [simulation,setSimulation]=useState(false);
  const [simulationLoaded,setSimulationLoaded]=useState(false);
  const part=data?.parts.find(p=>p.name===selected);
  const layout=useMemo(()=>data?explodedLayout(data,angles):new Map<string,T.Vector3>(),[data,angles]);

  useEffect(()=>{

    const mount=host.current!;let disposed=false,frame=0,renderer:T.WebGLRenderer;

    try{renderer=new T.WebGLRenderer({antialias:true});}catch{setStatus('3D graphics are unavailable. Enable WebGL or use the CAD renders below.');return;}

    const scene=new T.Scene();scene.background=new T.Color('#101923');

    const camera=new T.PerspectiveCamera(36,1,.1,5000);camera.up.set(0,0,1);camera.position.set(225,-280,180);

    renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=T.SRGBColorSpace;

    mount.appendChild(renderer.domElement);

    renderer.domElement.setAttribute('aria-label','MicroDuckling 3D model. Drag to orbit; use the parts list to select components.');

    const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,0,67);controls.enableDamping=true;controls.minDistance=12;controls.maxDistance=3000;

    scene.add(new T.HemisphereLight(0xe6f1ff,0x354353,2.4));

    const key=new T.DirectionalLight(0xffffff,3);key.position.set(80,-140,240);scene.add(key);

    const fill=new T.DirectionalLight(0xbddfff,1.4);fill.position.set(-80,100,70);scene.add(fill);

    const grid=new T.GridHelper(1400,70,0x324457,0x1b2a39);grid.rotation.x=Math.PI/2;grid.position.z=-.4;scene.add(grid);

    const e:Engine={scene,camera,controls,renderer,meshes:new Map(),grid,bounds:new T.Box3(),updateBounds:()=>{
      e.bounds.makeEmpty();e.meshes.forEach(m=>{if(m.visible)e.bounds.expandByObject(m)});
    },fit:()=>{
      e.updateBounds();const b=e.bounds;if(b.isEmpty())return;
      const c=b.getCenter(new T.Vector3()),radius=b.getSize(new T.Vector3()).length()/2;

      const vfov=T.MathUtils.degToRad(camera.fov),hfov=2*Math.atan(Math.tan(vfov/2)*camera.aspect);

      const dir=camera.position.clone().sub(controls.target).normalize();

      controls.target.copy(c);camera.position.copy(c).addScaledVector(dir,Math.max(30,radius/Math.sin(Math.min(vfov,hfov)/2)*1.1));controls.update();

    }};engine.current=e;

    const resize=()=>{const w=mount.clientWidth,h=mount.clientHeight;if(!w||!h)return;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix()};

    const observer=new ResizeObserver(resize);observer.observe(mount);resize();

    let down=[0,0];renderer.domElement.onpointerdown=ev=>{down=[ev.clientX,ev.clientY]};

    renderer.domElement.onpointerup=ev=>{if(Math.hypot(ev.clientX-down[0],ev.clientY-down[1])>4)return;

      const r=renderer.domElement.getBoundingClientRect(),ray=new T.Raycaster();ray.setFromCamera(new T.Vector2((ev.clientX-r.left)/r.width*2-1,-(ev.clientY-r.top)/r.height*2+1),camera);

      const hit=ray.intersectObjects([...e.meshes.values()].filter(m=>m.visible))[0];setSelected(hit?hit.object.name:null);

    };

    const abort=new AbortController();

    void(async()=>{try{

      const r=await fetch('/cad/assembly.json',{signal:abort.signal,cache:'no-store'});if(!r.ok)throw Error('CAD assembly is unavailable.');const d:Assembly=await r.json();d.parts=d.parts.map(p=>({...p,label:friendlyName(p)}));

      await Promise.all(d.parts.map(async p=>{

        const rr=await fetch(`/cad/meshes/${p.name}.json?v=${d.cad_sha256}`,{signal:abort.signal});if(!rr.ok)throw Error(`Missing geometry: ${p.label}`);

        const me=await rr.json() as CadMeshData;if(disposed)return;

        const m=createCadMesh(me,p);m.name=p.name;m.matrixAutoUpdate=false;m.visible=p.kind!=='coupon';scene.add(m);e.meshes.set(p.name,m);

      }));

      if(!disposed){setData(d);setStatus('');e.fit();}

    }catch(err){if(!disposed)setStatus(err instanceof Error?err.message:'Unable to load CAD');}})();

    const draw=()=>{if(mount.clientWidth){controls.update();updateCameraClipping(camera,e.bounds);renderer.render(scene,camera);}frame=requestAnimationFrame(draw)};draw();
    return()=>{disposed=true;abort.abort();cancelAnimationFrame(frame);observer.disconnect();controls.dispose();e.meshes.forEach(disposeCadMesh);grid.geometry.dispose();(grid.material as T.Material).dispose();renderer.dispose();mount.removeChild(renderer.domElement);engine.current=null;};

  },[]);

  useEffect(()=>{

    const e=engine.current;if(!e||!data)return;

    e.grid.visible=mode!=='explode'||amount===0;

    const printable=data.parts.filter(isPrintable);

    data.parts.forEach(p=>{

      const m=e.meshes.get(p.name);if(!m)return;

      m.visible=isVisible(p,{mode,hidden,onlyPrint,internals});

      let transform=new T.Matrix4();

      if(mode==='grid'){

        transform=gridMatrix(p,printable.indexOf(p));

      }else{

        if(p.joint)transform=jointMatrix(p.joint,data.joints,angles);

        if(mode==='explode'){const v=(layout.get(p.name)??new T.Vector3()).clone().multiplyScalar(amount/100);transform.premultiply(new T.Matrix4().makeTranslation(v.x,v.y,v.z));}

      }

      m.matrix.copy(transform);m.matrixWorldNeedsUpdate=true;

      highlightCadMesh(m,p.name===selected);
    });
    e.updateBounds();
  },[data,mode,amount,angles,hidden,onlyPrint,internals,selected,layout]);

  useEffect(()=>{const id=setTimeout(()=>engine.current?.fit(),70);return()=>clearTimeout(id)},[mode,data,onlyPrint,internals,amount]);

  const toggle=(name:string)=>{

    const p=data?.parts.find(p=>p.name===name);if(!p)return;

    if(!isVisible(p,{mode,hidden,onlyPrint,internals})){setHidden(h=>h.filter(n=>n!==name));if(isShell(p))setInternals(false);if(p.kind==='coupon')setMode('grid');}

    else setHidden(h=>[...h,name]);

  };

  const select=(p:Part)=>{setSelected(p.name);setHidden(h=>h.filter(n=>n!==p.name));if(isShell(p))setInternals(false);if(!isPrintable(p))setOnlyPrint(false);if(p.kind==='coupon')setMode('grid');};

  const reset=()=>{setSimulation(false);setMode('assembly');setAngles({...initialAngles});setAmount(0);setHidden([]);setSelected(null);setOnlyPrint(false);setInternals(false);setTimeout(()=>engine.current?.fit(),80)};

  const isolate=()=>{if(!data||!part)return;setInternals(false);setOnlyPrint(false);setHidden(data.parts.filter(p=>p.name!==part.name).map(p=>p.name));setTimeout(()=>engine.current?.fit(),70)};

  const visibleParts=data?.parts.filter(p=>(!onlyPrint||isPrintable(p))&&(mode!=='grid'||isPrintable(p)))??[];

  useEffect(()=>{

    if(!data)return;

    type Registry={registerTool:(tool:{name:string;description:string;inputSchema:object;annotations:object;execute:(input:unknown)=>Promise<unknown>},options:{signal:AbortSignal})=>void|Promise<void>};

    const context=(document as Document&{modelContext?:Registry}).modelContext;if(!context?.registerTool)return;

    const life=new AbortController();

    try{void Promise.resolve(context.registerTool({

      name:'configure_microduckling_view',description:'Configure the displayed CAD view, selected part and four joint poses. Changes the viewer only; does not command robot hardware.',

      inputSchema:{type:'object',properties:{mode:{type:'string',enum:['assembly','explode','grid']},part:{type:'string',enum:data.parts.map(p=>p.name)},internals:{type:'boolean'},angles:{type:'object',properties:Object.fromEntries(Object.entries(data.joints).map(([k,j])=>[k,{type:'number',minimum:j.limits[0],maximum:j.limits[1]}])),additionalProperties:false}},additionalProperties:false},

      annotations:{readOnlyHint:false,untrustedContentHint:false},

      execute:async input=>{

        const q=validateViewRequest(input,data);
        setSimulation(false);

        if(q.mode){setMode(q.mode);setHidden([]);setInternals(false);setSelected(null);}

        if(q.part){const p=data.parts.find(p=>p.name===q.part)!;setSelected(p.name);setHidden(h=>h.filter(n=>n!==p.name));setOnlyPrint(false);setInternals(false);setMode(p.kind==='coupon'?'grid':q.mode??'assembly');}

        if(q.internals!==undefined)setInternals(q.internals);

        if(q.angles)setAngles(a=>({...a,...q.angles}));

        await new Promise<void>(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>resolve())));

        return {applied:true,requested:q};

      },

    },{signal:life.signal})).catch(()=>{});}catch{/* Optional browser registry. Ordinary controls remain available. */}

    return()=>life.abort();

  },[data]);

  return <main className="cad-app">

    <header className="topbar"><div className="brand"><img className="brand-logo" src="/brand/microduckling-mascot.png" alt=""/><div><strong>MicroDuckling</strong><span>R07 prototype · {data?.revision??'CAD'}</span></div></div>
      <nav aria-label="Workspace">{modes.map(({id,label,Icon})=><Button key={id} variant={!simulation&&(mode===id||(id==='assembly'&&mode==='explode'))?'default':'ghost'} aria-pressed={!simulation&&(mode===id||(id==='assembly'&&mode==='explode'))} onClick={()=>{setSimulation(false);setMode(id==='assembly'&&amount>0?'explode':id);setInternals(false);setHidden([]);setSelected(null)}}><Icon size={17}/>{label}</Button>)}<Button variant={simulation?'default':'ghost'} aria-pressed={simulation} disabled={!data} onClick={()=>{setSimulationLoaded(true);setSimulation(true)}}><FlaskConical size={17}/>Simulation</Button></nav>

      <div className="header-actions">{!simulation&&<><Button variant="outline" aria-expanded={partsOpen} aria-controls="parts-panel" onClick={()=>setPartsOpen(v=>!v)}><PanelLeft size={16}/>Parts</Button><Button variant="outline" onClick={reset}><RotateCcw size={16}/>Reset</Button></>}<a href="https://github.com/itchson/MicroDuckling" target="_blank" rel="noreferrer">GitHub ↗</a></div>

    </header>

    <section style={simulation?{display:'none'}:undefined} className={`workspace ${partsOpen?'parts-open':'parts-closed'}`}>

      {partsOpen&&<aside id="parts-panel" className="parts-panel" aria-label="Assembly parts">
        <div className="panel-heading"><h2>Assembly</h2><span>{data?.parts.filter(p=>p.kind!=='coupon').length??'—'} components</span></div>
        <label className="filter"><Checkbox checked={onlyPrint} onCheckedChange={v=>setOnlyPrint(!!v)}/>Printed parts only</label>
        <div className="part-list"><PartsTree parts={visibleParts} selected={selected} visible={p=>isVisible(p,{mode,hidden,onlyPrint,internals})} onSelect={select} onToggle={toggle}/></div>
      </aside>}

      <div className="viewport-wrap"><div className="viewport" ref={host}/>{status&&<div className="loading" role="status">{status}<a href="/renders/assembled.png" target="_blank" rel="noreferrer">Open CAD render ↗</a></div>}

        <div className="view-caption"><span className="live-dot"/>{mode==='grid'?'PRINTED PARTS & FIT COUPONS':mode==='explode'?'EXPLODED ASSEMBLY':internals?'INTERNAL ARRANGEMENT':'ASSEMBLED'}<span>Drag to orbit · scroll to zoom · click a part</span></div>

        <div className="view-tools"><Button variant="secondary" onClick={()=>engine.current?.fit()}><Focus size={16}/>Fit</Button><Button variant="secondary" disabled={!part} onClick={isolate}>Isolate</Button><Button variant="secondary" onClick={()=>{setHidden([]);setInternals(false);setOnlyPrint(false)}}>Show all</Button>{mode!=='grid'&&<Button variant={internals?'default':'secondary'} aria-pressed={internals} onClick={()=>setInternals(v=>!v)}><Layers3 size={16}/>Inside</Button>}</div>

        <div className="model-status"><span className="badge">Fit prototype</span><span>{data?`${data.mass_g.toFixed(0)} g estimated · 136 mm tall`:'Four MG90S servos'}</span><p>{mode==='grid'?'Part inspection layout. Choose print orientation and supports in your slicer.':'Estimated assembled mass · physical build unverified.'}</p></div>

      </div>

      <aside className="controls-panel" aria-label="Model controls">

        {mode!=='grid'&&<section><div className="section-heading"><h2>Assembly</h2><span>{amount===0?'Assembled':`${amount}% exploded`}</span></div><div className="slider-line"><Slider aria-label="Part separation" min={0} max={100} step={1} value={[amount]} onValueChange={v=>{const value=Array.isArray(v)?v[0]:v;setAmount(value);setMode(value===0?'assembly':'explode')}}/><output>{amount}%</output></div><p className="help">At 100%, every component has a separate space. The transition illustrates disassembly.</p></section>}

        {mode!=='grid'&&<section><h2>Four servo joints</h2>{data&&Object.entries(data.joints).map(([id,j])=><div className="joint" key={id}><div><label>{j.label}</label><output>{angles[id]??0}°</output></div><Slider aria-label={j.label} min={j.limits[0]} max={j.limits[1]} step={1} value={[angles[id]??0]} onValueChange={v=>setAngles(a=>({...a,[id]:Array.isArray(v)?v[0]:v}))}/></div>)}<p className="help">Pose the CAD within its proposed travel. These controls do not run a walking simulation.</p></section>}

        <section className="part-detail"><h2>{part?'Selected part':'Part details'}</h2>{part?<><h3>{part.label}</h3><span className="badge">{part.kind==='print'?'Printed part':part.kind==='coupon'?'Fit coupon':part.kind==='tread'?'Traction layer':part.kind==='harness'?'Illustrative cable route':'Purchased component'}</span><dl><div><dt>Dimensions</dt><dd>{[0,1,2].map(i=>(part.bbox[i+3]-part.bbox[i]).toFixed(1)).join(' × ')} mm</dd></div>{part.pcb_dimensions_mm&&<div><dt>PCB outline</dt><dd>{part.pcb_dimensions_mm.slice(0,2).map(v=>v.toFixed(2)).join(' × ')} mm</dd></div>}<div><dt>Est. mass</dt><dd>{part.mass_g.toFixed(2)} g</dd></div></dl><p className="help">{part.note}</p>{isPrintable(part)&&<div className="downloads">{Object.entries(part.downloads).map(([format,url])=><DownloadLink key={format} href={url} download><Download size={15}/>{format.toUpperCase()}</DownloadLink>)}</div>}</>:<p className="help">Choose a component in the model or parts list to inspect its dimensions and download its files.</p>}</section>

        <details className="export-menu"><summary>Downloads & credits</summary><DownloadLink href="/downloads/MicroDuckling_R05_printed.step" download>Printed parts · STEP</DownloadLink><DownloadLink href="/downloads/MicroDuckling_R05_mechanical.FCStd" download>Mechanical model · FreeCAD</DownloadLink><p className="help">Board adaptations: Limor Fried / Adafruit, adapted by MicroDuckling contributors · CC BY-SA 3.0.</p><a href="https://github.com/itchson/MicroDuckling/blob/main/THIRD_PARTY_NOTICES.md" target="_blank" rel="noreferrer">Asset credits & licenses ↗</a></details>

      </aside>

    </section>

    {simulationLoaded&&data&&<div className="simulation-container" style={simulation?undefined:{display:'none'}}><Suspense fallback={<div className="simulation-loading" role="status">Loading simulation…</div>}><SimulationWorkspace data={data} visible={simulation}/></Suspense></div>}

  </main>;

}
