"""Build an honest public attribution, editing and native-resolution index."""
from pathlib import Path
from html import escape as e
import json
ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/'content/photo-manifest.json').read_text())
base=(ROOT/'about.html').read_text();head=base[:base.index('<main>')].replace('<title>О проекте — Drunken Guide</title>','<title>Авторы фотографий — Drunken Guide</title>')
footer=base[base.index('<footer class="platform-footer">'):]
rows=[]
for key,r in m['photos'].items():
 small=r['variants'][0];large=r['variants'][-1]
 license=f'<a href="{e(r["licenseUrl"])}" target="_blank" rel="noopener noreferrer">{e(r["license"])}</a>' if r['licenseUrl'] else e(r['license'])
 source=f'<a href="{e(r["source"])}" target="_blank" rel="noopener noreferrer">Страница исходного фото →</a>' if r['source'] else ''
 original=f'<a href="{e(r["original"])}" target="_blank" rel="noopener noreferrer">'+('Обработанный мастер →' if r['userProvided'] else 'Оригинал фотографии →')+'</a>'
 native=f'<br>Обработанный мастер: {r["nativeWidth"]} × {r["nativeHeight"]} пикселей.' if r['backgroundRetouched'] else ''
 label='Обработанный исходник' if r['userProvided'] else 'Оригинал фотографии'
 rows.append(f'''<article id="photo-{key}" class="photo-credit"><a href="{large['src']}" aria-label="Открыть: {e(r['alt'])}"><img src="{small['src']}" alt="{e(r['alt'])}" loading="lazy" width="{small['width']}" height="{small['height']}"></a><h2>{e(r['alt'])}</h2><p>Авторство: {e(r['author'])}. Условия: {license}.</p><p class="credit-size">{label}: {r['originalWidth']} × {r['originalHeight']} пикселей.{native}<br>Большая версия сайта: {large['width']} × {large['height']} пикселей.</p><p>{e(r['changes'])}</p><div class="credit-links">{source}{original}<a href="{large['src']}">Версия сайта →</a></div></article>''')
main='''<main><section class="page-heading wrap"><p class="breadcrumbs"><a href="index.html">Главная</a> / Фотографии</p><p class="eyebrow">ФОТОГРАФИИ И ОБРАБОТКА</p><h1>Авторы фотографий</h1><p class="page-intro">Здесь указаны источники, авторы, условия использования, реальные размеры и обработка каждого снимка. В первой сцене используется обработанная фотография, предоставленная пользователем: человек удалён, фон расширен генеративным редактором. Во второй и третьей сценах — фотографии Wikimedia Commons с тёплой барной палитрой. Такой же способ очистки фона применён к двум безалкогольным карточкам.</p></section><section class="wrap photo-credits"><p class="page-intro">Файлы не увеличивались искусственно. У обработанных мастеров своё исходное разрешение: их версии не выдаются за 4K-оригиналы. Для прочих фотографий сохранены исходные лицензии. Снимки с пометкой «вариант подачи» иллюстрируют сервировку; точный состав — в рецептах. Все изображения загружаются с самого сайта.</p><div class="photo-credit-grid">'''+''.join(rows)+'''</div><p class="page-intro"><a href="catalog.html">Перейти к рецептам →</a></p></section></main>'''
(ROOT/'photos.html').write_text(head+main+footer)
