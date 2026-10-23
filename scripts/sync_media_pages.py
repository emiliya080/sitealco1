"""Refresh static photo references, asset versions and CSS from the local manifest."""
from pathlib import Path
from html import escape as e
import json,re
ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/'content/photo-manifest.json').read_text());photos=m['photos'];paths={}
for key,row in photos.items():
 for variant,name in zip(row['variants'],['small','medium','large']):
  paths[f'assets/photos/{key}-{name}.webp']=(row,variant)
  paths[variant['src']]=(row,variant)
def update_image(match):
 tag=match[0];src=re.search(r'\bsrc="([^"]+)"',tag)
 if not src or src[1] not in paths:return tag
 row,variant=paths[src[1]]
 tag=tag.replace(src[1],variant['src'])
 if 'srcset=' in tag:
  unique=sorted({v['width']:v for v in row['variants']}.values(),key=lambda v:v['width'])
  srcset=', '.join(f"{v['src']} {v['width']}w" for v in unique)
  tag=re.sub(r'\bsrcset="[^"]*"',f'srcset="{srcset}"',tag)
 tag=re.sub(r'\balt="[^"]*"','alt="'+e(row['alt'])+'"',tag)
 for dimension in ['width','height']:tag=re.sub(r'\b'+dimension+r'="[^"]*"',dimension+'="'+str(variant[dimension])+'"',tag)
 return tag
for page in ROOT.glob('*.html'):
 html=page.read_text();html=re.sub(r'<img\b[^>]*>',update_image,html)
 html=re.sub(r'style.css\?v=\d+','style.css?v=12',html);html=re.sub(r'site-media.js\?v=\d+','site-media.js?v=2',html);html=re.sub(r'platform.js\?v=\d+','platform.js?v=8',html)
 page.write_text(html)
for page in ROOT.glob('*.css'):
 css=page.read_text()
 for old,(row,variant) in paths.items():
  if old!=variant['src']:css=css.replace(old,variant['src'])
 page.write_text(css)
