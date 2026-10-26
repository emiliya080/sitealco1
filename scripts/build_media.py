"""Build local responsive photographs and attribution records from downloaded Commons originals.

Originals and Commons imageinfo JSON records are kept outside the repository.
Pass their directory as the first argument. No network or artificial upscaling.
"""
from pathlib import Path
from html import unescape
import concurrent.futures,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
source=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/tmp/candidates')
# id: source basename, optional original-pixel crop, truthful subject description.
SPECS={
'opening':('user-layered',None,'Многослойный коктейль со льдом и апельсином — обработка фото пользователя'),
'character':('detail-negroni',None,'Янтарный Негрони со льдом и цитрусовой цедрой на тёмной барной стойке'),
'moment':('footer',None,'Коктейль Pendennis Club на ножке рядом с бутылками в тёплом барном свете'),
'negroni-detail':('hero-negroni',None,'Негрони в низком хрустальном бокале'),
'negroni':('detail-negroni',None,'Негрони с апельсиновой цедрой'),
'margarita':('margarita-studio',None,'Маргарита с солёным краем бокала'),
'cosmopolitan':('cosmopolitan',None,'Космополитен в бокале на ножке'),
'mojito':('mojito-collegium','2900x4160+0+0','Мохито с мятой и льдом на барной стойке'),
'cranberry':('cranberry-alt',None,'Вариант подачи красного коктейля с цитрусом'),
'virgin-mojito':('zero-alt','2560x4096+1800+1400','Безалкогольный коктейль с мятой и цитрусом — вариант подачи'),
'lemonade':('lemonade',None,'Домашний лимонад в высоком бокале'),
'berry-spritz':('zero-alt','3000x4600+4350+1450','Ягодно-цитрусовый моктейль — вариант подачи'),
'mood-date':('wingko-negroni',None,'Коктейль Wingko Babat Negroni'),
'mood-friends':('yellow-glasses',None,'Ряд бокалов с жёлтыми коктейлями и фруктовыми гарнирами'),
'mood-summer':('mojito','3844x6741+650+0','Подача коктейля Fresh Mojito Premium'),
'knowledge':('craft-hugo',None,'Бутылки напитка Hugo с цитрусовыми этикетками'),
'zero':('berry-lemonade',None,'Малиновый лимонад с мятой и льдом'),
'finale':('footer',None,'Коктейль Pendennis Club с бутылками ингредиентов'),
'footer':('cranberry-alt',None,'Крупный план коктейля со льдом и цитрусовым гарниром'),
}
output=ROOT/'assets/photos';output.mkdir(parents=True,exist_ok=True)
USER_EDITS={'opening':'user-layered'}
RETOUCHES={'virgin-mojito':'virgin-mojito','berry-spritz':'berry-spritz'}
def build(pair):
 key,(base,crop,alt)=pair
 user=key in USER_EDITS
 if user:
  original=ROOT/'assets/photo-edits'/(USER_EDITS[key]+'.png')
  dims=list(map(int,subprocess.check_output(['identify','-format','%w %h',str(original)],text=True).split()))
  info={'width':dims[0],'height':dims[1],'descriptionurl':None,'url':original.relative_to(ROOT).as_posix()};record={'title':'Фотография предоставлена пользователем: '+base}
  meta={};plain=lambda name:'';license='Предоставлено пользователем для оформления сайта'
 else:
  original=source/(base+'.jpg');record=json.loads((source/(base+'.json')).read_text());info=record['imageinfo'][0];meta=info['extmetadata']
  plain=lambda key:unescape(re.sub('<[^>]+>','',meta.get(key,{}).get('value',''))).strip()
  license=plain('LicenseShortName')
  if not (license.startswith('CC BY') or license in ['CC0','Public domain']):raise ValueError('Unsupported rights: '+key+' '+license)
 edited=key in RETOUCHES or user
 if key in RETOUCHES:original=ROOT/'assets/photo-edits'/(RETOUCHES[key]+'.png');crop=None
 native=list(map(int,subprocess.check_output(['convert',str(original),'-auto-orient','-format','%w %h','info:'],text=True).split()))
 if crop:native=list(map(int,re.match(r'(\d+)x(\d+)',crop).groups()))
 variants=[]
 for name,maxsize,quality in [('small',960,84),('medium',1920,88),('large',3840,90)]:
  edition='cinema' if key in ['character','moment'] else 'studio'
  dest=output/f'{key}-{edition}-{name}.webp'
  cmd=['convert',str(original),'-auto-orient']
  if crop:cmd+=['-crop',crop,'+repage']
  cmd+=['-resize',str(maxsize)+'x'+str(maxsize)+'>','-strip','-quality',str(quality),str(dest)]
  subprocess.run(cmd,check=True,capture_output=True)
  dims=subprocess.check_output(['identify','-format','%w %h',str(dest)],text=True).split()
  variants.append({'src':dest.relative_to(ROOT).as_posix(),'width':int(dims[0]),'height':int(dims[1]),'bytes':dest.stat().st_size})
 changes=('Фотография обработана генеративным редактором; подготовлены веб-версии без увеличения разрешения.' if edited else 'Кадрирование и WebP-конверсия; уменьшение без увеличения исходника.' if crop else 'WebP-конверсия и уменьшение без увеличения исходника; адаптивное кадрирование при показе.')
 if key=='opening':changes='По фото пользователя: удалены человек, перчатка и щипцы; фон и кадрирование адаптированы генеративным редактором.'
 if key=='character':changes='По фото пользователя: композиция адаптирована к широкому кадру, фон расширен генеративным редактором.'
 if key in RETOUCHES:changes='Фон с людьми и интерьером очищен генеративным редактором; сохранена фотографическая подача напитка.'
 return key,{'alt':alt,'sourceTitle':record['title'],'source':info['descriptionurl'],'original':info['url'].split('?')[0],'originalWidth':info['width'],'originalHeight':info['height'],'nativeWidth':native[0],'nativeHeight':native[1],'author':'Исходное фото предоставлено пользователем; автор не указан' if user else plain('Artist'),'license':license,'licenseUrl':None if user else plain('LicenseUrl') or 'https://creativecommons.org/publicdomain/zero/1.0/','changes':changes,'crop':crop,'userProvided':user,'backgroundRetouched':edited,'editedMaster':original.relative_to(ROOT).as_posix() if edited else None,'peopleFree':True,'variants':variants}
