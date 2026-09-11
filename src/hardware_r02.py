"""Purchased electronics geometry in millimetres; local PCB XY, bottom Z=0.

Adafruit XY outlines, holes, pads and package placements come directly from
the saved manufacturer Eagle files. Unlisted Z dimensions and generic fitted
header details are explicit modeling assumptions, not measured vendor CAD.
Pololu collision geometry is the unmodified vendor STEP. Its view groups
partition the original faces, with heuristic colors only.

Every public function returns shape, components[{name,shape,color}],
pcb_dimensions_mm, mount_holes[[x,y,diameter]], notes, and source_files.
Components contain exactly the displayed geometry; no invisible substitute
box replaces the returned collision solid/compound. A camera on its flex is
intentionally separate from esp32cam(). This module does not write files.
"""
from pathlib import Path
import math
import xml.etree.ElementTree as ET
import FreeCAD as App
import Part

REF = Path(__file__).resolve().parents[1] / "references/components_r02"
V = App.Vector
BLUE, BLACK, GOLD, SILVER = "#155a83", "#24262a", "#cfa956", "#b8bec4"
TAN, WHITE, GREEN = "#9b8964", "#e6e7de", "#47af61"


def _box(x, y, z, dx, dy, dz):
    return Part.makeBox(dx, dy, dz, V(x, y, z))


def _cyl(x, y, z, radius, height):
    return Part.makeCylinder(radius, height, V(x, y, z))


def _compound(shapes):
    return Part.makeCompound(shapes)


def _item(items, name, shape, color):
    if shape.isNull() or not shape.isValid():
        raise RuntimeError("Invalid hardware geometry: " + name)
    items.append(dict(name=name, shape=shape, color=color))


def _result(items, pcb, holes, notes, sources, shape=None, **metadata):
    shape = shape if shape is not None else _compound([x["shape"] for x in items])
    if shape.isNull() or not shape.isValid() or not shape.Solids:
        raise RuntimeError("Invalid complete hardware geometry")
    return dict(shape=shape, components=items, pcb_dimensions_mm=pcb,
                mount_holes=holes, notes=notes, source_files=list(sources), **metadata)


def _arc_wire(node, offset):
    x1,y1,x2,y2 = [float(node.get(k)) for k in ("x1","y1","x2","y2")]
    start,end = V(x1+offset[0],y1+offset[1],0),V(x2+offset[0],y2+offset[1],0)
    angle = math.radians(float(node.get("curve",0)))
    if abs(angle) < 1e-10:
        return Part.makeLine(start,end)
    delta=end-start
    center=(start+end)*.5+V(-delta.y,delta.x,0)*(1/(2*math.tan(angle/2)))
    arm=start-center;c,s=math.cos(angle/2),math.sin(angle/2)
    mid=center+V(arm.x*c-arm.y*s,arm.x*s+arm.y*c,0)
    return Part.Arc(start,mid,end).toShape()


def _placement(shape, element, offset):
    shape=shape.copy();rotation=element.get("rot","R0")
    if "M" in rotation:
        shape=shape.mirror(V(),V(1,0,0))
    shape.rotate(V(),V(0,0,1),float(rotation.split("R")[-1]))
    shape.translate(V(float(element.get("x"))+offset[0],float(element.get("y"))+offset[1],0))
    return shape


def _point(element, x, y, offset):
    rotation=element.get("rot","R0");angle=math.radians(float(rotation.split("R")[-1]))
    if "M" in rotation:x=-x
    return [float(element.get("x"))+offset[0]+x*math.cos(angle)-y*math.sin(angle),
            float(element.get("y"))+offset[1]+x*math.sin(angle)+y*math.cos(angle)]


