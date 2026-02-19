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

- **API_ID**
- **API_HASH**
- **TELEGRAM_SESSION_PATH**
- **DATABASE_URL**

## Структура

- `backend/` — API и статика (роутеры channels, posts; `static/index.html`).
- `collector/` — сборщик постов: `python -m collector.run [limit]`.
- `database/` — модели Channel, Post; async сессия и init_db.
- `scripts/` — скрипты (build_docs.py).
- `docs/` — документация (RELATED_PROJECTS.md).
- `config.py` — настройки из .env.

## API (кратко)

- `GET/POST/DELETE /api/channels` — каналы.
- `GET /api/posts` — посты (фильтры: channel_id, from_date, to_date, search, page, page_size).
- `GET /api/posts/{id}` — один пост.
- Документация: http://localhost:8000/docs

---
*Обновляется скриптом scripts/build_docs.py.*
