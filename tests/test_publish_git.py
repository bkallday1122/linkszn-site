"""Exercise publishing against a disposable local bare remote; no network or secrets."""
import datetime as dt
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'publish_deal.py'

class GitPublishTests(unittest.TestCase):
 def test_publish_retry_and_dirty_checkout_protection(self):
  with tempfile.TemporaryDirectory(prefix='linkszn-git-test-') as temp:
   root=Path(temp);remote=root/'remote.git';work=root/'work';work.mkdir()
   def git(*args,cwd=work):
    return subprocess.check_output(['git',*args],cwd=cwd,stderr=subprocess.PIPE,text=True).strip()
   git('init','--bare',str(remote));git('init','-b','main')
   git('config','user.name','Publisher test');git('config','user.email','test@example.invalid')
   shutil.copy2(SCRIPT,work/'publish_deal.py');(work/'deals').mkdir();(work/'deals'/'.gitkeep').touch()
   git('add','.');git('commit','-m','Initial');git('remote','add','origin',str(remote));git('push','-u','origin','main')
   stamp=dt.datetime.now(dt.timezone.utc).isoformat()
   d=dict(title='Verified integration fixture',woot_url='https://www.woot.com/offers/fixture',image='https://example.com/photo.jpg',price=20,comparisons=[dict(store='Fixture',price=50,url='https://example.com/item',checked_at=stamp,notes='Test only',available=True,matching=True)],pct_below=60,posted_at=stamp,checked_at=stamp,writeup=' '.join(['Original']*35))
   source=root/'input.json';source.write_text(json.dumps(d))
   def publish():
    return subprocess.run(['python3',str(work/'publish_deal.py'),str(source)],cwd=work,text=True,capture_output=True)
   first=publish();self.assertEqual(first.returncode,0,first.stderr)
   head=git('rev-parse','HEAD');self.assertEqual(head,git('rev-parse','refs/heads/main',cwd=remote))
   self.assertEqual(len(list((work/'deals').glob('*.json'))),1)
   self.assertTrue(git('show','--format=','--name-only','HEAD').startswith('deals/'))
   retry=publish();self.assertEqual(retry.returncode,0,retry.stderr);self.assertEqual(head,git('rev-parse','HEAD'))
   (work/'unrelated.txt').write_text('Preserve this work')
   dirty=publish();self.assertNotEqual(dirty.returncode,0);self.assertIn('Checkout must be clean',dirty.stderr)
   self.assertEqual(head,git('rev-parse','HEAD'));self.assertEqual((work/'unrelated.txt').read_text(),'Preserve this work')

if __name__=='__main__': unittest.main()
