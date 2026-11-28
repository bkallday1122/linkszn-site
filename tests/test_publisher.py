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

 def test_amazon_source_deal(self):
  d=copy.deepcopy(self.d)
  d.pop('woot_url')
  d.update(source='amazon', source_url='https://www.amazon.com/dp/B00EO96LL0?tag=linksznn-20', amazon_asin='B00EO96LL0', kind='new')
  slug=p.validate(d)
  self.assertTrue(slug.startswith('a-useful-product-'))
  self.assertEqual(d['source_url'],'https://www.amazon.com/dp/B00EO96LL0?tag=linksznn-20')
  public=p.public_deal(d)
  self.assertEqual(public['source'],'amazon')
  self.assertNotIn('woot_url', public)
  self.assertNotIn('amazon_price', public)
  self.assertNotIn('reference_price', public)
 def test_amazon_buy_link_normalized_and_wrong_tag_rejected(self):
  d=copy.deepcopy(self.d)
  d.pop('woot_url')
  d.update(source='amazon', source_url='https://amazon.com/dp/B00EO96LL0', amazon_asin='B00EO96LL0')
  p.validate(d)
  self.assertEqual(d['source_url'],'https://www.amazon.com/dp/B00EO96LL0?tag=linksznn-20')
  d=copy.deepcopy(self.d); d.pop('woot_url')
  d.update(source='amazon', source_url='https://www.amazon.com/dp/B00EO96LL0?tag=other-20', amazon_asin='B00EO96LL0')
  with self.assertRaises(ValueError): p.validate(d)
 def test_rejects_amazon_named_comparison(self):
  self.d['comparisons'][0]['store']='Amazon'
  with self.assertRaises(ValueError): p.validate(self.d)
 def test_amazon_source_allows_named_manufacturer_comparison(self):
  d=copy.deepcopy(self.d)
  d.pop('woot_url')
  d.update(source='amazon', source_url='https://www.amazon.com/dp/B0DWS4QD67?tag=linksznn-20', amazon_asin='B0DWS4QD67')
  d['comparisons'][0].update(store='LiTHELi Official Store', url='https://www.amazon.com/dp/B0DWS4QD67', notes='Manufacturer official store offer, new and in stock')
  p.validate(d)
 def test_strips_internal_fields(self):
  d=copy.deepcopy(self.d)
  d.update(amazon_price=3.2, reference_price=5.45, comparison={'verdict':'pass'})
  pub=p.public_deal(d)
  self.assertNotIn('amazon_price', pub)
  self.assertNotIn('reference_price', pub)
  self.assertNotIn('comparison', pub)

 def test_useful_pick_amazon_no_discount_fields(self):
  d=copy.deepcopy(self.d)
  d.pop('woot_url'); d.pop('pct_below'); d['comparisons']=[]
  d.update(source='amazon', source_url='https://www.amazon.com/dp/B0HFSDPVQ1?tag=linksznn-20', amazon_asin='B0HFSDPVQ1', kind='useful_pick')
  slug=p.validate(d)
  self.assertTrue(slug.startswith('a-useful-product-'))
  self.assertEqual(d['comparisons'],[])
  self.assertNotIn('pct_below', d)
  pub=p.public_deal(d)
  self.assertEqual(pub['kind'],'useful_pick')
  self.assertEqual(pub['comparisons'],[])
  self.assertNotIn('pct_below', pub)
  self.assertNotIn('amazon_price', pub)
 def test_useful_pick_rejects_pct_below_and_comparisons(self):
  d=copy.deepcopy(self.d)
  d.pop('woot_url')
  d.update(source='amazon', source_url='https://www.amazon.com/dp/B0HFSDPVQ1?tag=linksznn-20', amazon_asin='B0HFSDPVQ1', kind='useful_pick')
  with self.assertRaises(ValueError): p.validate(d)
  d=copy.deepcopy(self.d)
  d.pop('woot_url'); d.pop('pct_below'); d['comparisons']=[]
  d.update(source='amazon', source_url='https://www.amazon.com/dp/B0HFSDPVQ1?tag=linksznn-20', amazon_asin='B0HFSDPVQ1', kind='useful_pick', pct_below=31)
  with self.assertRaises(ValueError): p.validate(d)
 def test_useful_pick_rejects_unknown_kind(self):
  self.d['kind']='pick'
  with self.assertRaises(ValueError): p.validate(self.d)


if __name__=='__main__': unittest.main()
