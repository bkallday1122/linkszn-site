#!/usr/bin/env python3
"""Make 1200x628 JPEG card images at public/img/<slug>.jpg from each deal's image.
Usage: make_og_images.py [slug ...]  (no args = every deal missing one)."""
import io,json,pathlib,re,sys,urllib.request
from PIL import Image
ROOT=pathlib.Path(__file__).resolve().parent; OUT=ROOT/'public'/'img'
def src(u): return re.sub(r'\._AC_[^.]*_(?=\.\w+$)','',u)  # full-size original
def make(slug):
    out=OUT/f'{slug}.jpg'
    if out.exists(): return False
    d=json.loads((ROOT/'deals'/f'{slug}.json').read_text())
    img=d.get('image') or d.get('image_url') or d.get('img') or ''
    cands=[src(img),img] if img else []
    if d.get('woot_url'):
        try:
            h=urllib.request.urlopen(urllib.request.Request(d['woot_url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=20).read().decode('utf8','ignore')
            m=re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)',h) or re.search(r'content=["\']([^"\']+)["\'][^>]*property=["\']og:image',h)
            if m: cands.append(m.group(1))
        except Exception: pass
    b=None
    for u in cands:
        try:
            b=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=20).read(); break
        except Exception: b=None
    if not b: print('no image',slug); return False
    im=Image.open(io.BytesIO(b)).convert('RGBA'); bg=Image.new('RGB',(1200,628),'white')
    im.thumbnail((1120,588),Image.LANCZOS); bg.paste(im,((1200-im.width)//2,(628-im.height)//2),im)
    OUT.mkdir(parents=True,exist_ok=True); bg.save(out,'JPEG',quality=85,optimize=True); return True
if __name__=='__main__':
    slugs=sys.argv[1:] or [p.stem for p in sorted((ROOT/'deals').glob('*.json'))]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(16) as ex: print(sum(ex.map(make,slugs)),'made')
