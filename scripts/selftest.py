"""Exercise build/export contracts, reset geometry, rejection, and installation."""
from pathlib import Path
import argparse,copy,json,math,uuid,zipfile
import xml.etree.ElementTree as ET
from scene_model import validate,load,pose,matrix,path_commands
from build_html import build
from export_pptx import export,NS,q
from install_skill import install

def sample():
    card=lambda id,label:{'id':id,'width':180,'height':90,'children':[
        {'kind':'rect','x':0,'y':0,'w':180,'h':90,'rx':14,'fill':'#DDECEF','stroke':'#167D8D','strokeWidth':2},
        {'kind':'text','x':8,'y':8,'w':164,'h':74,'text':label,'fontSize':36,'fontWeight':700,'fill':'#167D8D','align':'center'}]}
    return {'version':1,'title':'点击式动画链路验证','width':1600,'height':900,'font':'Microsoft YaHei','palette':{'background':'#F5F2EA','ink':'#253D3F','accent':'#167D8D'},
    'objects':[card('token-a','今天'),card('token-b','很好'),
        {'id':'arrow','width':300,'height':40,'children':[{'kind':'line','x1':8,'y1':20,'x2':282,'y2':20,'stroke':'#167D8D','strokeWidth':3,'arrowEnd':True}]},
        {'id':'curve','width':300,'height':100,'children':[{'kind':'path','d':'M 10 90 Q 120 5 280 60','stroke':'#B96523','strokeWidth':3,'fill':'none'}]},
        {'id':'dot','width':80,'height':80,'children':[{'kind':'circle','cx':40,'cy':40,'r':30,'fill':'#B96523'}]}],
    'states':[
        {'id':'start','chapter':'连续变化','title':'从同一组对象开始','narration':'点击以后，文字卡片移动到新的位置。','objects':{'token-a':{'x':300,'y':300},'token-b':{'x':1000,'y':300},'arrow':{'x':590,'y':325}}},
        {'id':'move','chapter':'连续变化','title':'移动、缩放和旋转','narration':'对象保持身份，几何状态改变。','objects':{'token-a':{'x':550,'y':350,'scale':1.2,'rotation':25},'token-b':{'x':850,'y':430,'scaleX':.8,'scaleY':1.15,'rotation':-15},'arrow':{'x':670,'y':600,'scaleX':.65},'curve':{'x':350,'y':550},'dot':{'x':1150,'y':460}}},
        {'id':'reset-scale','chapter':'重组','title':'回到完整缩放的重组状态','narration':'所有缩放和旋转都精确恢复。','objects':{'token-a':{'x':570,'y':380},'token-b':{'x':850,'y':380},'arrow':{'x':580,'y':600},'curve':{'x':1050,'y':570}}}]}

def main(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);s=sample();assert not validate(s)
    source=out/'scene.json';source.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
    html=out/'explainer.html';ppt=out/'explainer.pptx';build(source,html);r=export(html,ppt);assert r['slides']==3
    assert load(html)==s
    for broken in ('unknown','nan','command'):
        bad=copy.deepcopy(s)
        if broken=='unknown':bad['states'][0]['objects']['missing']={'x':0,'y':0}
        elif broken=='nan':bad['states'][0]['objects']['token-a']['x']=float('nan')
        else:bad['objects'][3]['children'][0]['d']='M0 0 A50 50 0 0 0 80 80'
        try:validate(bad)
        except ValueError:pass
        else:raise AssertionError('Invalid scene accepted: '+broken)
    evil=copy.deepcopy(s);evil['states'][0]['title']='</script><script>alert(1)</script>'
    f=out/'escape.json';f.write_text(json.dumps(evil),encoding='utf-8');build(f,out/'escape.html');assert load(out/'escape.html')==evil
    assert '<script>alert(1)</script>' not in (out/'escape.html').read_text(encoding='utf-8')
    unit=12192000/s['width'];byid={o['id']:o for o in s['objects']};checked=0
    with zipfile.ZipFile(ppt) as z:
        types=ET.fromstring(z.read('[Content_Types].xml'))
        assert all(not e.attrib.get('ContentType','').endswith('.xml') for e in types)
        for i,state in enumerate(s['states'],1):
            slide=ET.fromstring(z.read(f'ppt/slides/slide{i}.xml'))
            for group in slide.findall('.//'+q('p','grpSp')):
                name=group.find(q('p','nvGrpSpPr')).find(q('p','cNvPr')).get('name')[2:];o=byid[name];p=pose(state,name)
                xf=group.find(q('p','grpSpPr')).find(q('a','xfrm'));off=xf.find(q('a','off'));ext=xf.find(q('a','ext'));w,h=int(ext.get('cx')),int(ext.get('cy'));x,y=int(off.get('x')),int(off.get('y'));a=int(xf.get('rot',0))/60000*math.pi/180
                m=matrix(p)
                for px,py in [(0,0),(o['width'],0),(0,o['height']),(o['width'],o['height'])]:
                    dx=px/o['width']*w-w/2;dy=py/o['height']*h-h/2
                    got=(x+w/2+dx*math.cos(a)-dy*math.sin(a),y+h/2+dx*math.sin(a)+dy*math.cos(a))
                    want=((m[0]*px+m[2]*py+m[4])*unit,(m[1]*px+m[3]*py+m[5])*unit)
                    assert max(abs(got[j]-want[j]) for j in (0,1))<3,(name,got,want);checked+=1
            if i>1:
                assert slide.find('.//'+q('p159','morph')) is not None
                assert all(t.get('advTm') is None and t.get('advClick')=='1' for t in slide.iter(q('p','transition')))
    tmp=out/('install-test-'+uuid.uuid4().hex);tmp.mkdir()
    installed=install(tmp);assert Path(installed['path'],'SKILL.md').is_file()
    assert not Path(installed['path'],'.git').exists()
    try:install(tmp)
    except FileExistsError:pass
    else:raise AssertionError('Installer overwrote existing skill')
    report={'status':'passed','native_geometry_corners_checked':checked,'checks':['scene_contract','html_roundtrip','json_script_escape','invalid_input_rejection','editable_native_objects','shared_names','rotation_origin_equivalence','native_morph','click_only','installer_no_overwrite'],'sample_html':str(html.resolve()),'sample_pptx':str(ppt.resolve()),'browser_or_powerpoint_playback':'not_tested'}
    (out/'selftest-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);main(p.parse_args().out)
