// Turn dist/d/<code>/index.html into dist/d/<code>.html so /d/<code> serves 200 with no 308 slash redirect.
import fs from 'node:fs'; import path from 'node:path';
const D='dist/d'; if (fs.existsSync(D)) for (const c of fs.readdirSync(D)) { const f=path.join(D,c,'index.html');
  if (fs.existsSync(f)) { fs.renameSync(f, path.join(D,c+'.html')); fs.rmdirSync(path.join(D,c)); } }
