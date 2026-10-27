"""Rebuild the content-rich homepage from the checked-in recipe catalogue."""
from pathlib import Path
import json,re
from html import escape as esc
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'content/platform-data.json').read_text())
ing={i['id']:i for i in data['ingredients']};recipes={r['id']:r for r in data['recipes']}
MEDIA=json.loads((ROOT/'content/photo-manifest.json').read_text())
photos={id:MEDIA['recipes'][id] for id in ['negroni','margarita','cosmopolitan','mojito','blue-lagoon','bloody-mary']}
def image(id,cls='',sizes='100vw',eager=False):
 row=MEDIA['photos'][MEDIA['recipes'].get(id,id)];variants=row['variants'];src=variants[1]['src'];srcset=', '.join(f"{v['src']} {v['width']}w" for v in sorted({v['width']:v for v in variants}.values(),key=lambda v:v['width']))
 return f'<img class="{cls}" src="{src}" srcset="{srcset}" sizes="{sizes}" alt="{esc(row["alt"])}" loading="{"eager" if eager else "lazy"}" decoding="async" width="{variants[1]["width"]}" height="{variants[1]["height"]}">'
def lifestyle(id,alt,cls=''):
 return image(id,cls)
def parts(r,limit=9):
 return ''.join(f'<li><span>{esc(ing[p["id"]]["name"])}</span><b>{p["amount"]} {esc(ing[p["id"]]["unit"])}</b></li>' for p in r['parts'] if p['id']!='ice')
def card(id):
 r=recipes[id]
 return f'<a class="story-recipe-card" href="recipe-{id}.html" data-reveal><div class="story-card-image">{image(id)}<span>{r["minutes"]} мин · {esc(r["method"])}</span></div><div class="story-card-copy"><p class="eyebrow">{esc(r["base"])} / {esc(r["taste"])}</p><h3>{esc(r["name"])}</h3><p>{esc(r["intro"])}</p><ul class="story-parts">{parts(r)}</ul><span class="story-link">Рецепт, пропорции и приготовление <b aria-hidden="true">↗</b></span></div></a>'
p=ROOT/'index.html';old=p.read_text();head=old[:old.index('<main id="main">')];opening_start=old.index('<section class="photo-interlude"');opening=old[opening_start:old.index('</section>',opening_start)+len('</section>')]
opening=opening.replace('<h2 id="photo-moment-title">','<h1 id="photo-moment-title">').replace('В чистом виде.</em></h2>','В чистом виде.</em></h1>')
for i,key in enumerate(['opening','character','moment']):
 pattern=r'(<article class="photo-slide" data-photo="'+str(i)+r'"[^>]*>)<img[^>]*>'
 opening=re.sub(pattern,lambda m:m[1]+image(key,'photo-scene-image',eager=True),opening)
opening=re.sub(r'<a class="photo-source".*?</a>','<a class="photo-source" href="photos.html">Авторы фотографий ↗</a>',opening)
hero_messages=[
 ('От классики к своему вкусу','Точные пропорции, понятные рецепты и сочетания, к которым хочется возвращаться.','catalog.html','Открыть каталог'),
 ('Соберите вкус своими руками','Выберите коктейль — мы покажем ингредиенты, пропорции и каждый шаг приготовления.','catalog.html','Приготовить коктейль'),
 ('Повод уже звучит по-особенному','Праздничные, романтические и сезонные подборки помогут задать настроение вечеру.','collections.html','Выбрать подборку'),
]
def enrich_slide(match):
 article=match.group(0);i=int(match.group(1));title,copy,href,label=hero_messages[i]
 article=re.sub(r'<p class="photo-caption">.*?</p>',f'<p class="photo-caption"><strong>{title}</strong><span>{copy}</span></p>',article,flags=re.S)
 article=re.sub(r'<a class="cinema-cta" href="[^"]+">.*?</a>',f'<a class="cinema-cta" href="{href}">{label} <span aria-hidden="true">↗</span></a>',article,flags=re.S)
 return article
opening=re.sub(r'<article class="photo-slide" data-photo="([0-2])".*?</article>',enrich_slide,opening,flags=re.S)

