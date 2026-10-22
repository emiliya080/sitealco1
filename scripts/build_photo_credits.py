"""Build a public attribution and original-resolution index for every local photograph."""
from pathlib import Path
from html import escape as e
import json,re
ROOT=Path(__file__).resolve().parents[1]
m=json.loads((ROOT/'content/photo-manifest.json').read_text())
base=(ROOT/'about.html').read_text();head=base[:base.index('<main>')].replace('<title>О проекте — Drunken Guide</title>','<title>Авторы фотографий — Drunken Guide</title>')
# Dedicated page uses the regular shared header and footer.
footer=base[base.index('<footer class="platform-footer">'):]
rows=[]
for key,r in m['photos'].items():
 v=r['variants'];small=v[0];large=v[-1]
 rows.append(f'''<article id="photo-{key}" class="photo-credit"><a href="{large['src']}" aria-label="Открыть фотографию {e(r['alt'])} в большом размере"><img src="{small['src']}" alt="{e(r['alt'])}" loading="lazy" width="{small['width']}" height="{small['height']}"></a><h2>{e(r['alt'])}</h2><p>Автор: {e(r['author'])}. Лицензия: <a href="{e(r['licenseUrl'])}" target="_blank" rel="noopener noreferrer">{e(r['license'])}</a>.</p><p class="credit-size">Оригинал: {r['originalWidth']} × {r['originalHeight']} пикселей.<br>Большая версия сайта: {large['width']} × {large['height']} пикселей.</p><p>{e(r['changes'])}</p><div class="credit-links"><a href="{e(r['source'])}" target="_blank" rel="noopener noreferrer">Страница автора и файла →</a><a href="{e(r['original'])}" target="_blank" rel="noopener noreferrer">Оригинал →</a><a href="{large['src']}">Большая версия →</a></div></article>''')
main='''<main><section class="page-heading wrap"><p class="breadcrumbs"><a href="index.html">Главная</a> / Фотографии</p><p class="eyebrow">РЕАЛЬНАЯ СЪЁМКА</p><h1>Авторы фотографий</h1><p class="page-intro">На сайте используются фотографии настоящих напитков, а не сгенерированные изображения. Здесь указаны авторы, исходные размеры, лицензии и изменения каждого файла. Все фотографии загружаются с самого сайта.</p></section><section class="wrap photo-credits"><p class="page-intro">Копии обработаны без искусственного увеличения разрешения. Пропорции сохранены; для экранов подготовлены разные размеры. Обработанные версии доступны на условиях указанной для них лицензии. Фотографии с пометкой «вариант подачи» иллюстрируют сервировку, а точный состав напитка указан в рецепте.</p><div class="photo-credit-grid">'''+''.join(rows)+'''</div><p class="page-intro"><a href="catalog.html">Перейти к рецептам →</a></p></section></main>'''
(ROOT/'photos.html').write_text(head+main+footer)
