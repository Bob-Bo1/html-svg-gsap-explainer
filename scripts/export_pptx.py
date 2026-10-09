"""Scene-backed HTML to editable vector PPTX with native click-only Morph.

Uses standard-library OOXML serialization. Does not rasterize whole slides,
execute HTML, control Office, or infer states from arbitrary webpages.
"""
from __future__ import annotations
import argparse,json,math,posixpath,zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
from scene_model import load,pose,path_commands,validate

NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'rel':'http://schemas.openxmlformats.org/package/2006/relationships',
    'ct':'http://schemas.openxmlformats.org/package/2006/content-types',
    'mc':'http://schemas.openxmlformats.org/markup-compatibility/2006',
    'p14':'http://schemas.microsoft.com/office/powerpoint/2010/main',
    'p159':'http://schemas.microsoft.com/office/powerpoint/2015/09/main'}
for k in ('p','a','r','mc','p14','p159'):ET.register_namespace(k,NS[k])
def q(prefix,local):return '{'+NS[prefix]+'}'+local
def node(tag,attrs=None,parent=None,text=None):
    prefix,local=tag.split(':');e=ET.Element(q(prefix,local),{k:str(v) for k,v in (attrs or {}).items()})
    if text is not None:e.text=str(text)
    if parent is not None:parent.append(e)
    return e
def xml(e):return ET.tostring(e,encoding='utf-8',xml_declaration=True)
def color(parent,value,opacity=1):
    if value=='none':node('a:noFill',parent=parent);return
    fill=node('a:solidFill',parent=parent);c=node('a:srgbClr',{'val':value.lstrip('#').upper()},fill)
    if opacity<.999999:node('a:alpha',{'val':max(0,round(opacity*100000))},c)
def paint(sp,c,opacity,unit):
    color(sp,c.get('fill','none'),opacity)
    ln=node('a:ln',{'w':max(1,round(c.get('strokeWidth',1)*unit)),'cap':'rnd'},sp)
    color(ln,c.get('stroke','none'),opacity);node('a:round',parent=ln)
    if c.get('arrowEnd'):node('a:tailEnd',{'type':'triangle','w':'med','len':'med'},ln)
def xfrm(parent,x,y,w,h,unit):
    xf=node('a:xfrm',parent=parent);node('a:off',{'x':round(x*unit),'y':round(y*unit)},xf);node('a:ext',{'cx':max(1,round(w*unit)),'cy':max(1,round(h*unit))},xf);return xf
def nonvisual(parent,id,name):
    nv=node('p:nvSpPr',parent=parent);node('p:cNvPr',{'id':id,'name':name},nv);node('p:cNvSpPr',parent=nv);node('p:nvPr',parent=nv)
def tree():
    sp=node('p:spTree');nv=node('p:nvGrpSpPr',parent=sp);node('p:cNvPr',{'id':1,'name':''},nv);node('p:cNvGrpSpPr',parent=nv);node('p:nvPr',parent=nv)
    grp=node('p:grpSpPr',parent=sp);xf=node('a:xfrm',parent=grp)
    for tag,attrs in [('off',{'x':0,'y':0}),('ext',{'cx':0,'cy':0}),('chOff',{'x':0,'y':0}),('chExt',{'cx':0,'cy':0})]:node('a:'+tag,attrs,xf)
    return sp

def text_shape(parent,id,name,c,unit,font,opacity=1):
    sp=node('p:sp',parent=parent);nonvisual(sp,id,name);props=node('p:spPr',parent=sp)
    xfrm(props,c.get('x',0),c.get('y',0),c['w'],c['h'],unit)
    geom=node('a:prstGeom',{'prst':'rect'},props);node('a:avLst',parent=geom);node('a:noFill',parent=props);ln=node('a:ln',parent=props);node('a:noFill',parent=ln)
    tx=node('p:txBody',parent=sp);node('a:bodyPr',{'wrap':'none','anchor':'ctr','lIns':0,'rIns':0,'tIns':0,'bIns':0},tx);node('a:lstStyle',parent=tx)
    for line in c['text'].split('\n'):
        p=node('a:p',parent=tx);pp=node('a:pPr',{'algn':{'left':'l','right':'r','center':'ctr'}.get(c.get('align','center'),'ctr')},p)
        ls=node('a:lnSpc',parent=pp);node('a:spcPct',{'val':130000},ls)
        run=node('a:r',parent=p);rp=node('a:rPr',{'lang':'zh-CN','sz':max(100,round(c.get('fontSize',28)*unit/914400*7200)),'b':int(c.get('fontWeight',400)>=700)},run)
        color(rp,c.get('fill','#253D3F'),opacity)
        node('a:latin',{'typeface':font},rp);node('a:ea',{'typeface':font},rp);node('a:cs',{'typeface':font},rp)
        node('a:t',parent=run,text=line);node('a:endParaRPr',{'lang':'zh-CN'},p)
    return sp

