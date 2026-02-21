# CLOUDE.md — сводка по проекту TGSOS

Краткий контекст для разработки и для AI-агентов: стек, команды, переменные.

## Стек

| Слой      | Технология        |
|-----------|-------------------|
| Backend   | FastAPI, Uvicorn  |
| БД        | SQLAlchemy 2.0, SQLite (aiosqlite) |
| Telegram  | Telethon (user client) |
| Конфиг    | python-dotenv, .env |

## Команды

| Действие        | Команда |
|-----------------|--------|
| Запуск API      | `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000` |
| Сбор постов     | `python -m collector.run` или `python -m collector.run 500` |
| Генерация доков | `python scripts/build_docs.py` |
| Docker: запуск API | `docker compose up -d --build` |
| Docker: сбор постов | `docker compose run --rm collector` (первый раз: `run --rm -it`) |
| Docker: остановка | `docker compose down` |

## Переменные окружения

- **API_HASH**
- **API_ID**
- **COLLECTOR_LIMIT**
- **DATABASE_URL**
- **PORT**
- **SCHEDULER_INTERVAL_MINUTES**
- **TELEGRAM_SESSION_PATH**

## Структура

- `backend/` — API и статика (роутеры categories, channels, posts, collect; `static/index.html`).
- `collector/` — сборщик постов: `python -m collector.run [limit]`.
- `database/` — модели Category, Channel, Post; async сессия и init_db.
- `scripts/` — скрипты (build_docs.py).
- `docs/` — документация (RELATED_PROJECTS.md).
- `config.py` — настройки из .env.

## Дедупликация

- **Посты:** уникальность по паре `(channel_id, message_id)`. При повторном сборе запись обновляется (upsert), дубли не создаются.
- **Каналы:** при добавлении проверка по `username` — повторное добавление возвращает 400.
- **Категории:** уникальность по `name` в модели.

## API (кратко)

- GET/POST/DELETE /api/categories — категории.
- GET /api/channels, POST /api/channels (username, title, category_id), PATCH/DELETE /api/channels/{id}.
- GET /api/posts — посты (фильтры: category_id, channel_id, from_date, to_date, search, page, page_size).
- GET /api/posts/{id} — один пост.
- GET /api/collect/status — идёт ли сбор.
- POST /api/collect/run?limit=200 — запустить сбор в фоне (202 = запущен, 409 = уже идёт).

Документация: http://localhost:8000/docs

---
*Обновляется скриптом scripts/build_docs.py.*
