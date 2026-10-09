"""Check dependencies; install only missing browser QA dependencies into a venv."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def browser_paths():
    found=[]
    for name in ('chromium','chromium-browser','google-chrome','chrome','msedge'):
        p=shutil.which(name)
        if p:found.append(p)
    for key in ('PROGRAMFILES','PROGRAMFILES(X86)','LOCALAPPDATA'):
        base=Path(os.environ.get(key,''))
        for rel in ('Google/Chrome/Application/chrome.exe','Microsoft/Edge/Application/msedge.exe'):
            if (base/rel).is_file():found.append(str(base/rel))
    for p in ('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'):
        if Path(p).is_file():found.append(p)
    caches=[Path.home()/'.cache/ms-playwright',Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'ms-playwright']
    for cache in caches:
        for glob in ('chromium-*/chrome-linux/chrome','chromium-*/chrome-linux64/chrome','chromium-*/chrome-win/chrome.exe','chromium-*/chrome-win64/chrome.exe','chromium-*/chrome-mac/Chromium.app/Contents/MacOS/Chromium'):
            found.extend(str(p) for p in cache.glob(glob))
    return list(dict.fromkeys(found))

def probe_python(py):
    cmd=[str(py),'-c','import importlib.util,json,sys; print(json.dumps({"version":list(sys.version_info[:3]),"playwright":bool(importlib.util.find_spec("playwright"))}))']
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
    if r.returncode:raise RuntimeError(r.stderr[-2000:])
    return json.loads(r.stdout)

def command(cmd,timeout=300):
    r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=timeout)
    if r.returncode:raise RuntimeError(r.stderr[-3000:] or r.stdout[-3000:])

def check(mode='html',install=False):
    if sys.version_info<(3,10):return {'status':'blocked','reason':'Python >= 3.10 required; install from python.org','python':sys.executable}
    gsap=ROOT/'assets/gsap.min.js'
    if not gsap.exists():return {'status':'blocked','reason':'Bundled GSAP missing; restore the skill package'}
    pin=ROOT/'assets/gsap.sha256'
    if pin.exists() and hashlib.sha256(gsap.read_bytes()).hexdigest()!=pin.read_text().strip():return {'status':'blocked','reason':'Bundled GSAP integrity mismatch'}
    envpy=ROOT/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    py=envpy if envpy.exists() else Path(sys.executable);info=probe_python(py)
    missing=[];installed=[];error=None
    # PowerPoint serializer itself has no third-party dependencies.
    if mode=='html' and not info['playwright']:missing.append('playwright')
    browsers=browser_paths()
    if mode=='html' and not browsers:missing.append('chromium')
    if install and missing:
        try:
            if not envpy.exists():command([sys.executable,'-m','venv',ROOT/'.venv']);py=envpy
            info=probe_python(py)
            if not info['playwright']:
                command([py,'-m','pip','install','--disable-pip-version-check','--index-url','https://pypi.org/simple','playwright']);installed.append('playwright')
            if not browsers:command([py,'-m','playwright','install','chromium'],600);installed.append('chromium')
            browsers=browser_paths();info=probe_python(py);missing=[]
            if not info['playwright']:missing.append('playwright')
            if not browsers:missing.append('chromium')
        except (OSError,RuntimeError,subprocess.TimeoutExpired) as e:error=str(e)
    status='ready' if not missing else 'partial'
    if error:status='blocked'
    return {'status':status,'mode':mode,'core_generation':'ready','python':str(py),'python_version':info['version'],'gsap':'bundled','playwright':info['playwright'],'browsers':browsers,'missing':missing,'installed':installed,'error':error,'note':'Executable presence is not proof that browser launch is permitted. Missing QA dependencies do not prevent core HTML/PPTX generation.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['html','pptx'],default='html');p.add_argument('--install',action='store_true');a=p.parse_args()
    result=check(a.mode,a.install);print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(2 if result['status']=='blocked' else 0)