def path_geometry(props,commands,w,h,unit,fill):
    geom=node('a:custGeom',parent=props)
    for k in ('avLst','gdLst','ahLst','cxnLst'):node('a:'+k,parent=geom)
    node('a:rect',{'l':'l','t':'t','r':'r','b':'b'},geom)
    paths=node('a:pathLst',parent=geom);path=node('a:path',{'w':max(1,round(w*unit)),'h':max(1,round(h*unit)),'fill':'norm' if fill!='none' else 'none','stroke':'1'},paths)
    tags={'M':'moveTo','L':'lnTo','C':'cubicBezTo','Q':'quadBezTo','Z':'close'}
    for cmd,vals in commands:
        item=node('a:'+tags[cmd],parent=path)
        for i in range(0,len(vals),2):node('a:pt',{'x':round(vals[i]*unit),'y':round(vals[i+1]*unit)},item)

def primitive(parent,id,name,c,object,unit,font,opacity):
    kind=c['kind'];opacity*=c.get('opacity',1)
    if kind=='text':return text_shape(parent,id,name,c,unit,font,opacity)
    sp=node('p:sp',parent=parent);nonvisual(sp,id,name);props=node('p:spPr',parent=sp)
    if kind=='rect':
        x,y,w,h=c.get('x',0),c.get('y',0),c['w'],c['h'];shape='roundRect' if c.get('rx',0) else 'rect'
    elif kind=='circle':x,y,w,h=c['cx']-c['r'],c['cy']-c['r'],c['r']*2,c['r']*2;shape='ellipse'
    elif kind=='ellipse':x,y,w,h=c['cx']-c['rx'],c['cy']-c['ry'],c['rx']*2,c['ry']*2;shape='ellipse'
    else:x,y,w,h=0,0,object['width'],object['height'];shape=None
    xfrm(props,x,y,w,h,unit)
    if shape:
        geom=node('a:prstGeom',{'prst':shape},props);av=node('a:avLst',parent=geom)
        if shape=='roundRect':node('a:gd',{'name':'adj','fmla':'val '+str(min(50000,round(c['rx']/min(w,h)*100000)))},av)
    else:
        if kind=='path':commands=path_commands(c['d'])
        elif kind=='line':commands=[('M',[c['x1'],c['y1']]),('L',[c['x2'],c['y2']])]
        elif kind in {'polygon','polyline'}:
            commands=[('M',c['points'][0])]+[('L',p) for p in c['points'][1:]]
            if kind=='polygon':commands.append(('Z',[]))
        else:raise ValueError('Unsupported PowerPoint element '+kind)
        path_geometry(props,commands,w,h,unit,c.get('fill','none'))
    paint(props,c,opacity,unit);return sp

def group(parent,o,p,start_id,unit,font):
    g=node('p:grpSp',parent=parent);nv=node('p:nvGrpSpPr',parent=g);node('p:cNvPr',{'id':start_id,'name':'!!'+o['id']},nv);node('p:cNvGrpSpPr',parent=nv);node('p:nvPr',parent=nv)
    sp=node('p:grpSpPr',parent=g);w=o['width']*p['scale']*p['scaleX'];h=o['height']*p['scale']*p['scaleY'];a=math.radians(p['rotation']);cs,sn=math.cos(a),math.sin(a)
    # PowerPoint rotates around the center. Offset its box so the resulting
    # top-left-origin transform is identical to the SVG matrix.
    x=p['x']+(w*cs-h*sn-w)/2;y=p['y']+(w*sn+h*cs-h)/2
    xf=node('a:xfrm',{'rot':round((p['rotation']%360)*60000)},sp)
    node('a:off',{'x':round(x*unit),'y':round(y*unit)},xf);node('a:ext',{'cx':max(1,round(w*unit)),'cy':max(1,round(h*unit))},xf)
    node('a:chOff',{'x':0,'y':0},xf);node('a:chExt',{'cx':max(1,round(o['width']*unit)),'cy':max(1,round(o['height']*unit))},xf)
    for j,c in enumerate(o['children']):primitive(g,start_id+j+1,o['id']+'-part-'+str(j),c,o,unit,font,p['opacity'])
    return start_id+len(o['children'])+1

def morph(slide,duration):
    ac=node('mc:AlternateContent',parent=slide);choice=node('mc:Choice',{'Requires':'p159'},ac)
    attrs={'spd':'slow','advClick':'1',q('p14','dur'):round(duration*1000)}
    tr=node('p:transition',attrs,choice);node('p159:morph',{'option':'byObject'},tr)
    fb=node('mc:Fallback',parent=ac);tr=node('p:transition',attrs,fb);node('p:fade',parent=tr)

