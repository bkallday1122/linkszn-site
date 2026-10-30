#!/usr/bin/env python3
"""Git credential helper: disclose the local token only to this repository."""
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 2 or sys.argv[1] != 'get':
    sys.exit(0)
fields=dict(line.rstrip('\n').split('=',1) for line in sys.stdin if '=' in line)
if fields.get('protocol') != 'https' or fields.get('host') != 'github.com' or fields.get('path','').removesuffix('.git') != 'bkallday1122/linkszn-site':
    sys.exit(0)
root=Path(__file__).resolve().parent
gitdir=Path(subprocess.check_output(['git','rev-parse','--absolute-git-dir'],cwd=root,text=True).strip())
secret=gitdir/'linkszn-publisher.token'
if not secret.is_file(): sys.exit(0)
if secret.stat().st_mode & 0o077:
    print('Refusing token file readable by other users',file=sys.stderr);sys.exit(1)
print('username=bkallday1122')
print('password='+secret.read_text().strip())
