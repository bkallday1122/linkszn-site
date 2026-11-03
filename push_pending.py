#!/usr/bin/env python3
"""Debounced pusher for linkszn-site. Pushes all local unpushed commits on main together,
at most once every MIN_GAP seconds, so a burst of publishes triggers one Cloudflare build.
Safe under concurrency: one pusher at a time (flock); the repo publish lock is held while
rebasing/pushing; never discards commits; retries rejected pushes after pull --rebase.
Usage: push_pending.py [--now]   (normally spawned detached by publish_deal.py)"""
import fcntl, json, os, subprocess, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent
MIN_GAP = int(os.environ.get('LINKSZN_PUSH_GAP', '45'))
def git(*a, check=True):
    return subprocess.run(('git',)+a, cwd=ROOT, check=check, text=True, capture_output=True)
GITDIR = Path(git('rev-parse', '--absolute-git-dir').stdout.strip())
STAMP = GITDIR/'linkszn-last-push'; LOG = GITDIR/'linkszn-push.log'
def log(m):
    with LOG.open('a') as f: f.write(time.strftime('%Y-%m-%d %H:%M:%S ')+m+'\n')
def ahead():
    git('fetch', '-q', 'origin', 'main', check=False)
    r = git('rev-list', '--count', 'origin/main..main', check=False)
    return int(r.stdout.strip() or 0)
def resolve_shortlinks():
    """Union-merge shortlinks.json during a rebase conflict; abort on any other conflict."""
    files = git('diff', '--name-only', '--diff-filter=U', check=False).stdout.split()
    if files != ['shortlinks.json']: return False
    m = {}
    for stage in (':2:shortlinks.json', ':3:shortlinks.json'):
        m.update(json.loads(git('show', stage).stdout))
    (ROOT/'shortlinks.json').write_text(json.dumps(dict(sorted(m.items())), indent=1)+'\n')
    git('add', 'shortlinks.json')
    return True
def rebase():
    r = git('pull', '--rebase', 'origin', 'main', check=False)
    for _ in range(50):
        if r.returncode == 0: return True
        if not resolve_shortlinks():
            git('rebase', '--abort', check=False); log('rebase conflict, aborted: '+r.stdout[-300:]+r.stderr[-300:]); return False
        r = subprocess.run(['git', '-c', 'core.editor=true', 'rebase', '--continue'], cwd=ROOT, text=True, capture_output=True)
    git('rebase', '--abort', check=False); return False
def push_once(publock):
    with publock.open('w') as pl:
        fcntl.flock(pl, fcntl.LOCK_EX)
        n = ahead()
        if n == 0: return 0
        for attempt in range(5):
            if not rebase(): time.sleep(5); continue
            r = git('push', 'origin', 'main', check=False)
            if r.returncode == 0:
                STAMP.write_text(str(time.time())); log(f'pushed {n} commit(s) {git("rev-parse","HEAD").stdout.strip()[:7]}'); return n
            log(f'push rejected (attempt {attempt+1}): {r.stderr.strip()[-200:]}'); time.sleep(3)
        log('push failed after retries; commits kept locally'); return -1
def main():
    now = '--now' in sys.argv
    with (GITDIR/'linkszn-pusher.lock').open('w') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)   # waiters run after the active pusher; never skip
        while True:
            if ahead() == 0: return
            if not now:
                last = float(STAMP.read_text()) if STAMP.exists() else 0
                wait = MIN_GAP - (time.time()-last)
                if wait > 0: time.sleep(wait)
            now = False
            if push_once(GITDIR/'linkszn-publish.lock') < 0: time.sleep(15)
if __name__ == '__main__': main()
