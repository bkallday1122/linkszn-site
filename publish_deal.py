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
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
SHORT_ALPHA='abcdefghjkmnpqrstuvwxyz23456789'
AMAZON_TAG='linksznn-20'
ASIN_RE=re.compile(r'^[A-Z0-9]{10}$')
ASIN_PATH_RE=re.compile(r'/(?:dp|gp/product|gp/aw/d)/([A-Z0-9]{10})(?:/|$)',re.I)
# Public deal JSON is committed to a public repo. Strip internal Amazon/pipeline fields.
PUBLIC_KEYS=(
    'title','source','source_url','woot_url','image','price','comparisons','pct_below',
    'posted_at','checked_at','writeup','category','condition','notes','expires_at',
    'amazon_asin','amazon_match_notes','amazon_match_checked_at','kind',
    'promo_code','woot_price','promo_expires',
)

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

def amazon_host(value):
    host=(urlparse(value).hostname or '').lower()
    return host=='amazon.com' or host.endswith('.amazon.com')

def extract_asin(value):
    path=urlparse(value).path or ''
    m=ASIN_PATH_RE.search(path)
    return m.group(1).upper() if m else None

def affiliate_url(asin):
    return f'https://www.amazon.com/dp/{asin}?tag={AMAZON_TAG}'

def source_of(d):
    s=str(d.get('source') or '').strip().lower()
    if s in ('amazon','woot'): return s
    if d.get('woot_url'): return 'woot'
    if d.get('source_url') or d.get('amazon_asin'): return 'amazon'
    return 'woot'

def buy_url_of(d):
    return d['source_url'] if source_of(d)=='amazon' else d['woot_url']

def slug_hash_url(d):
    if source_of(d)=='amazon':
        return f'https://www.amazon.com/dp/{d["amazon_asin"]}'
    return d['woot_url'].split('?')[0]

def public_deal(d):
    out={k:d[k] for k in PUBLIC_KEYS if k in d}
    if source_of(d)=='amazon':
        out['source']='amazon'
        out['source_url']=d['source_url']
        out['amazon_asin']=d['amazon_asin']
        out.pop('woot_url', None)
    else:
        out.pop('source', None)
        out.pop('source_url', None)
    return out

def normalize_amazon(d):
    if 'image' not in d and isinstance(d.get('image_url'), str) and d['image_url'].strip():
        d['image']=d['image_url']
    asin=d.get('amazon_asin') or extract_asin(d.get('source_url') or d.get('affiliate_url') or '')
    if not isinstance(asin, str) or not ASIN_RE.fullmatch(asin):
        raise ValueError('amazon_asin must be a 10-character Amazon product identifier')
    raw=d.get('source_url') or d.get('affiliate_url') or ''
    if raw:
        url(raw)
        if not amazon_host(raw):
            raise ValueError('Amazon source_url must point to amazon.com')
        got=extract_asin(raw)
        if got and got!=asin:
            raise ValueError('source_url ASIN does not match amazon_asin')
        tags=parse_qs(urlparse(raw).query).get('tag') or []
        if tags and tags[0]!=AMAZON_TAG:
            raise ValueError('Amazon buy link must use the linksznn-20 associate tag')
    d['amazon_asin']=asin
    d['source']='amazon'
    d['source_url']=affiliate_url(asin)
    return d

