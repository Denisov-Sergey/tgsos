# AGENTS.md — инструкции для AI-агентов (TGSOS)

Файл под формат [AGENTS.md](https://agents.md/). Содержит контекст для coding-агентов (Cursor, Aider, Copilot и др.).

## Обзор проекта

**TGSOS** — личный сервис сбора постов из Telegram-каналов в одну БД с веб-интерфейсом для просмотра и поиска.

- Язык: **Python 3.11+**
- Backend: **FastAPI**, Uvicorn
- БД: **SQLAlchemy 2.0**, SQLite (aiosqlite)
- Telegram: **Telethon** (user client, не Bot API)

## Структура репозитория

- `backend/` — API и статика (роутеры categories, channels, posts, collect; `static/index.html`).
- `collector/` — сборщик постов: `python -m collector.run [limit]`.
- `database/` — модели Category, Channel, Post; async сессия и init_db.
- `scripts/` — скрипты (build_docs.py).
- `docs/` — документация (RELATED_PROJECTS.md).
- `config.py` — настройки из .env.

## Сборка и запуск

- Установка: `pip install -r requirements.txt`
- Конфиг: скопировать `.env.example` в `.env`, указать `API_ID`, `API_HASH` (см. my.telegram.org).
- API и веб: `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
- Сбор постов: `python -m collector.run` (при первом запуске — вход в Telegram).

**Docker:** все переменные из `.env`. Запуск API: `docker compose up -d --build`. Сбор постов: `docker compose run --rm collector` (первый раз с `-it` для ввода кода Telegram). В интерфейсе на вкладке «Каналы» есть кнопка **«Запустить сбор постов»**; при необходимости можно включить автозапуск сборщика через `SCHEDULER_INTERVAL_MINUTES` в `.env`.

**Важно:** кнопка «Запустить сбор» и встроенный планировщик рассчитаны на один процесс (один воркер uvicorn). Не запускайте приложение с `--workers 2+`.

## Переменные окружения

- `API_HASH` (обязательно)
- `API_ID` (обязательно)
- `COLLECTOR_LIMIT` (опционально)
- `DATABASE_URL` (опционально)
- `PORT` (опционально)
- `SCHEDULER_INTERVAL_MINUTES` (опционально)
- `TELEGRAM_SESSION_PATH` (опционально)

## Зависимости (основные)

```
telethon>=1.34.0
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
python-dotenv>=1.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
aiosqlite>=0.19.0
```

## Дедупликация

- **Посты:** уникальность по паре `(channel_id, message_id)`. При повторном сборе запись обновляется (upsert), дубли не создаются.
- **Каналы:** при добавлении проверка по `username` — повторное добавление возвращает 400.
- **Категории:** уникальность по `name` в модели.

## Конвенции кода

- Python: type hints, async def для I/O, snake_case.
- FastAPI: Pydantic-модели для запросов/ответов; Depends(get_session) для БД.
- Не коммитить `.env`, сессии Telethon, `*.db` (см. .gitignore).

## API (кратко)

- GET/POST/DELETE /api/categories — категории.
- GET /api/channels, POST /api/channels (username, title, category_id), PATCH/DELETE /api/channels/{id}.
- GET /api/posts — посты (фильтры: category_id, channel_id, from_date, to_date, search, page, page_size).
- GET /api/posts/{id} — один пост.
- GET /api/collect/status — идёт ли сбор.
- POST /api/collect/run?limit=200 — запустить сбор в фоне (202 = запущен, 409 = уже идёт).

Документация: http://localhost:8000/docs

## Документация

- README: установка и использование.
- CLOUDE.md: сводка по стеку и командам (генерируется этим скриптом).
- docs/RELATED_PROJECTS.md: похожие решения на GitHub.
- Правила Cursor: `.cursor/rules/` (python-fastapi-tgsos, docs-and-agents, docker-rebuild — автопересборка после правок в backend/collector/Docker).

---
*Сгенерировано скриптом scripts/build_docs.py. Редактировать при необходимости или менять скрипт и перезапускать.*
