# AGENTS.md — инструкции для AI-агентов (TGSOS)

Файл под формат [AGENTS.md](https://agents.md/). Содержит контекст для coding-агентов (Cursor, Aider, Copilot и др.).

## Обзор проекта

**TGSOS** — личный сервис сбора постов из Telegram-каналов в одну БД с веб-интерфейсом для просмотра и поиска.

- Язык: **Python 3.11+**
- Backend: **FastAPI**, Uvicorn
- БД: **SQLAlchemy 2.0**, SQLite (aiosqlite)
- Telegram: **Telethon** (user client, не Bot API)

## Структура репозитория

- `backend/` — API и статика (роутеры channels, posts; `static/index.html`).
- `collector/` — сборщик постов: `python -m collector.run [limit]`.
- `database/` — модели Channel, Post; async сессия и init_db.
- `scripts/` — скрипты (build_docs.py).
- `docs/` — документация (RELATED_PROJECTS.md).
- `config.py` — настройки из .env.

## Сборка и запуск

- Установка: `pip install -r requirements.txt`
- Конфиг: скопировать `.env.example` в `.env`, указать `API_ID`, `API_HASH` (см. my.telegram.org).
- API и веб: `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
- Сбор постов: `python -m collector.run` (при первом запуске — вход в Telegram).

**Docker:** все переменные из `.env`. Запуск API: `docker compose up -d --build`. Сбор постов: `docker compose run --rm collector` (первый раз с `-it` для ввода кода Telegram).

## Переменные окружения

- `API_ID`
- `API_HASH`
- `TELEGRAM_SESSION_PATH`
- `DATABASE_URL`

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

## Конвенции кода

- Python: type hints, async def для I/O, snake_case.
- FastAPI: Pydantic-модели для запросов/ответов; Depends(get_session) для БД.
- Не коммитить `.env`, сессии Telethon, `*.db` (см. .gitignore).

## Документация

- README: установка и использование.
- CLOUDE.md: сводка по стеку и командам (генерируется этим скриптом).
- docs/RELATED_PROJECTS.md: похожие решения на GitHub.
- Правила Cursor: `.cursor/rules/` (python-fastapi-tgsos, docs-and-agents).

---
*Сгенерировано скриптом scripts/build_docs.py. Редактировать при необходимости или менять скрипт и перезапускать.*
