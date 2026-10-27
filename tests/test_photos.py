import json,unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
class Photos(unittest.TestCase):
 def test_real_resolution_and_sources(self):
  manifest=json.loads((ROOT/'content/photo-manifest.json').read_text())
  self.assertEqual(len(manifest['recipes']),13)
  for key,photo in manifest['photos'].items():
   with self.subTest(photo=key):
    if photo.get('userProvided'):
     if photo.get('backgroundRetouched'):self.assertTrue((ROOT/photo['editedMaster']).is_file())
     else:self.assertTrue((ROOT/photo['original']).is_file())
    else:self.assertTrue(photo['source'].startswith('https://commons.wikimedia.org/wiki/File:'))
    self.assertTrue(photo.get('userProvided') or photo['license'].startswith('CC ') or photo['license']=='CC0')
    self.assertTrue(photo.get('peopleFree'))
    self.assertTrue(photo['author'])
    self.assertGreaterEqual(max(photo['nativeWidth'],photo['nativeHeight']),1200)
    if not photo.get('userProvided'):self.assertGreaterEqual(max(photo['originalWidth'],photo['originalHeight']),3000)
    for variant in photo['variants']:
     with Image.open(ROOT/variant['src']) as image:
      self.assertEqual(image.size,(variant['width'],variant['height']))
      self.assertEqual(image.format,'WEBP')
      self.assertLessEqual(image.width,photo['nativeWidth'])
      self.assertLessEqual(image.height,photo['nativeHeight'])
    self.assertEqual(max(photo['variants'][-1]['width'],photo['variants'][-1]['height']),min(3840,max(photo['nativeWidth'],photo['nativeHeight'])))
 def test_main_scene_photos_are_distinct_and_local(self):
  from html.parser import HTMLParser
  class Images(HTMLParser):
   def __init__(self):super().__init__();self.images=[]
   def handle_starttag(self,tag,attrs):
    if tag=='img':self.images.append(dict(attrs))
  page=Images();page.feed((ROOT/'index.html').read_text())
  urls=[i['src'] for i in page.images]
  self.assertEqual(len(urls),len(set(urls)))
  self.assertGreaterEqual(len(urls),12)
  for image in page.images:
   descriptors=[part.strip().split()[-1] for part in image.get('srcset','').split(',') if part.strip()]
   self.assertEqual(len(descriptors),len(set(descriptors)))
  for url in urls:self.assertTrue(url.startswith('assets/photos/'));self.assertTrue((ROOT/url).is_file())
if __name__=='__main__':unittest.main()
