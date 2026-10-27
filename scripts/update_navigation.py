"""Keep the primary navigation identical across every static page."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ITEMS = [
    ('index.html', 'Главная'),
    ('drinks.html', 'Каталог'),
    ('catalog.html', 'Коктейли'),
    ('reviews.html', 'Отзывы'),
    ('collections.html', 'Подборки'),
    ('community.html', 'Сообщество'),
    ('encyclopedia.html', 'Интересное'),
]

ICONS = {
    'search.html': '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/></svg>',
    'favorites.html': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.8 9.2c0 5-8.8 10.1-8.8 10.1S3.2 14.2 3.2 9.2A4.4 4.4 0 0 1 12 8a4.4 4.4 0 0 1 8.8 1.2Z"/></svg>',
    'notifications.html': '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5.5 17.5h13l-1.7-2.2V10a4.8 4.8 0 0 0-9.6 0v5.3Z"/><path d="M10 20h4"/></svg>',
    'account.html': '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3.5"/><path d="M5.5 20c.6-4 2.8-6 6.5-6s5.9 2 6.5 6"/></svg>',
}

def tools(name):
    labels = [('search.html','Поиск'),('favorites.html','Избранное'),('notifications.html','Уведомления'),('account.html','Профиль')]
    return '<div class="header-tools" aria-label="Личные разделы">' + ''.join(f'<a href="{href}" aria-label="{label}" data-label="{label}"{(" class=\"active\" aria-current=\"page\"" if name == href else "")}>{ICONS[href]}<span>{label}</span></a>' for href,label in labels) + '</div>'

def normalize_header(text, name):
    text = re.sub(r'<a href="photos\.html"[^>]*>Авторы фотографий и лицензии</a>', '', text)
    text = re.sub(r'<label class="header-motion".*?</label>', '', text, count=1)
    text = re.sub(r'<nav aria-label="Основная навигация">.*?</nav>', nav(name), text, count=1)
    if '<div class="header-tools"' in text:
        text = re.sub(r'<div class="header-tools".*?</div>', tools(name), text, count=1)
    else:
        text = re.sub(r'<a class="account-link.*?</a>', tools(name), text, count=1)
    text = re.sub(r'<div class="utility-nav wrap".*?</div>', '', text, count=1)
    text = re.sub(r'<div class="wrap photo-preferences">.*?</div>', '', text, count=1)
    if name == 'index.html':
        control = '<label class="header-motion" title="Плавная анимация"><input id="photo-motion" type="checkbox" checked><span>Анимация</span></label>'
        text = text.replace('</div><button class="menu"', '</div>' + control + '<button class="menu"', 1)
    return text

def active_for(name):
    if name == 'index.html': return 'index.html'
    if name == 'drinks.html': return 'drinks.html'
    if name in {'catalog.html', 'mocktails.html', 'recipe.html'} or name.startswith('recipe-'): return 'catalog.html'
    if name == 'reviews.html': return 'reviews.html'
    if name == 'collections.html' or name.startswith('collection-') or name == 'occasions.html': return 'collections.html'
    if name == 'community.html': return 'community.html'
    if name == 'encyclopedia.html' or name.startswith('encyclopedia-'): return 'encyclopedia.html'

def nav(name):
    active = active_for(name)
    links = []
    for href, label in ITEMS:
        current = ' class="active" aria-current="page"' if href == active else ''
        links.append(f'<a href="{href}"{current}>{label}</a>')
    return '<nav aria-label="Основная навигация">' + ''.join(links) + '</nav>'

def create_page(name, title, eyebrow, intro, content):
    index = (ROOT / 'index.html').read_text()
    header = re.search(r'<header class="header wrap">.*?</header>(?:<div class="utility-nav wrap".*?</div>)?', index).group()
    footer = index[index.index('<footer class="platform-footer">'):]
    header = normalize_header(header, name)
    head = f'<!doctype html><html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#101110"><title>{title} — Drunken Guide</title><link rel="stylesheet" href="style.css?v=17"><link rel="icon" href="assets/favicon.svg" type="image/svg+xml"></head><body>'
    main = f'<main><section class="page-heading wrap"><p class="breadcrumbs"><a href="index.html">Главная</a> <span>/</span> {title}</p><p class="eyebrow">{eyebrow}</p><h1>{title}</h1><p class="page-intro">{intro}</p></section><section class="wrap page-section">{content}</section></main>'
    (ROOT / name).write_text(head + header + main + footer)

create_page('reviews.html', 'Отзывы', 'МНЕНИЯ И ОПЫТ', 'Оценки, фотографии и впечатления пользователей о приготовленных коктейлях.', '<div class="home-action-grid"><a href="catalog.html"><span>01</span><h3>Отзывы к рецептам</h3><p>Откройте коктейль, чтобы увидеть его рейтинг и опубликованные отзывы.</p><b>Перейти к коктейлям →</b></a><a href="account.html"><span>02</span><h3>Оставить отзыв</h3><p>Войдите в аккаунт, выберите приготовленный рецепт, поставьте оценку и добавьте фотографию.</p><b>Войти →</b></a></div><p class="hint">В общей ленте показываются только отзывы, прошедшие модерацию. На GitHub Pages серверная лента недоступна; она включается при размещении проекта на сервере.</p>')
create_page('community.html', 'Сообщество', 'ЛЮДИ И ИДЕИ', 'Профили, авторские рецепты, вопросы и общение вокруг культуры напитков.', '<div class="home-action-grid"><a href="account.html"><span>01</span><h3>Ваш профиль</h3><p>Настройте предпочтения, аватар и видимость имени в отзывах.</p><b>Открыть кабинет →</b></a><a href="builder.html?mode=create"><span>02</span><h3>Предложить рецепт</h3><p>Соберите собственный коктейль и отправьте его редакции сообщества.</p><b>Создать рецепт →</b></a><a href="help.html"><span>03</span><h3>Вопросы и ответы</h3><p>Ответы о рецептах, функциях сайта и работе личного кабинета.</p><b>Открыть помощь →</b></a></div><p class="hint">Список пользователей, друзья и публичные обсуждения появятся после подключения серверной версии. Сайт не показывает выдуманные профили.</p>')
create_page('search.html', 'Поиск', 'НАЙТИ НУЖНОЕ', 'Ищите коктейли по названию, основе, вкусу или ингредиенту.', '<form class="glass-panel global-search-form" action="catalog.html"><label for="global-search">Название или ингредиент</label><div class="global-search-row"><input id="global-search" name="q" type="search" placeholder="Например, джин, лайм или Negroni" autocomplete="off"><button class="outline-button">Найти коктейли</button></div></form><div class="home-action-grid"><a href="catalog.html"><span>01</span><h3>Коктейли</h3><p>Поиск по рецептам, основе, вкусу и ингредиентам.</p><b>Открыть каталог →</b></a><a href="drinks.html"><span>02</span><h3>Напитки</h3><p>Основные категории алкоголя и их особенности.</p><b>Смотреть напитки →</b></a><a href="encyclopedia.html"><span>03</span><h3>Статьи</h3><p>История, производство и культура напитков.</p><b>Открыть энциклопедию →</b></a></div>')
create_page('notifications.html', 'Уведомления', 'ВАШИ СОБЫТИЯ', 'Новые ответы, реакции, статусы публикаций и важные события аккаунта.', '<div class="glass-panel notification-empty"><p class="eyebrow">ПОКА ТИХО</p><h2>Новых уведомлений нет</h2><p>После входа здесь появятся ответы на отзывы, статусы предложенных рецептов и события вашего профиля.</p><a class="outline-button" href="account.html">Перейти в профиль →</a></div>')

pattern = re.compile(r'<nav aria-label="Основная навигация">.*?</nav>')
for path in ROOT.glob('*.html'):
    text = path.read_text()
    if pattern.search(text):
        text = normalize_header(text, path.name)
        text = re.sub(r'style\.css\?v=\d+', 'style.css?v=17', text)
        text = re.sub(r'platform\.js\?v=\d+', 'platform.js?v=11', text)
        path.write_text(text)