def _eagle(filename, thickness):
    path=REF/filename
    board=ET.parse(path).getroot().find("./drawing/board")
    edges=board.findall("./plain/wire[@layer='20']")
    xmin=min(float(n.get(k)) for n in edges for k in ("x1","x2"))
    ymin=min(float(n.get(k)) for n in edges for k in ("y1","y2"))
    xmax=max(float(n.get(k)) for n in edges for k in ("x1","x2"))
    ymax=max(float(n.get(k)) for n in edges for k in ("y1","y2"))
    offset=(-xmin,-ymin)
    pcb=Part.Face(Part.Wire([_arc_wire(n,offset) for n in edges])).extrude(V(0,0,thickness))
    packages={(lib.get("name"),p.get("name")):p for lib in board.findall("./libraries/library")
              for p in lib.findall("./packages/package")}
    elements={e.get("name"):e for e in board.findall("./elements/element")}
    holes=[];drills=[];pads=[];pad_metadata=[]
    for name,e in elements.items():
        package=packages[(e.get("library"),e.get("package"))]
        for p in package:
            if p.tag not in ("pad","smd","hole"):continue
            x,y=float(p.get("x")),float(p.get("y"));xy=_point(e,x,y,offset)
            diameter=float(p.get("drill",0))
            if diameter:
                drills.append(_cyl(*xy,-.1,diameter/2,thickness+.2))
                if "MOUNTINGHOLE" in e.get("package"):
                    holes.append(xy+[diameter])
            if p.tag=="hole":continue
            if p.tag=="pad":
                copper_d=float(p.get("diameter",diameter+.7))
                if p.get("shape") in ("square","octagon"):
                    count=4 if p.get("shape")=="square" else 8
                    radius=copper_d/math.sqrt(2) if count==4 else copper_d/(2*math.cos(math.pi/8))
                    angle=math.pi/4 if count==4 else math.pi/8
                    points=[V(x+radius*math.cos(angle+i*2*math.pi/count),y+radius*math.sin(angle+i*2*math.pi/count),thickness) for i in range(count)]
                    q=Part.Face(Part.makePolygon(points+points[:1])).extrude(V(0,0,.035))
                else:q=_cyl(x,y,thickness,copper_d/2,.035)
                q=q.cut(_cyl(x,y,thickness-.01,diameter/2,.06))
                pads.append(_placement(q,e,offset))
                bottom=q.copy();bottom.translate(V(0,0,-thickness-.035));pads.append(_placement(bottom,e,offset))
            else:
                dx,dy=float(p.get("dx")),float(p.get("dy"))
                q=_box(-dx/2,-dy/2,0,dx,dy,.035)
                q.rotate(V(),V(0,0,1),float(p.get("rot","R0").split("R")[-1]))
                q.translate(V(x,y,-.035 if "M" in e.get("rot","") else thickness))
                pads.append(_placement(q,e,offset))
            pad_metadata.append(dict(element=name,pad=p.get("name"),xy_mm=xy,drill_mm=diameter))
    # Include the manufacturer's plain mechanical holes and via drill positions.
    for node in list(board.findall("./plain/hole"))+list(board.findall("./signals/signal/via")):
        drills.append(_cyl(float(node.get("x"))+offset[0],float(node.get("y"))+offset[1],-.1,float(node.get("drill"))/2,thickness+.2))
    if drills:pcb=pcb.cut(_compound(drills))
    return dict(pcb=pcb,pads=pads,holes=holes,elements=elements,packages=packages,offset=offset,
                dimensions=[xmax-xmin,ymax-ymin,thickness],pad_metadata=pad_metadata,source=path.name)


def _body(items,data,name,rect,height,color=BLACK,z=None):
    e=data["elements"][name]
    x,y,dx,dy=rect;z=data["dimensions"][2] if z is None else z
    _item(items,name,_placement(_box(x,y,z,dx,dy,height),e,data["offset"]),color)


def _headers(items,data,name,thickness):
    e=data["elements"][name];p=data["packages"][(e.get("library"),e.get("package"))]
    pins=[(float(n.get("x")),float(n.get("y"))) for n in p.findall("pad")]
    xmin=min(x for x,y in pins)-1.27;ymin=min(y for x,y in pins)-1.27
    dx=max(x for x,y in pins)-xmin+1.27;dy=max(y for x,y in pins)-ymin+1.27
    housing=_box(xmin,ymin,thickness,dx,dy,2.5)
    for x,y in pins:housing=housing.cut(_box(x-.32,y-.32,thickness-.1,.64,.64,2.7))
    _item(items,name+"_housing",_placement(housing,e,data["offset"]),BLACK)
    _item(items,name+"_pins",_placement(_compound([_box(x-.32,y-.32,-3,.64,.64,thickness+11.5) for x,y in pins]),e,data["offset"]),GOLD)


