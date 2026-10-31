import copy
import datetime as dt
import unittest
import publish_deal as p

class ValidationTests(unittest.TestCase):
 def setUp(self):
  stamp=dt.datetime.now(dt.timezone.utc).isoformat()
  self.d=dict(title='A useful product',woot_url='https://sellout.woot.com/offers/example',image='https://example.com/photo.jpg',price=20,comparisons=[dict(store='Retailer',price=50,url='https://example.com/product',checked_at=stamp,notes='Matching model',available=True,matching=True)],pct_below=60,posted_at=stamp,checked_at=stamp,writeup=' '.join(['Original']*35))
 def test_valid_and_deterministic(self): self.assertEqual(p.validate(self.d),p.validate(copy.deepcopy(self.d)))
 def test_amazon_product_identifier(self):
  self.d['amazon_asin']='B00D8P5T0U'
  self.d['amazon_match_notes']='Energizer CR2032 four-pack'
  p.validate(self.d)
  for bad in ('https://example.com', 'B00D8P5T0U?tag=other', '', None):
   self.d['amazon_asin']=bad
   with self.assertRaises(ValueError): p.validate(self.d)
 def test_wrong_savings(self):
  self.d['pct_below']=80
  with self.assertRaises(ValueError): p.validate(self.d)
 def test_lowest_comparison_controls(self):
  c=copy.deepcopy(self.d['comparisons'][0]);c['price']=25;self.d['comparisons'].append(c)
  with self.assertRaises(ValueError): p.validate(self.d)
 def test_stale_comparison(self):
  self.d['comparisons'][0]['checked_at']='2020-01-01T00:00:00Z'
  with self.assertRaises(ValueError): p.validate(self.d)
 def test_mismatched_or_unavailable(self):
  for key in ('matching','available'):
   d=copy.deepcopy(self.d);d['comparisons'][0][key]=False
   with self.assertRaises(ValueError): p.validate(d)
 def test_false_woot_host(self):
  self.d['woot_url']='https://woot.com.example.org/deal'
  with self.assertRaises(ValueError): p.validate(self.d)
 def test_secret_url_and_nan(self):
  for url in ('https://user:secret@example.com/image','http://example.com/image'):
   d=copy.deepcopy(self.d);d['image']=url
   with self.assertRaises(ValueError): p.validate(d)
  self.d['price']=float('nan')
  with self.assertRaises(ValueError): p.validate(self.d)
if __name__=='__main__': unittest.main()
