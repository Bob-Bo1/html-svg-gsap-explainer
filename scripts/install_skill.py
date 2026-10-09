"""Install only this skill into the current user's Codex skills directory."""
from pathlib import Path
import argparse,json,os,shutil,uuid
NAME='html-svg-gsap-explainer'

def install(destination=None):
    source=Path(__file__).resolve().parents[1]
    base=Path(destination) if destination else Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'skills'
    target=base/NAME
    if target.resolve()==source:return {'status':'already_installed','path':str(target)}
    if target.exists():raise FileExistsError(f'{target} already exists. No files changed; choose a different destination or explicitly request an update.')
    base.mkdir(parents=True,exist_ok=True)
    staging=base/(NAME+'-install-'+uuid.uuid4().hex)
    # Inherit the directory ACL on Windows rather than creating a 0700 temp
    # directory that can become unreadable under restricted execution tokens.
    staging.mkdir()
    try:
        for name in ('SKILL.md','agents','scripts','references','assets'):
            src=source/name;dst=staging/name
            if src.is_dir():shutil.copytree(src,dst,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            else:shutil.copy2(src,dst)
        if not (staging/'SKILL.md').is_file() or not (staging/'assets/gsap.min.js').is_file():raise ValueError('Incomplete skill package')
        staging.rename(target)
    except Exception:
        # Only the verified task-owned staging directory can be removed.
        if staging.parent.resolve()!=base.resolve() or not staging.name.startswith(NAME+'-install-'):raise
        shutil.rmtree(staging);raise
    return {'status':'installed','path':str(target.resolve()),'invoke':'$'+NAME,'note':'Restart Codex or open a new conversation to refresh skill discovery.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--destination');a=p.parse_args();print(json.dumps(install(a.destination),ensure_ascii=False,indent=2))