def _small_parts(items,data,skip):
    packages={"0805-NO":(-1,-.625,2,1.25,.8),"0603-NO":(-.8,-.4,1.6,.8,.6),
              "_0805MP":(-1,-.625,2,1.25,.6),"RESPACK_4X0603":(-1.6,-.8,3.2,1.6,.65),
              "SOT23-5":(-1.4224,-.8104,2.8448,1.6208,1.1),"SOT363":(-1,-.65,2,1.3,1.1),
              "SOD-323":(-.9,-.625,1.8,1.25,1.0),"LGA-14L":(-1.5,-1.25,3,2.5,1.1),
              "CHIPLED_0805_NOOUTLINE":(-1,-.625,2,1.25,.8),"CHIPLED_0603_NOOUTLINE":(-.8,-.4,1.6,.8,.7)}
    for name,e in data["elements"].items():
        package=e.get("package")
        if name in skip or package not in packages or "M" in e.get("rot",""):continue
        x,y,dx,dy,h=packages[package]
        color=GREEN if "LED" in package else TAN if name.startswith("C") else BLACK
        _body(items,data,name,(x,y,dx,dy),h,color)


def pca9685():
    """Adafruit rev C, four fitted 3×4 banks and one fitted six-pin I²C bus."""
    t=1.6;d=_eagle("Adafruit PCA9685 rev C.brd",t);items=[]
    _item(items,"PCA9685_PCB",d["pcb"],BLUE);_item(items,"PCB_plated_pads",_compound(d["pads"]),GOLD)
    for name in ("JP1","JP2","JP5","JP6","JP3"):_headers(items,d,name,t)
    _body(items,d,"U1",(-4.4646,-2.2828,8.9292,4.5656),1.2)
    e=d["elements"]["U1"];p=d["packages"][(e.get("library"),e.get("package"))]
    leads=[]
    for rect in p.findall("rectangle[@layer='51']"):
        x1,y1,x2,y2=[float(rect.get(k)) for k in ("x1","y1","x2","y2")]
        leads.append(_box(min(x1,x2),min(y1,y2),t,max(abs(x2-x1),.05),max(abs(y2-y1),.05),.22))
    _item(items,"U1_28_leads",_placement(_compound(leads),e,d["offset"]),SILVER)
    _body(items,d,"Q1",(-3.277,-2.159,6.554,5.9944),2.3)
    e=d["elements"]["J1"];terminal=_box(-3.4,-3.6,t,7,7,8.5);screws=[]
    for x in (-1.7,1.8):
        terminal=terminal.cut(_cyl(x,0,t+5.0,1.3,3.7))
        terminal=terminal.cut(Part.makeCylinder(1.2,3,V(x,-3.8,t+2.8),V(0,1,0)))
        screws.append(_cyl(x,0,t+6.1,1.12,1.4).cut(_box(x-1.3,-.2,t+7.0,2.6,.4,.6)))
    _item(items,"J1_terminal",_placement(terminal,e,d["offset"]),"#2f6da0")
    _item(items,"J1_screws",_placement(_compound(screws),e,d["offset"]),SILVER)
    _small_parts(items,d,{"U1","Q1","C2"})
    return _result(items,d["dimensions"],d["holes"],
        "Manufacturer rev C Eagle defines exact XY outline, drill and package/pad positions; supplied parts fitted as four 12-pin banks and one 6-pin side bus. JP4 and optional bulk capacitor C2 remain unpopulated. PCB thickness1.6, header .64-square pins Z-3..10.1, 2.5 housing height, terminal8.5 above PCB, and other component Z dimensions are conservative generic assumptions requiring sample measurement. Package bodies are simplified footprint-based envelopes, not vendor mechanical CAD.",
        [d["source"]],electrical_pads=d["pad_metadata"],fitted_pin_count=54)


