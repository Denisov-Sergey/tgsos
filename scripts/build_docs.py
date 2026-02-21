#!/usr/bin/env python3
"""
Генерирует AGENTS.md и CLOUDE.md из структуры проекта, requirements и .env.example.
Запуск: из корня репозитория: python scripts/build_docs.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Единый источник правды: структура репозитория
STRUCTURE_LINES = [
    "- `backend/` — API и статика (роутеры categories, channels, posts, collect; `static/index.html`).",
    "- `collector/` — сборщик постов: `python -m collector.run [limit]`.",
    "- `database/` — модели Category, Channel, Post; async сессия и init_db.",
    "- `scripts/` — скрипты (build_docs.py).",
    "- `docs/` — документация (RELATED_PROJECTS.md).",
    "- `config.py` — настройки из .env.",
]

# Единый источник правды: список API
API_LINES = [
    "GET/POST/DELETE /api/categories — категории.",
    "GET /api/channels, POST /api/channels (username, title, category_id), PATCH/DELETE /api/channels/{id}.",
    "GET /api/posts — посты (фильтры: category_id, channel_id, from_date, to_date, search, page, page_size).",
    "GET /api/posts/{id} — один пост.",
    "GET /api/collect/status — идёт ли сбор.",
    "POST /api/collect/run?limit=200 — запустить сбор в фоне (202 = запущен, 409 = уже идёт).",
]

REQUIRED_ENV_KEYS = ("API_ID", "API_HASH")


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def parse_env_example(content: str) -> tuple[list[str], list[str]]:
    """Парсит .env.example: возвращает (обязательные, опциональные) ключи. Сортировка, без дублей."""
    required = []
    optional = []
    seen = set()
    key_pattern = re.compile(r"^#?\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        m = key_pattern.match(line)
        if not m:
            continue
        key = m.group(1)
        if key in seen:
            continue
        seen.add(key)
        if key in REQUIRED_ENV_KEYS:
            required.append(key)
        else:
            optional.append(key)

    required_sorted = sorted(required)
    optional_sorted = sorted(optional)
    return required_sorted, optional_sorted


def main() -> None:
    requirements_path = ROOT / "requirements.txt"
    env_example_path = ROOT / ".env.example"
    requirements = read_file(requirements_path)
    env_example = read_file(env_example_path)

    env_required, env_optional = parse_env_example(env_example)
    env_required_block = "\n".join(f"- `{k}` (обязательно)" for k in env_required) if env_required else ""
    env_optional_block = "\n".join(f"- `{k}` (опционально)" for k in env_optional) if env_optional else ""
    env_full_block = (env_required_block + "\n" + env_optional_block).strip() if (env_required or env_optional) else "- См. `.env.example`"

    structure_block = "\n".join(STRUCTURE_LINES)
    api_block = "\n".join(f"- {line}" for line in API_LINES)

    dedup_section = """## Дедупликация

- **Посты:** уникальность по паре `(channel_id, message_id)`. При повторном сборе запись обновляется (upsert), дубли не создаются.
- **Каналы:** при добавлении проверка по `username` — повторное добавление возвращает 400.
- **Категории:** уникальность по `name` в модели."""

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

**Docker:** все переменные из `.env`. Запуск API: `docker compose up -d --build`. Сбор постов: `docker compose run --rm collector` (первый раз с `-it` для ввода кода Telegram). В интерфейсе на вкладке «Каналы» есть кнопка **«Запустить сбор постов»**; при необходимости можно включить автозапуск сборщика через `SCHEDULER_INTERVAL_MINUTES` в `.env`.

**Важно:** кнопка «Запустить сбор» и встроенный планировщик рассчитаны на один процесс (один воркер uvicorn). Не запускайте приложение с `--workers 2+`.

## Переменные окружения

{env_full_block}

## Зависимости (основные)

```
{requirements[:800]}{"..." if len(requirements) > 800 else ""}
```

{dedup_section}

## Конвенции кода

- Python: type hints, async def для I/O, snake_case.
- FastAPI: Pydantic-модели для запросов/ответов; Depends(get_session) для БД.
- Не коммитить `.env`, сессии Telethon, `*.db` (см. .gitignore).

## API (кратко)

{api_block}

Документация: http://localhost:8000/docs

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

{chr(10).join(f"- **{k}**" for k in env_required + env_optional) if (env_required or env_optional) else "- См. `.env.example`"}

## Структура

{structure_block}

{dedup_section}

## API (кратко)

{api_block}

Документация: http://localhost:8000/docs

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
