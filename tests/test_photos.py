import json,unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
class Photos(unittest.TestCase):
 def test_real_resolution_and_sources(self):
  manifest=json.loads((ROOT/'content/photo-manifest.json').read_text())
  self.assertEqual(len(manifest['recipes']),8)
  for key,photo in manifest['photos'].items():
   with self.subTest(photo=key):
    self.assertTrue(photo['source'].startswith('https://commons.wikimedia.org/wiki/File:'))
    self.assertTrue(photo['license'].startswith('CC ' ) or photo['license']=='CC0')
    self.assertTrue(photo['author'])
    self.assertGreaterEqual(max(photo['originalWidth'],photo['originalHeight']),4000)
    for variant in photo['variants']:
     with Image.open(ROOT/variant['src']) as image:
      self.assertEqual(image.size,(variant['width'],variant['height']))
      self.assertEqual(image.format,'WEBP')
      self.assertLessEqual(image.width,photo['originalWidth'])
      self.assertLessEqual(image.height,photo['originalHeight'])
    self.assertEqual(max(photo['variants'][-1]['width'],photo['variants'][-1]['height']),3840)
 def test_main_scene_photos_are_distinct_and_local(self):
  from html.parser import HTMLParser
  class Images(HTMLParser):
   def __init__(self):super().__init__();self.images=[]
   def handle_starttag(self,tag,attrs):
    if tag=='img':self.images.append(dict(attrs))
  page=Images();page.feed((ROOT/'index.html').read_text())
  urls=[i['src'] for i in page.images]
  self.assertEqual(len(urls),len(set(urls)))
  self.assertGreaterEqual(len(urls),15)
  for url in urls:self.assertTrue(url.startswith('assets/photos/'));self.assertTrue((ROOT/url).is_file())
if __name__=='__main__':unittest.main()