def imu():
    """Adafruit 4503 LSM6DS3TR-C; bare header pads and two fitted QT sockets."""
    t=1.6;d=_eagle("Adafruit_LSM6DS3.brd",t);items=[]
    _item(items,"LSM6DS3_PCB",d["pcb"],BLUE);_item(items,"PCB_plated_pads",_compound(d["pads"]),GOLD)
    _small_parts(items,d,set())
    for name in ("CONN3","CONN4"):
        e=d["elements"][name];housing=_box(-3,-2.086,t,6.1,4.25,3)
        housing=housing.cut(_box(-2.2,-2.2,t+.8,4.4,2.8,1.35))
        _item(items,name+"_QT_socket",_placement(housing,e,d["offset"]),WHITE)
        contacts=_compound([_box(x-.1,-1.7,t+.9,.2,2,.2) for x in (-1.5,-.5,.5,1.5)])
        _item(items,name+"_contacts",_placement(contacts,e,d["offset"]),GOLD)
    return _result(items,d["dimensions"],d["holes"],
        "XY outline, pads, two mechanical holes and placements from manufacturer Eagle. Header pins omitted for direct soldering; both STEMMA QT connectors shown. Manufacturer lists4.6mm assembled height; 1.6mm PCB and3.0mm QT envelope chosen to match that overall bound. Individual component heights, contact geometry and connector mating clearances are unverified.",
        [d["source"]],electrical_pads=d["pad_metadata"],fitted_pin_count=0)


def esp32cam():
    """Ai-Thinker board, camera side +Z, RF shield/antenna/headers at -Z."""
    items=[];t=1.;pcb=_box(0,0,0,27,40.5,t)
    pcb=pcb.makeFillet(2.0,[e for e in pcb.Edges if abs(e.BoundBox.ZLength-t)<1e-6])
    xs=(2.07,24.93);ys=[4.58+2.54*i for i in range(8)];pads=[];pins=[]
    for x in xs:
        for y in ys:
            pcb=pcb.cut(_cyl(x,y,-.1,.5,1.2))
            for z in (-.035,t):pads.append(_cyl(x,y,z,.9,.035).cut(_cyl(x,y,z-.01,.5,.06)))
            pins.append(_box(x-.32,y-.32,-8.5,.64,.64,9.7))
        h=_box(x-1.27,ys[0]-1.27,-2.5,2.54,20.32,2.5)
        for y in ys:h=h.cut(_box(x-.32,y-.32,-2.6,.64,.64,2.7))
        _item(items,"rear_header_"+str(x),h,BLACK)
    _item(items,"ESP32CAM_PCB",pcb,"#171b1b");_item(items,"header_pads",_compound(pads),GOLD)
    _item(items,"16_header_pins",_compound(pins),GOLD)
    _item(items,"RF_module_substrate",_box(4.7,13.5,-.8,17.6,25.4,.8),"#21433e")
    shield=_box(5.1,14.4,-2.0,16.8,18.5,1.2)
    _item(items,"AiThinker_RF_shield",shield,SILVER)
    # The published image's antenna meander is mirrored into the camera-front
    # coordinate system. Its trace widths and segments are illustrative.
    antenna=[]
    for x in (7,11.4,15.8,20.2):antenna.append(_box(x,35,-.84,.35,3.4,.04))
    for x,y in ((7,38.05),(9.2,35),(11.4,38.05),(13.6,35),(15.8,38.05),(18,35)):
        antenna.append(_box(x,y,-.84,2.55,.35,.04))
    _item(items,"PCB_antenna_trace",_compound(antenna),GOLD)
    _item(items,"RF_module_castellations",_compound([_box(x,y,-.85,1,.6,.85) for x in (4.1,21.9) for y in [14.6+1.25*i for i in range(14)]]),SILVER)
    _item(items,"reset_switch",_box(18.5,.9,-2,3.6,3.5,2),SILVER)
    _item(items,"reset_button",_cyl(20.3,2.65,-2.5,1.1,.5),BLACK)
    _item(items,"rear_regulator",_box(4,1.2,-1.4,6.3,4.3,1.4),BLACK)
    # Published front image: SD cage at antenna end; FFC latch near bottom.
    cage=_box(5.8,25,t,15.2,15.5,1.5)
    cage=cage.cut(_box(6.15,25.25,t-.02,14.5,15.5,1.17))
    for x in (9.5,17):cage=cage.cut(_box(x,28.5,t+1.15,.7,2.7,.6))
    _item(items,"microSD_metal_cage",cage,SILVER)
    _item(items,"microSD_contact_bed",_box(6.15,25.25,t,14.5,2.3,.3),BLACK)
    ffc_latch=_box(5.7,12.8,t+.85,15.6,.7,.5)
    ffc_connector=_box(5.7,12.8,t,15.6,2.8,1.15).cut(ffc_latch).removeSplitter()
    _item(items,"camera_FFC_connector",ffc_connector,WHITE)
    _item(items,"camera_FFC_latch",ffc_latch,BLACK)
    _item(items,"camera_FFC_contacts",_compound([_box(7+.5*i,12.1,t,.2,.7,.16) for i in range(24)]),SILVER)
    _item(items,"flash_LED_frame",_box(23,9.6,t,3.1,3.1,.65),WHITE)
    _item(items,"flash_LED_emitter",_cyl(24.55,11.15,t+.65,1.12,.2),"#e3da70")
    passives=[];terminals=[]
    for x,y,dx,dy in [(10.2,20,3.8,4.1),(18,20.4,2.2,2.8),(5.2,21.1,1.2,2),(20.8,19.2,1.2,2),
                      (8.1,8,1.2,2),(10.1,8,1.2,2),(12.1,8,1.2,2),(14.1,8,1.2,2),(16.1,8,1.2,2)]:
        passives.append(_box(x,y,t,dx,dy,.65))
        terminals.extend([_box(x,y-.15,t,dx,.25,.22),_box(x,y+dy-.1,t,dx,.25,.22)])
    smt_terminations=_compound(terminals)
    _item(items,"front_SMT_components",_compound(passives).cut(smt_terminations).removeSplitter(),BLACK)
    _item(items,"front_SMT_terminations",smt_terminations,SILVER)
    return _result(items,[27,40.5,t],[],
        "Ai-Thinker V1.0 drawing verifies27mm width,22.86mm header row spacing,2.54mm pitch and4.58mm bottom pin offset. Text says40.5mm length while drawing says40mm: conservative40.5 used; verify actual sample. PCB1.0mm, R2 corners, fitted.64-square headers and all non-pad component XY/height envelopes inferred conservatively from manufacturer illustration, not a manufacturing drawing. RF and headers are rear(-Z), SD/FFC/flash front(+Z). No OV2640/lens/flex registration is represented; the camera must be modeled and adjusted independently.",
        ["Ai-Thinker-ESP32-CAM-V1.0.pdf"],header_rows_x_mm=list(xs),header_y_mm=ys,fitted_pin_count=16)


