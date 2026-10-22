# Видео при прокрутке

Подключён фрагмент файла videoplayback.mp4, предоставленного пользователем (исходная ссылка https://www.youtube.com/watch?v=3irS3ovgYvQ).

После просмотра контактных листов выбран непрерывный план наполнения коктейльного бокала: 00:27.350–00:29.300. Экспорт assets/pour-scroll.mp4: H.264, 640×360, 24 кадра/с, около 275 КБ, без аудио, ключевые кадры каждые 6 кадров, faststart. Постер assets/pour-poster.jpg взят из первого кадра этого же фрагмента. Полный исходник в репозиторий не включён.

Команда обработки:

```sh
python3 scripts/prepare_scroll_video.py /path/to/videoplayback.mp4 --start 27.35 --duration 1.95 --activate
ffmpeg -i assets/pour-scroll.mp4 -frames:v 1 -q:v 2 assets/pour-poster.jpg
```

Прокрутка вперёд и назад меняет время остановленного ролика. Видео загружается вблизи секции. При ошибке загрузки, выключении анимации и prefers-reduced-motion остаётся настоящий кадр. На телефоне видео расположено над текстом; на компьютере справа. Исходное разрешение не позволяет получить детализацию 1080p.

Проверка:

```sh
STORY_TEST_BASE_URL=http://127.0.0.1:8003 node tests/scroll-video.browser.cjs
STORY_TEST_BASE_URL=http://127.0.0.1:8003 node tests/photo-home.browser.cjs
```
