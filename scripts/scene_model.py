"""Shared, dependency-free scene contract and geometry."""
from __future__ import annotations
import json, math, re
from pathlib import Path

KINDS={'rect','circle','ellipse','text','line','path','polygon','polyline'}
DEFAULT={'x':0,'y':0,'scale':1,'scaleX':1,'scaleY':1,'rotation':0,'opacity':1}
COLOR=re.compile(r'^#[0-9a-fA-F]{6}$')
ID=re.compile(r'^[A-Za-z][A-Za-z0-9_-]*$')
NUM=re.compile(r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?')

def number(v,where):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):
        raise ValueError(f'{where}: finite number required')
    return v

def path_commands(d):
    tokens=re.findall(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',d)
    leftover=re.sub(r'[\s,]','',re.sub(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?','',d))
    if leftover:raise ValueError('Malformed path')
    counts={'M':2,'L':2,'H':1,'V':1,'C':6,'Q':4,'Z':0};out=[];i=0;cmd=None;x=y=0
    while i<len(tokens):
        if tokens[i].isalpha():cmd=tokens[i];i+=1
        if cmd not in counts:raise ValueError(f'Unsupported SVG path command: {cmd}. Use absolute M L H V C Q Z.')
        n=counts[cmd]
        if n==0:
            out.append(('Z',[]));cmd=None;continue
        values=tokens[i:i+n]
        if len(values)!=n or any(v.isalpha() for v in values):raise ValueError('Incomplete SVG path')
        vals=list(map(float,values));i+=n
        if any(not math.isfinite(v) for v in vals):raise ValueError('Path coordinates must be finite')
        if cmd=='H':x=vals[0];out.append(('L',[x,y]))
        elif cmd=='V':y=vals[0];out.append(('L',[x,y]))
        else:
            out.append((cmd,vals));x,y=vals[-2:]
        if cmd=='M':cmd='L'
    if not out or out[0][0]!='M':raise ValueError('Path must begin with M')
    return out

def pose(state,id):
    p={**DEFAULT,**state.get('objects',{}).get(id,{})}
    if id not in state.get('objects',{}):p['opacity']=0
    return p

def matrix(p):
    a=math.radians(p['rotation']);c=math.cos(a);s=math.sin(a)
    sx=p['scale']*p['scaleX'];sy=p['scale']*p['scaleY']
    return [c*sx,s*sx,-s*sy,c*sy,p['x'],p['y']]

def bounds(o,p):
    a,b,c,d,e,f=matrix(p)
    points=[(a*x+c*y+e,b*x+d*y+f) for x,y in [(0,0),(o['width'],0),(0,o['height']),(o['width'],o['height'])]]
    return min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points)

def validate(scene):
    if scene.get('version')!=1:raise ValueError('scene version must be 1')
    for k in ('width','height'):
        if number(scene.get(k),k)<=0:raise ValueError(f'{k} must be positive')
    if not isinstance(scene.get('title'),str):raise ValueError('title required')
    for k in ('background','ink','accent'):
        if not COLOR.fullmatch(scene.get('palette',{}).get(k,'')):raise ValueError(f'palette.{k}: six-digit hex color required')
    objs=scene.get('objects',[]);states=scene.get('states',[])
    if not objs or not states:raise ValueError('objects and states required')
    ids=set()
    for o in objs:
        id=o.get('id','')
        if not ID.fullmatch(id) or id in ids:raise ValueError(f'Invalid or duplicate object ID: {id}')
        ids.add(id)
        for k in ('width','height'):
            if number(o.get(k),f'{id}.{k}')<=0:raise ValueError('Object dimensions must be positive')
        if not o.get('children'):raise ValueError(f'{id}: children required')
        for j,ch in enumerate(o['children']):
            kind=ch.get('kind');where=f'{id}.children[{j}]'
            if kind not in KINDS:raise ValueError(f'{where}: unsupported kind {kind}')
            for k in ('fill','stroke'):
                v=ch.get(k,'none')
                if v!='none' and not COLOR.fullmatch(v):raise ValueError(f'{where}.{k}: invalid color')
            for k,v in ch.items():
                if k in {'x','y','w','h','rx','ry','r','cx','cy','x1','y1','x2','y2','fontSize','fontWeight','strokeWidth','opacity'}:number(v,f'{where}.{k}')
            required={'rect':('w','h'),'text':('w','h'),'circle':('cx','cy','r'),'ellipse':('cx','cy','rx','ry'),'line':('x1','y1','x2','y2')}.get(kind,())
            for k in required:
                if k not in ch:raise ValueError(f'{where}.{k} required')
            if kind in {'rect','text'}:
                for k in ('w','h'):
                    if ch.get(k,0)<=0:raise ValueError(f'{where}.{k} must be positive')
            if kind=='text':
                if not isinstance(ch.get('text'),str):raise ValueError(f'{where}: text string required')
                if ch.get('fontSize',28)<=0:raise ValueError('fontSize must be positive')
                if ch.get('align','center') not in {'left','center','right'}:raise ValueError('Invalid text alignment')
            if kind=='circle' and ch['r']<=0:raise ValueError('Circle radius must be positive')
            if kind=='ellipse' and min(ch['rx'],ch['ry'])<=0:raise ValueError('Ellipse radii must be positive')
            if ch.get('strokeWidth',1)<0:raise ValueError('strokeWidth cannot be negative')
            if kind=='path':path_commands(ch.get('d',''))
            if kind in {'polygon','polyline'}:
                if len(ch.get('points',[]))<2:raise ValueError(f'{where}: points required')
                for xy in ch['points']:
                    if len(xy)!=2:raise ValueError('points must be [x,y]')
                    for v in xy:number(v,where)
            if not 0<=ch.get('opacity',1)<=1:raise ValueError('child opacity outside 0..1')
    state_ids=set();warnings=[]
    for si,s in enumerate(states):
        if not ID.fullmatch(s.get('id','')) or s['id'] in state_ids:raise ValueError('State IDs must be valid and unique')
        state_ids.add(s['id'])
        if not s.get('title'):raise ValueError('State title required')
        dur=number(s.get('duration',.8),'duration')
        if not .1<=dur<=10:raise ValueError('duration must be between 0.1 and 10 seconds')
        if not set(s.get('objects',{}))<=ids:raise ValueError('State references unknown object')
        for o in objs:
            p=pose(s,o['id'])
            for k,v in p.items():
                if k not in DEFAULT:raise ValueError(f'Unknown pose property: {k}')
                number(v,f'{s["id"]}.{o["id"]}.{k}')
            if not 0<=p['opacity']<=1 or min(p['scale'],p['scaleX'],p['scaleY'])<=0:raise ValueError('Invalid opacity or scale')
            if p['opacity']>.01:
                x1,y1,x2,y2=bounds(o,p)
                if x1<0 or y1<0 or x2>scene['width'] or y2>scene['height']:warnings.append(f'{s["id"]}/{o["id"]}: outside canvas')
    return warnings

def load(path):
    p=Path(path);raw=p.read_text(encoding='utf-8-sig')
    if p.suffix.lower()=='.json':scene=json.loads(raw)
    else:
        m=re.search(r'<script\b[^>]*\bid=["\']explainer-data["\'][^>]*>(.*?)</script>',raw,re.S|re.I)
        if not m:raise ValueError('HTML has no explainer-data. Adapt this HTML to the scene contract first.')
        scene=json.loads(m.group(1))
    validate(scene);return scene