def pololu(filename="Pololu-D24V50F5.step"):
    """Read the original manufacturer STEP; color groups reuse its faces."""
    path=Path(filename);path=path if path.is_absolute() else REF/path
    if not path.is_file():raise FileNotFoundError(path)
    shape=Part.read(str(path));b=shape.BoundBox
    if "D24V50" in path.name:
        pcb=[17.78,20.32,1.5748];holes=[[2.159,2.159,2.1844],[15.621,18.161,2.1844]]
    elif "D24V10" in path.name:pcb=[12.7,17.78,1.016];holes=[]
    elif "D24V5" in path.name:pcb=[10.16,12.7,1.016];holes=[]
    else:raise ValueError("PCB datum not recorded for this STEP filename")
    groups={"PCB":[],"component_bodies":[],"metal_surfaces":[]}
    for face in shape.Faces:
        z=face.BoundBox
        if z.ZMin>=-1e-5 and z.ZMax<=pcb[2]+1e-5:group="PCB"
        elif (z.ZLength>4.5 or z.ZMin>pcb[2]+5
              or (z.ZMin>=pcb[2]-.01 and z.ZMax<=pcb[2]+.6)
              or (z.ZMax<=0 and z.ZMin>=-.3)):group="metal_surfaces"
        else:group="component_bodies"
        groups[group].append(face)
    items=[]
    for name,color in (("PCB",BLUE),("component_bodies",BLACK),("metal_surfaces",SILVER)):
        if groups[name]:_item(items,name,_compound(groups[name]),color)
    return _result(items,pcb,holes,
        "Collision B-rep is the unmodified manufacturer STEP in its native PCB-bottom datum; no component or board shape has been substituted. Display groups partition all original faces using bounding-Z heuristics only; blue/dark/metal colors are approximate and do not establish material identity. Vendor drawings specify board-edge tolerance±0.3mm and drill-location±0.1mm. Connections/wires/soldered headers are not included in vendor STEP.",
        [path.name],shape=shape,face_count=len(shape.Faces),source_bounds_mm=[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax])
