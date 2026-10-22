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
'opening':('negroni-sbagliato',None,'Наливание Negroni Sbagliato в хрустальный бокал'),
'character':('cosmopolitan',None,'Космополитен в коктейльном бокале'),
'moment':('zero-scene',None,'Безалкогольные коктейли в бокалах на столе'),
'negroni-detail':('hero-negroni',None,'Негрони в низком хрустальном бокале'),
'negroni':('detail-negroni',None,'Негрони с апельсиновой цедрой'),
'margarita':('margarita-alt',None,'Маргарита с солёным краем бокала'),
'cosmopolitan':('cosmo-alt',None,'Космополитен в бокале на ножке'),
'mojito':('mojito-collegium',None,'Мохито с мятой и льдом на барной стойке'),
'cranberry':('cranberry-alt',None,'Вариант подачи красного коктейля с цитрусом'),
'virgin-mojito':('zero-alt','2560x4096+1800+1400','Безалкогольный коктейль с мятой и цитрусом — вариант подачи'),
'lemonade':('lemonade',None,'Домашний лимонад в высоком бокале'),
'berry-spritz':('zero-alt','3000x4600+4350+1450','Ягодно-цитрусовый моктейль — вариант подачи'),
'mood-date':('wingko-negroni',None,'Коктейль Wingko Babat Negroni'),
'mood-friends':('margarita',None,'Маргарита со льдом и солёным краем'),
'mood-summer':('mojito',None,'Подача коктейля Fresh Mojito Premium'),
'knowledge':('bar',None,'Бокал с цитрусовым гарниром на стойке настоящего бара'),
'zero':('berry-lemonade',None,'Малиновый лимонад с мятой и льдом'),
'finale':('footer',None,'Коктейль Pendennis Club с бутылками ингредиентов'),
'footer':('knowledge',None,'Бармен за работой — реальные бутылки и барные инструменты'),
}
output=ROOT/'assets/photos';output.mkdir(parents=True,exist_ok=True)
def build(pair):
 key,(base,crop,alt)=pair
 original=source/(base+'.jpg');record=json.loads((source/(base+'.json')).read_text());info=record['imageinfo'][0];meta=info['extmetadata']
 plain=lambda key:unescape(re.sub('<[^>]+>','',meta.get(key,{}).get('value',''))).strip()
 license=plain('LicenseShortName')
 if not (license.startswith('CC BY') or license in ['CC0','Public domain']):raise ValueError('Unsupported rights: '+key+' '+license)
 variants=[]
 for name,maxsize,quality in [('small',960,82),('medium',1920,85),('large',3840,88)]:
  dest=output/f'{key}-{name}.webp'
  cmd=['convert',str(original),'-auto-orient']
  if crop:cmd+=['-crop',crop,'+repage']
  cmd+=['-resize',str(maxsize)+'x'+str(maxsize)+'>','-strip','-quality',str(quality),str(dest)]
  subprocess.run(cmd,check=True,capture_output=True)
  dims=subprocess.check_output(['identify','-format','%w %h',str(dest)],text=True).split()
  variants.append({'src':dest.relative_to(ROOT).as_posix(),'width':int(dims[0]),'height':int(dims[1]),'bytes':dest.stat().st_size})
 return key,{'alt':alt,'sourceTitle':record['title'],'source':info['descriptionurl'],'original':info['url'].split('?')[0],'originalWidth':info['width'],'originalHeight':info['height'],'author':plain('Artist'),'license':license,'licenseUrl':plain('LicenseUrl') or 'https://creativecommons.org/publicdomain/zero/1.0/','changes':'Кадрирование и WebP-конверсия; уменьшение без увеличения исходника.' if crop else 'WebP-конверсия и уменьшение без увеличения исходника; кадрирование при отображении.','crop':crop,'variants':variants}
rows={}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for k,row in pool.map(build,SPECS.items()):rows[k]=row;print(k,row['variants'][-1]['width'],row['variants'][-1]['height'],flush=True)
manifest={'version':1,'sourceProvider':'Wikimedia Commons','photos':rows,'recipes':{id:id for id in ['negroni','margarita','cosmopolitan','mojito','cranberry','virgin-mojito','lemonade','berry-spritz']}}
(ROOT/'content/photo-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(ROOT/'site-media.js').write_text('// Local, inspected photographs. Attribution: photos.html\nwindow.DG_MEDIA='+json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+';\n')
