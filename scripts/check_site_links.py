"""Check local page/assets/fragment links without following external URLs."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
root=Path(__file__).resolve().parents[1]
class Page(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.ids=set()
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if 'id' in attrs:self.ids.add(attrs['id'])
  for key in ('href','src'):
   if attrs.get(key):self.links.append(attrs[key])
pages={}
for file in root.glob('*.html'):
 parsed=Page();parsed.feed(file.read_text());pages[file.resolve()]=parsed
errors=[];count=0
for file,page in pages.items():
 for link in page.links:
  url=urlsplit(link)
  if url.scheme or url.netloc:continue
  target=(file.parent/unquote(url.path)).resolve() if url.path else file
  if not target.exists():errors.append(f'{file.name}: missing {link}');continue
  if url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:errors.append(f'{file.name}: missing fragment {link}')
  count+=1
if errors:raise SystemExit('\n'.join(errors))
print(f'PASS: {len(pages)} pages; {count} local page, asset and fragment links resolve.')
