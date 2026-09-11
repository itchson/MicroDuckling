import {Eye,EyeOff} from 'lucide-react';
import type {ReactNode} from 'react';
import {type Part} from '@/lib/robot';

type Props={parts:Part[];selected:string|null;visible:(part:Part)=>boolean;onSelect:(part:Part)=>void;onToggle:(name:string)=>void};
const fastener=/Screw|Nut|Horn|Shim/;
function bucket(p:Part):string {
  if(p.kind==='coupon')return 'Fit coupons';
  if(p.kind==='print')return 'Printed structure';
  if(p.kind==='harness'||/Strap|Pad|Tread/.test(p.name))return 'Wiring & soft parts';
  if(fastener.test(p.name))return 'Horns & fasteners';
  if(/^Servo(Left|Right|Neck|Mouth)$/.test(p.name))return 'Servos';
  if(/^(ESP32CAM|OV2640Camera|IMU|ServoController|Battery|Buck_\d)$/.test(p.name))return 'Electronics';
  return 'Mechanical hardware';
}
export function PartsTree({parts,selected,visible,onSelect,onToggle}:Props){
  const categories=(items:Part[])=>items.reduce<Record<string,Part[]>>((out,p)=>{(out[bucket(p)]??=[]).push(p);return out},{});
  const leaf=(p:Part)=><li key={p.name} className={`part-row ${selected===p.name?'active':''}`}><button className="eye-button" aria-label={`${visible(p)?'Hide':'Show'} ${p.label}`} onClick={()=>onToggle(p.name)}>{visible(p)?<Eye size={15}/>:<EyeOff size={15}/>}</button><button className="part-select" aria-pressed={selected===p.name} title={p.label} onClick={()=>onSelect(p)}><i style={{background:p.color}}/><span>{p.label}</span></button></li>;
  const group=(title:string,items:Part[],nested?:ReactNode,descendants:Part[]=[])=>items.length||nested?<li key={title}><details open={[...items,...descendants].some(p=>p.name===selected)||undefined}><summary>{title}<span>{items.length+descendants.length||''}</span></summary><ul>{Object.entries(categories(items)).map(([name,children])=><li key={name}><details open={children.some(p=>p.name===selected)||undefined}><summary>{name}<span>{children.length}</span></summary><ul>{children.map(leaf)}</ul></details></li>)}{nested}</ul></details></li>:null;
  const ordinary=parts.filter(p=>p.kind!=='coupon');
  return <ul className="parts-tree" aria-label="Robot component hierarchy"><li><details open><summary>MicroDuckling<span>{parts.length}</span></summary><ul>
    {group('Body',ordinary.filter(p=>p.link==='body'))}
    {group('Head',ordinary.filter(p=>p.link==='head'),group('Mouth',ordinary.filter(p=>p.link==='jaw')),ordinary.filter(p=>p.link==='jaw'))}
    {group('Legs',[],<>{group('Left leg',ordinary.filter(p=>p.link==='left_leg'))}{group('Right leg',ordinary.filter(p=>p.link==='right_leg'))}</>,ordinary.filter(p=>p.link==='left_leg'||p.link==='right_leg'))}
    {group('Fit coupons',parts.filter(p=>p.kind==='coupon'))}
  </ul></details></li></ul>;
}