def relationships(items):
    root=ET.Element(q('rel','Relationships'))
    for id,type,target in items:ET.SubElement(root,q('rel','Relationship'),{'Id':id,'Type':NS['r']+'/'+type,'Target':target})
    return xml(root)

def theme(font):
    root=node('a:theme',{'name':'Explainer'});elems=node('a:themeElements',parent=root);colors=node('a:clrScheme',{'name':'Explainer'},elems)
    for name,hex in [('dk1','253D3F'),('lt1','F5F2EA'),('dk2','657475'),('lt2','FFFDF8'),('accent1','167D8D'),('accent2','B96523'),('accent3','4A7462'),('accent4','7D6D91'),('accent5','697D9A'),('accent6','967B51'),('hlink','167D8D'),('folHlink','7D6D91')]:node('a:srgbClr',{'val':hex},node('a:'+name,parent=colors))
    fonts=node('a:fontScheme',{'name':'Explainer'},elems)
    for name in ('majorFont','minorFont'):
        f=node('a:'+name,parent=fonts)
        for tag in ('latin','ea','cs'):node('a:'+tag,{'typeface':font},f)
    fmt=node('a:fmtScheme',{'name':'Explainer'},elems)
    for tag in ('fillStyleLst','bgFillStyleLst'):
        lst=node('a:'+tag,parent=fmt)
        for _ in range(3):node('a:schemeClr',{'val':'phClr'},node('a:solidFill',parent=lst))
    # Required ordering: fill, line, effect, background.
    bg=fmt.find(q('a','bgFillStyleLst'));fmt.remove(bg)
    lines=node('a:lnStyleLst',parent=fmt)
    for w in (9525,19050,28575):
        ln=node('a:ln',{'w':w},lines);node('a:schemeClr',{'val':'phClr'},node('a:solidFill',parent=ln));node('a:prstDash',{'val':'solid'},ln)
    effects=node('a:effectStyleLst',parent=fmt)
    for _ in range(3):node('a:effectLst',parent=node('a:effectStyle',parent=effects))
    fmt.append(bg);return xml(root)

