from pathlib import Path
import argparse,hashlib,html,json
from scene_model import load,validate

def build(source,out):
    scene=load(source);root=Path(__file__).resolve().parents[1]
    player=(root/'assets/player.html').read_text(encoding='utf-8')
    gsap=(root/'assets/gsap.min.js').read_text(encoding='utf-8')
    # JSON is data, never executable markup; protect script terminators.
    data=json.dumps(scene,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    result=player.replace('__TITLE__',html.escape(scene['title'])).replace('/*__GSAP__*/',gsap.replace('</script','<\\/script')).replace('__SCENE_JSON__',data)
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(result,encoding='utf-8')
    return {'html':str(out.resolve()),'states':len(scene['states']),'objects':len(scene['objects']),'warnings':validate(scene),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('scene');p.add_argument('--out',required=True);a=p.parse_args()
    print(json.dumps(build(a.scene,a.out),ensure_ascii=False,indent=2))
