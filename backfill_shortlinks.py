#!/usr/bin/env python3
"""One-time: assign stable short codes to every existing deal (never changes existing codes)."""
from pathlib import Path
import publish_deal as p
m=p.load_short(); n=0
for f in sorted((p.ROOT/'deals').glob('*.json')):
    if f.stem not in m: m[f.stem]=p.short_code(f.stem,m); n+=1
p.save_short(m); print(f'added {n}, total {len(m)}')