# Hero now carries the sole page H1; no fake phone UI on the homepage.
r=recipes['negroni']
steps=[('Найдите свой вкус','Выберите основу, характер и настроение напитка — подбор поможет быстро найти подходящий рецепт.'),('Подготовьте ингредиенты','Проверьте точные пропорции и соберите всё необходимое заранее, чтобы ничего не отвлекало от процесса.'),('Откройте приготовление','Следуйте наглядным шагам рецепта, отмечайте результат и сохраняйте удачные сочетания в избранное.')]
recipe_video='<video class="recipe-journey-video" muted playsinline preload="auto" poster="assets/video/recipe-steps-poster.jpg" aria-label="Атмосферная подача коктейля с пламенем"><source src="assets/video/recipe-steps-scroll.mp4" type="video/mp4"></video>'
spotlight='<section id="negroni-story" class="recipe-journey" data-scroll-effect="recipe"><div class="recipe-journey-pin"><a class="recipe-journey-photo" href="builder.html?mode=preferences" aria-label="Подобрать коктейль по своему вкусу">'+recipe_video+'<span>ABSINTHE <b>RITUAL &amp; FLAME</b></span><small class="recipe-video-status" role="status" hidden>Видео не загрузилось — показана заставка.</small></a><div class="recipe-journey-copy"><p class="eyebrow">01 / ОТ ИДЕИ К ПОДАЧЕ</p><h2>Ваш вкус.<br><em>Ваш ритуал.</em></h2><ol class="recipe-story-steps">'+''.join(f'<li data-recipe-step="{i}"><span class="step-number">0{i+1}</span><div><h3>{title}</h3><p>{copy}</p></div></li>' for i,(title,copy) in enumerate(steps))+'</ol><a class="story-button" href="builder.html?mode=preferences">Открыть подбор <span aria-hidden="true">↗</span></a><div class="recipe-scene-progress" aria-hidden="true"><span></span></div></div></div></section>'
catalog='<section id="recipes" class="home-recipe-section"><div class="section-title"><div><p class="eyebrow">02 / РЕЦЕПТЫ, К КОТОРЫМ ВОЗВРАЩАЮТСЯ</p><h2>Начните с классики.</h2></div><div class="recipe-loop-actions"><button class="recipe-loop-toggle" type="button" aria-pressed="false"><span aria-hidden="true">Ⅱ</span><b>Пауза</b></button><a class="story-link" href="catalog.html">Весь каталог ↗</a></div></div><div class="recipe-loop-window" data-recipe-loop aria-label="Зацикленная подборка рецептов"><div class="home-recipe-grid">'+''.join(card(id) for id in photos)+'</div></div><p class="recipe-loop-hint">Тяните карточки мышью или пальцем <span aria-hidden="true">↔</span></p></section>'
knowledge='<section id="knowledge" class="knowledge-section knowledge-video-section"><div class="knowledge-video-inner"><div class="knowledge-video-media"><video class="knowledge-scroll-video" muted playsinline preload="auto" poster="assets/video/knowledge-ice-poster.jpg" aria-label="Кубики льда падают в бокал с виски"><source src="assets/video/knowledge-ice-scroll.mp4" type="video/mp4"></video><div class="knowledge-video-shade"></div><p class="knowledge-video-status" role="status" hidden>Видео не загрузилось — показан статичный кадр.</p></div><div class="knowledge-copy"><p class="eyebrow">04 / НЕ ТОЛЬКО РЕЦЕПТЫ</p><h2>У каждого вкуса<br>своя история.</h2><p class="knowledge-lead">Лёд падает в бокал, пока вы открываете характер напитков.</p><div class="knowledge-grid">'+''.join(f'<a href="encyclopedia-{id}.html"><span>{tag}</span><h3>{name}</h3><p>{copy}</p><b aria-hidden="true">Читать ↗</b></a>' for id,tag,name,copy in [('gin','ТРАВЫ И ПРЯНОСТИ','Джин','Можжевельник, ботаникалы и разница между основными стилями.'),('rum','САХАРНЫЙ ТРОСТНИК','Ром','Сырьё, выдержка и характер напитка, на котором строится мохито.'),('tequila','ГОЛУБАЯ АГАВА','Текила','Как производят текилу и чем отличаются её основные категории.'),('wine','ТИХИЕ И ИГРИСТЫЕ','Вино','Стили, характеристики и примеры производителей.')])+'</div><a class="story-link" href="encyclopedia.html">Вся энциклопедия ↗</a></div></div></section>'
toolitems=[('builder.html?mode=bar','01','Что есть дома?','Укажите ингредиенты и количество. Посмотрите, что можно приготовить прямо сейчас.'),('builder.html?mode=preferences','02','Попасть во вкус','Выберите основу, вкус и тип напитка — получите подходящие рецепты.'),('compare.html','03','Сравнить рецепты','Сопоставьте ингредиенты, сложность, время и расчётную крепость.'),('planner.html','04','Собрать вечеринку','Добавьте коктейли и порции. Общие ингредиенты сложатся в список покупок.'),('builder.html?mode=create','05','Создать своё','Соберите собственное сочетание с расчётом объёма и крепости.'),('favorites.html','06','Сохранить любимое','Возвращайтесь к избранным рецептам. Ваш выбор хранится на этом устройстве.')]
tools='<section id="home-tools" class="home-tools" data-scroll-effect="stagger"><div class="section-title"><div><p class="eyebrow">06 / ОТ ИДЕИ К ХОРОШЕМУ ВЕЧЕРУ</p><h2>Ваш домашний бар.</h2></div><p>Инструменты работают без регистрации.<br>Планы и избранное сохраняются на устройстве.</p></div><div class="home-tool-grid">'+''.join(f'<a href="{href}" data-reveal><span>{n}</span><h3>{name}</h3><p>{copy}</p><b aria-hidden="true">Открыть ↗</b></a>' for href,n,name,copy in toolitems)+'</div></section>'
final='<section class="home-finale" data-scroll-effect="finale">'+image('finale','finale-photo')+'<p class="eyebrow">ХОРОШИЙ ВКУС НАЧИНАЕТСЯ С ЛЮБОПЫТСТВА</p><h2>Какой рецепт<br><em>будет вашим?</em></h2><div><a class="story-button" href="catalog.html">Найти свой коктейль ↗</a><a class="story-link" href="about.html">О Drunken Guide ↗</a></div><p class="source-note">Фотографии коктейлей и обработка фона. <a href="photos.html">Авторы, исходники и лицензии ↗</a>.</p></section>'
footer=old[old.index('<footer class="platform-footer">'):old.index('<script src="script.js')]
start=footer.find('<div><h3>Наше приложение</h3>');start=footer.find('<div><h3>Ваши инструменты</h3>') if start<0 else start;footer=footer[:start]+'<div><h3>Ваши инструменты</h3><a href="favorites.html">Избранные рецепты</a><a href="compare.html">Сравнение коктейлей</a><a href="planner.html">План и список покупок</a><a href="builder.html?mode=bar">Домашний бар</a><a href="download.html">О мобильном приложении</a><a href="photos.html">Авторы фотографий и лицензии</a></div></div></footer>'
footer=re.sub(r'<a class="footer-photo".*?</a>','',footer,count=1,flags=re.S)
scripts='<script src="script.js?v=7"></script><script src="site-config.js"></script><script src="site-media.js?v=2"></script><script src="platform-core.js?v=1"></script><script src="platform.js?v=11"></script><script src="photo-home.js?v=8"></script><script src="recipe-loop.js?v=4"></script><script src="home-story.js?v=6"></script></body></html>'
s=head+'<main id="main">'+opening+spotlight+catalog+knowledge+tools+final+'</main>'+footer+scripts
s=re.sub(r'<link rel="stylesheet" href="home-story.css\?v=\d+">','',s);s=re.sub(r'photo-home.css\?v=\d+','photo-home.css?v=7',s).replace('</head>','<link rel="stylesheet" href="home-story.css?v=23"></head>')
s=s.replace('↗','<span class="ui-arrow" aria-hidden="true"></span>');p.write_text(s)