def export(source,out):
    scene=load(source);unit=12192000/scene['width'];slidew=12192000;slideh=round(scene['height']*unit);font=scene.get('font','Microsoft YaHei');parts={}
    pres=node('p:presentation');masters=node('p:sldMasterIdLst',parent=pres);node('p:sldMasterId',{'id':2147483648,q('r','id'):'rId1'},masters);slides=node('p:sldIdLst',parent=pres)
    relations=[('rId1','slideMaster','slideMasters/slideMaster1.xml')]
    for i,state in enumerate(scene['states'],1):
        node('p:sldId',{'id':255+i,q('r','id'):f'rId{i+1}'},slides);relations.append((f'rId{i+1}','slide',f'slides/slide{i}.xml'))
        slide=node('p:sld');cs=node('p:cSld',{'name':state['title']},slide);bg=node('p:bg',parent=cs);bgp=node('p:bgPr',parent=bg);color(bgp,scene['palette']['background']);node('a:effectLst',parent=bgp);sp=tree();cs.append(sp);id=2
        meta=[('meta-chapter',65,35,scene['width']-130,34,state.get('chapter',''),18,400),('meta-title',65,70,scene['width']-130,60,state['title'],36,700),('meta-note',65,scene['height']-112,scene['width']-130,40,state.get('note',''),19,400)]
        for name,x,y,w,h,txt,size,weight in meta:
            text_shape(sp,id,'!!_ui-'+name,{'x':x,'y':y,'w':w,'h':h,'text':txt,'fontSize':size,'fontWeight':weight,'fill':scene['palette']['ink'],'align':'left'},unit,font);id+=1
        for o in scene['objects']:
            p=pose(state,o['id'])
            if p['opacity']>.001:id=group(sp,o,p,id,unit,font)
        clr=node('p:clrMapOvr',parent=slide);node('a:masterClrMapping',parent=clr)
        if i>1:morph(slide,state.get('duration',.8))
        parts[f'ppt/slides/slide{i}.xml']=xml(slide);parts[f'ppt/slides/_rels/slide{i}.xml.rels']=relationships([('rId1','slideLayout','../slideLayouts/slideLayout1.xml')])
    node('p:sldSz',{'cx':slidew,'cy':slideh,'type':'custom'},pres);node('p:notesSz',{'cx':6858000,'cy':9144000},pres)
    parts['ppt/presentation.xml']=xml(pres);parts['ppt/_rels/presentation.xml.rels']=relationships(relations)
    master=node('p:sldMaster');cs=node('p:cSld',parent=master);cs.append(tree())
    node('p:clrMap',{'bg1':'lt1','tx1':'dk1','bg2':'lt2','tx2':'dk2',**{f'accent{i}':f'accent{i}' for i in range(1,7)},'hlink':'hlink','folHlink':'folHlink'},master)
    lst=node('p:sldLayoutIdLst',parent=master);node('p:sldLayoutId',{'id':2147483649,q('r','id'):'rId1'},lst);styles=node('p:txStyles',parent=master)
    for name in ('titleStyle','bodyStyle','otherStyle'):node('p:'+name,parent=styles)
    parts['ppt/slideMasters/slideMaster1.xml']=xml(master);parts['ppt/slideMasters/_rels/slideMaster1.xml.rels']=relationships([('rId1','slideLayout','../slideLayouts/slideLayout1.xml'),('rId2','theme','../theme/theme1.xml')])
    layout=node('p:sldLayout',{'type':'blank','preserve':'1'});cs=node('p:cSld',{'name':'Blank'},layout);cs.append(tree());node('a:masterClrMapping',parent=node('p:clrMapOvr',parent=layout))
    parts['ppt/slideLayouts/slideLayout1.xml']=xml(layout);parts['ppt/slideLayouts/_rels/slideLayout1.xml.rels']=relationships([('rId1','slideMaster','../slideMasters/slideMaster1.xml')]);parts['ppt/theme/theme1.xml']=theme(font)
    parts['_rels/.rels']=relationships([('rId1','officeDocument','ppt/presentation.xml')])
    types=ET.Element(q('ct','Types'));ET.SubElement(types,q('ct','Default'),{'Extension':'rels','ContentType':'application/vnd.openxmlformats-package.relationships+xml'});ET.SubElement(types,q('ct','Default'),{'Extension':'xml','ContentType':'application/xml'})
    mime={'presentation':'presentation','slideMaster':'slideMaster','slideLayout':'slideLayout','slide':'slide'}
    for name in parts:
        if name.endswith('.rels'):continue
        if name.startswith('ppt/theme/'):ctype='application/vnd.openxmlformats-officedocument.theme+xml'
        else:
            kind='slideMaster' if '/slideMasters/' in name else 'slideLayout' if '/slideLayouts/' in name else 'slide' if '/slides/' in name else 'presentation'
            ctype='application/vnd.openxmlformats-officedocument.presentationml.'+kind+'+xml'
            if kind=='presentation':ctype='application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml'
        ET.SubElement(types,q('ct','Override'),{'PartName':'/'+name,'ContentType':ctype})
    parts['[Content_Types].xml']=xml(types)
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name,blob in parts.items():z.writestr(name,blob)
    result=inspect(out);result.update({'pptx':str(out.resolve()),'warnings':validate(scene),'browser_or_powerpoint_playback':'not_tested'});return result

def inspect(path):
    with zipfile.ZipFile(path) as z:
        names=set(z.namelist())
        for name in names:
            if name.endswith(('.xml','.rels')):ET.fromstring(z.read(name))
            if name.endswith('.rels'):
                base='' if name=='_rels/.rels' else posixpath.dirname(posixpath.dirname(name))
                for rel in ET.fromstring(z.read(name)):
                    dest=posixpath.normpath(posixpath.join(base,rel.attrib['Target']))
                    if dest not in names:raise ValueError(f'Broken relationship: {dest}')
        slides=sorted(n for n in names if n.startswith('ppt/slides/slide') and n.endswith('.xml'));groups=0
        for name in slides:
            s=ET.fromstring(z.read(name));ids=[e.attrib['id'] for e in s.iter(q('p','cNvPr'))]
            if len(ids)!=len(set(ids)):raise ValueError('Duplicate shape IDs')
            stable=[e.attrib['name'] for e in s.iter(q('p','cNvPr')) if e.attrib['name'].startswith('!!')]
            if len(stable)!=len(set(stable)):raise ValueError('Duplicate Morph names')
            if s.find('.//'+q('p','pic')) is not None:raise ValueError('Unexpected flattened picture')
            groups+=len(s.findall('.//'+q('p','grpSp')))
            if name!='ppt/slides/slide1.xml':
                if s.find('.//'+q('p159','morph')) is None:raise ValueError('Missing native Morph')
                for tr in s.iter(q('p','transition')):
                    if tr.get('advClick')!='1' or tr.get('advTm') is not None:raise ValueError('Invalid slide advance')
    return {'structure':'passed','slides':len(slides),'object_groups':groups,'native_morph':True,'automatic_advance':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--out',required=True);a=p.parse_args();print(json.dumps(export(a.source,a.out),ensure_ascii=False,indent=2))
