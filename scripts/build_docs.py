#!/usr/bin/env python3
"""
Генерирует AGENTS.md и CLOUDE.md из структуры проекта, requirements и .env.example.
Запуск: из корня репозитория: python scripts/build_docs.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def main() -> None:
    requirements_path = ROOT / "requirements.txt"
    env_example_path = ROOT / ".env.example"
    requirements = read_file(requirements_path)
    env_example = read_file(env_example_path)

    env_vars = []
    for line in env_example.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key = line.split("=")[0].strip()
            env_vars.append(key)

    structure_lines = [
        "- `backend/` — API и статика (роутеры channels, posts; `static/index.html`).",
        "- `collector/` — сборщик постов: `python -m collector.run [limit]`.",
        "- `database/` — модели Channel, Post; async сессия и init_db.",
        "- `scripts/` — скрипты (build_docs.py).",
        "- `docs/` — документация (RELATED_PROJECTS.md).",
        "- `config.py` — настройки из .env.",
    ]
    structure_block = "\n".join(structure_lines)

    agents_md = f"""# AGENTS.md — инструкции для AI-агентов (TGSOS)

Файл под формат [AGENTS.md](https://agents.md/). Содержит контекст для coding-агентов (Cursor, Aider, Copilot и др.).

## Обзор проекта

**TGSOS** — личный сервис сбора постов из Telegram-каналов в одну БД с веб-интерфейсом для просмотра и поиска.

- Язык: **Python 3.11+**
- Backend: **FastAPI**, Uvicorn
- БД: **SQLAlchemy 2.0**, SQLite (aiosqlite)
- Telegram: **Telethon** (user client, не Bot API)

## Структура репозитория

{structure_block}

## Сборка и запуск

- Установка: `pip install -r requirements.txt`
- Конфиг: скопировать `.env.example` в `.env`, указать `API_ID`, `API_HASH` (см. my.telegram.org).
- API и веб: `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
- Сбор постов: `python -m collector.run` (при первом запуске — вход в Telegram).

**Docker:** все переменные из `.env`. Запуск API: `docker compose up -d --build`. Сбор постов: `docker compose run --rm collector` (первый раз с `-it` для ввода кода Telegram).

## Переменные окружения

{chr(10).join(f"- `{v}`" for v in env_vars) if env_vars else "- См. `.env.example`"}

## Зависимости (основные)

```
{requirements[:800]}{"..." if len(requirements) > 800 else ""}
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
"""

    cloude_md = f"""# CLOUDE.md — сводка по проекту TGSOS

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

{chr(10).join(f"- **{v}**" for v in env_vars) if env_vars else "- См. `.env.example`"}

## Структура

{structure_block}

## API (кратко)

- `GET/POST/DELETE /api/channels` — каналы.
- `GET /api/posts` — посты (фильтры: channel_id, from_date, to_date, search, page, page_size).
- `GET /api/posts/{{id}}` — один пост.
- Документация: http://localhost:8000/docs

---
*Обновляется скриптом scripts/build_docs.py.*
"""

    agents_path = ROOT / "AGENTS.md"
    cloude_path = ROOT / "CLOUDE.md"
    agents_path.write_text(agents_md, encoding="utf-8")
    cloude_path.write_text(cloude_md, encoding="utf-8")
    print(f"Written: {agents_path}")
    print(f"Written: {cloude_path}")


if __name__ == "__main__":
    main()