def validate(d):
    src=source_of(d)
    if src=='amazon':
        normalize_amazon(d)
        required=('title','source_url','image','price','comparisons','pct_below','posted_at','writeup','checked_at')
        strings=('title','writeup','image','source_url','posted_at','checked_at')
    else:
        required=('title','woot_url','image','price','comparisons','pct_below','posted_at','writeup','checked_at')
        strings=('title','writeup','image','woot_url','posted_at','checked_at')
    for k in required:
        if k not in d: raise ValueError(f'Missing {k}')
    for k in strings:
        if not isinstance(d[k],str) or not d[k].strip(): raise ValueError(f'Invalid {k}')
    if src=='amazon':
        url(d['source_url']); url(d['image']); price(d['price'])
    else:
        url(d['woot_url'], True); url(d['image']); price(d['price'])
        if 'amazon_asin' in d:
            if not isinstance(d['amazon_asin'], str) or not ASIN_RE.fullmatch(d['amazon_asin']):
                raise ValueError('amazon_asin must be a 10-character Amazon product identifier')
            if not isinstance(d.get('amazon_match_notes'), str) or not d['amazon_match_notes'].strip():
                raise ValueError('Describe the verified Amazon model, variant and quantity in amazon_match_notes')
    if d.get('kind') is not None:
        kind=str(d.get('kind') or '').strip().lower()
        if kind not in ('new','restock'): raise ValueError('kind must be new or restock')
        d['kind']=kind
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
        store=str(c.get('store') or '').strip()
        if not store: raise ValueError('Comparison is missing a store name')
        if re.fullmatch(r'amazon', store, re.I):
            raise ValueError('Do not list Amazon as a comparison store or show Amazon comparison prices')
        if amazon_host(c['url']) and src!='amazon':
            raise ValueError('Do not use Amazon URLs as comparison prices')
        if amazon_host(c['url']) and src=='amazon':
            # Manufacturer/official-store references may live on Amazon, but must be named as that store, never "Amazon".
            if not re.search(r'official|manufacturer|brand store', str(c.get('notes') or ''), re.I):
                raise ValueError('An Amazon-hosted comparison must be a named official/manufacturer store, not an Amazon price')
        if c.get('available') is not True: raise ValueError('Comparison must explicitly confirm available: true')
        if c.get('matching') is not True: raise ValueError('Comparison must explicitly confirm matching: true')
        t=timestamp(c['checked_at'])
        if t > now+dt.timedelta(minutes=5) or now-t > dt.timedelta(hours=24): raise ValueError('Comparison price check must be within 24 hours')
    pct=math.floor((1-d['price']/min(c['price'] for c in d['comparisons']))*100+1e-9)
    if pct < 40: raise ValueError(f'Deal is only {pct}% below the lowest comparison; minimum is 40%')
    if d['pct_below'] != pct: raise ValueError(f'pct_below must be {pct}, rounded down from the lowest comparison')
    slug=re.sub(r'[^a-z0-9]+','-',d['title'].lower()).strip('-')[:90]
    if not slug: raise ValueError('Title must produce a valid slug')
    return slug+'-'+hashlib.sha256(slug_hash_url(d).encode()).hexdigest()[:8]

def schedule_push():
    """Hand the commit to the debounced pusher (one push per ~45s burst = one Cloudflare build)."""
    subprocess.Popen([sys.executable,str(ROOT/'push_pending.py')],cwd=ROOT,start_new_session=True,
                     stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('json_file', type=Path)
    p.add_argument('--dry-run',action='store_true',help='Validate only, without writing or pushing')
    p.add_argument('--write-only',action='store_true',help='Write validated JSON without committing or pushing')
    args=p.parse_args()
    d=json.loads(args.json_file.read_text()); slug=validate(d)
    target=ROOT/'deals'/f'{slug}.json'
    text=json.dumps(public_deal(d),ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if args.dry_run:
        print(f'Valid: deals/{target.name}'); return
    gitdir=Path(run('git','rev-parse','--absolute-git-dir').strip())
    with (gitdir/'linkszn-publish.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if not args.write_only:
            if run('git','branch','--show-current').strip() != 'main': raise ValueError('Publisher requires main branch')
            if run('git','status','--porcelain').strip(): raise ValueError('Checkout must be clean; preserve existing work before publishing')
            # local unpushed deal commits may exist (debounced pusher); rebase keeps them
            subprocess.run(['git','fetch','-q','origin','main'],cwd=ROOT)
            if subprocess.run(['git','rev-list','--count','origin/main..main'],cwd=ROOT,text=True,capture_output=True).stdout.strip()=='0':
                run('git','pull','--ff-only','origin','main')
        mapping=load_short(); had=slug in mapping; code=short_code(slug,mapping); mapping[slug]=code
        same=target.exists() and target.read_text()==text
        if same and had:
            if not args.write_only: schedule_push()
            print(f'Already present: https://linkszn.com/deals/{slug}/')
            print(f'Short link: https://linkszn.com/d/{code}'); return
        target.parent.mkdir(exist_ok=True)
        if not same:
            temp=target.with_suffix('.json.tmp'); temp.write_text(text); temp.replace(target)
        save_short(mapping)
        if args.write_only:
            print(f'Written: {target}'); print(f'Short link: https://linkszn.com/d/{code}'); return
        rel=target.relative_to(ROOT).as_posix()
        extra=[]
        try:
            import make_og_images; make_og_images.make(slug)
            if (ROOT/'public'/'img'/f"{slug}.jpg").exists(): extra=[f"public/img/{slug}.jpg"]
        except Exception as e: print('Card image skipped:',type(e).__name__)
        run('git','add','--',rel,'shortlinks.json',*extra)
        run('git','commit','-m',f'Publish deal: {d["title"]}','--',rel,'shortlinks.json',*extra)
        schedule_push()
        print(f'Pushed {run("git","rev-parse","HEAD").strip()} (committed; batched push within ~45s)')
        print(f'Deployment queued; verify https://linkszn.com/deals/{slug}/ before calling it live.')
        print(f'Short link: https://linkszn.com/d/{code} (live once the deploy finishes)')

if __name__=='__main__':
    try: main()
    except (ValueError,KeyError,TypeError,json.JSONDecodeError,subprocess.CalledProcessError) as e:
        print(f'Publish failed: {e}',file=sys.stderr); sys.exit(1)
