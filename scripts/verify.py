"""Static validation plus optional real-browser interaction and geometry QA."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from scene_model import load,validate,pose,matrix
from doctor import browser_paths

def verify(path,out,static_only=False):
    scene=load(path);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    raw=Path(path).read_text(encoding='utf-8');result={'static':'passed','warnings':validate(scene),'states':len(scene['states']),'browser':'not_run'}
    for token in ('id="explainer-data"','window.explainer','matrix(','gsap.timeline','paused:true'):
        if token not in raw:raise ValueError(f'Missing HTML player contract: {token}')
    if static_only:
        result['browser']='skipped_explicitly'
    else:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                options={'headless':True}
                browsers=browser_paths()
                if browsers:options['executable_path']=browsers[0]
                browser=p.chromium.launch(**options)
                page=browser.new_page(viewport={'width':1600,'height':1120});errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(Path(path).resolve().as_uri());page.wait_for_function('window.explainer!==undefined')
                page.wait_for_timeout(1200)
                assert page.evaluate('explainer.getState().index')==0,'autoplay'
                if len(scene['states'])>1:
                    page.locator('#next').click();page.wait_for_function('!explainer.getState().busy')
                    page.wait_for_timeout(1000);assert page.evaluate('explainer.getState().index')==1,'auto-advance'
                    page.keyboard.press('ArrowLeft');page.wait_for_function('!explainer.getState().busy');assert page.evaluate('explainer.getState().index')==0
                    page.evaluate('explainer.next();explainer.next();explainer.next()');page.wait_for_function('!explainer.getState().busy');assert page.evaluate('explainer.getState().index')==1,'rapid click skip'
                for i,state in enumerate(scene['states']):
                    page.evaluate('(i)=>explainer.goTo(i,false)',i)
                    attrs=page.evaluate('()=>Object.fromEntries(Array.from(document.querySelectorAll("[data-object]")).map(g=>[g.dataset.object,{matrix:g.getAttribute("transform"),opacity:Number(g.getAttribute("opacity"))}]))')
                    for obj in scene['objects']:
                        wanted=pose(state,obj['id']);actual=attrs[obj['id']]
                        got=list(map(float,actual['matrix'][7:-1].split()))
                        assert all(abs(a-b)<1e-6 for a,b in zip(got,matrix(wanted))),f'offset {i}/{obj["id"]}'
                        assert abs(actual['opacity']-wanted['opacity'])<1e-7
                    page.locator('#view').screenshot(path=str(out/f'state-{i:02}.png'))
                page.locator('#reset').click();assert page.evaluate('explainer.getState().index')==0
                page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'mobile overflow'
                assert not errors,errors
                browser.close();result['browser']='passed';result['checks']=['no_autoplay','click_hold','previous','rapid_click_guard','all_matrices','reset','mobile_width','no_js_errors']
        except (ImportError,OSError) as e:result.update(browser='blocked',reason=str(e))
        except Exception as e:
            # Browser launch permission/dependency failures are distinct from assertions.
            if isinstance(e,AssertionError):result.update(browser='failed',reason=str(e))
            else:result.update(browser='blocked',reason=str(e))
    (out/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('html');p.add_argument('--out',default='qa');p.add_argument('--static-only',action='store_true');a=p.parse_args();r=verify(a.html,a.out,a.static_only);print(json.dumps(r,ensure_ascii=False,indent=2));sys.exit(1 if r['browser']=='failed' else 2 if r['browser']=='blocked' else 0)
