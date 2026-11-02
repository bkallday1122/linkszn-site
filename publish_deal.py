#!/usr/bin/env python3
"""Validate a verified deal, commit its JSON file plus the short-link map, and push main."""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
SHORT_ALPHA='abcdefghjkmnpqrstuvwxyz23456789'

def short_code(slug, mapping):
    """Stable 5-char code for a slug; existing codes never change."""
    if slug in mapping: return mapping[slug]
    used=set(mapping.values()); n=0
    while True:
        h=int(hashlib.sha256(f'{slug}:{n}'.encode()).hexdigest(),16); c=''
        for _ in range(5): h,r=divmod(h,len(SHORT_ALPHA)); c+=SHORT_ALPHA[r]
        if c not in used: return c
        n+=1

def load_short(root=None):
    f=(root or ROOT)/'shortlinks.json'
    return json.loads(f.read_text()) if f.exists() else {}

def save_short(mapping, root=None):
    f=(root or ROOT)/'shortlinks.json'; t=f.with_suffix('.json.tmp')
    t.write_text(json.dumps(dict(sorted(mapping.items())),indent=1)+'\n'); t.replace(f)

def run(*args, capture=True):
    return subprocess.run(args, cwd=ROOT, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout

def timestamp(value):
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamps must include a timezone')
    return parsed

def url(value, woot=False):
    p = urlparse(value)
    if p.scheme != 'https' or not p.hostname or p.username or p.password:
        raise ValueError('URLs must be HTTPS and contain no credentials')
    if woot and not (p.hostname == 'woot.com' or p.hostname.endswith('.woot.com')):
        raise ValueError('woot_url must point directly to woot.com')

def price(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError('Prices must be finite positive numbers')

def validate(d):
    for k in ('title','woot_url','image','price','comparisons','pct_below','posted_at','writeup','checked_at'):
        if k not in d: raise ValueError(f'Missing {k}')
    for k in ('title','writeup','image','woot_url','posted_at','checked_at'):
        if not isinstance(d[k],str) or not d[k].strip(): raise ValueError(f'Invalid {k}')
    url(d['woot_url'], True); url(d['image']); price(d['price'])
    if 'amazon_asin' in d:
        if not isinstance(d['amazon_asin'], str) or not re.fullmatch(r'[A-Z0-9]{10}', d['amazon_asin']):
            raise ValueError('amazon_asin must be a 10-character Amazon product identifier')
        if not isinstance(d.get('amazon_match_notes'), str) or not d['amazon_match_notes'].strip():
            raise ValueError('Describe the verified Amazon model, variant and quantity in amazon_match_notes')
    now = dt.datetime.now(dt.timezone.utc)
    for k in ('posted_at','checked_at'):
        t=timestamp(d[k])
        if t > now + dt.timedelta(minutes=5): raise ValueError(f'{k} is in the future')
    if now-timestamp(d['checked_at']) > dt.timedelta(hours=24):
        raise ValueError('Recheck prices before publishing: checked_at is over 24 hours old')
    if len(d['writeup'].split()) < 30: raise ValueError('Provide an original 2–4 sentence write-up (at least 30 words)')
    if not isinstance(d['comparisons'],list) or not d['comparisons']: raise ValueError('At least one verified retailer comparison is required')
    for c in d['comparisons']:
        for k in ('store','price','url','checked_at','notes'):
            if k not in c: raise ValueError(f'Comparison missing {k}')
        price(c['price']); url(c['url'])
        if c.get('available') is not True: raise ValueError('Comparison must explicitly confirm available: true')
        if c.get('matching') is not True: raise ValueError('Comparison must explicitly confirm matching: true')
        t=timestamp(c['checked_at'])
        if t > now+dt.timedelta(minutes=5) or now-t > dt.timedelta(hours=24): raise ValueError('Comparison price check must be within 24 hours')
    pct=math.floor((1-d['price']/min(c['price'] for c in d['comparisons']))*100+1e-9)
    if pct < 40: raise ValueError(f'Deal is only {pct}% below the lowest comparison; minimum is 40%')
    if d['pct_below'] != pct: raise ValueError(f'pct_below must be {pct}, rounded down from the lowest comparison')
    slug=re.sub(r'[^a-z0-9]+','-',d['title'].lower()).strip('-')[:90]
    if not slug: raise ValueError('Title must produce a valid slug')
    return slug+'-'+hashlib.sha256(d['woot_url'].split('?')[0].encode()).hexdigest()[:8]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('json_file', type=Path)
    p.add_argument('--dry-run',action='store_true',help='Validate only, without writing or pushing')
    p.add_argument('--write-only',action='store_true',help='Write validated JSON without committing or pushing')
    args=p.parse_args()
    d=json.loads(args.json_file.read_text()); slug=validate(d)
    target=ROOT/'deals'/f'{slug}.json'
    text=json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if args.dry_run:
        print(f'Valid: deals/{target.name}'); return
    gitdir=Path(run('git','rev-parse','--absolute-git-dir').strip())
    with (gitdir/'linkszn-publish.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if not args.write_only:
            if run('git','branch','--show-current').strip() != 'main': raise ValueError('Publisher requires main branch')
            if run('git','status','--porcelain').strip(): raise ValueError('Checkout must be clean; preserve existing work before publishing')
            run('git','pull','--ff-only','origin','main')
        mapping=load_short(); had=slug in mapping; code=short_code(slug,mapping); mapping[slug]=code
        same=target.exists() and target.read_text()==text
        if same and had:
            if not args.write_only: run('git','push','origin','main')
            print(f'Already present: https://linkszn.com/deals/{slug}/')
            print(f'Short link: https://linkszn.com/d/{code}'); return
        target.parent.mkdir(exist_ok=True)
        if not same:
            temp=target.with_suffix('.json.tmp'); temp.write_text(text); temp.replace(target)
        save_short(mapping)
        if args.write_only:
            print(f'Written: {target}'); print(f'Short link: https://linkszn.com/d/{code}'); return
        rel=target.relative_to(ROOT).as_posix()
        run('git','add','--',rel,'shortlinks.json')
        run('git','commit','-m',f'Publish deal: {d["title"]}','--',rel,'shortlinks.json')
        run('git','push','origin','main')
        print(f'Pushed {run("git","rev-parse","HEAD").strip()}')
        print(f'Deployment queued; verify https://linkszn.com/deals/{slug}/ before calling it live.')
        print(f'Short link: https://linkszn.com/d/{code} (live once the deploy finishes)')

if __name__=='__main__':
    try: main()
    except (ValueError,KeyError,TypeError,json.JSONDecodeError,subprocess.CalledProcessError) as e:
        print(f'Publish failed: {e}',file=sys.stderr); sys.exit(1)