selected=set(sys.argv[2:]);unknown=selected-set(SPECS)
if unknown:raise SystemExit('Unknown photograph IDs: '+', '.join(sorted(unknown)))
current=json.loads((ROOT/'content/photo-manifest.json').read_text())['photos']
rows=current if selected else {key:row for key,row in current.items() if row.get('changes','').startswith('Файл заменён пользователем')}
# Direct replacements uploaded by the owner are authoritative and must not be
# overwritten by a later full rebuild from the older source-photo archive.
protected={key for key,row in rows.items() if row.get('changes','').startswith('Файл заменён пользователем')}
items=[(key,value) for key,value in SPECS.items() if (not selected or key in selected) and key not in protected]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for k,row in pool.map(build,items):rows[k]=row;print(k,row['variants'][-1]['width'],row['variants'][-1]['height'],flush=True)
manifest={'version':2,'sourceProvider':'Wikimedia Commons и обработанные фотографии пользователя','photos':rows,'recipes':{id:id for id in ['negroni','margarita','cosmopolitan','mojito','cranberry','virgin-mojito','lemonade','berry-spritz']}}
(ROOT/'content/photo-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(ROOT/'site-media.js').write_text('// Local, inspected photographs. Attribution: photos.html\nwindow.DG_MEDIA='+json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+';\n')
