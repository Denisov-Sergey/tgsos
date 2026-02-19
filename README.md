# TGSOS — личный агрегатор каналов Telegram

Сервис собирает посты из ваших Telegram-каналов в одну базу и даёт веб-интерфейс для просмотра и поиска.

## Требования

- Python 3.11+
- Аккаунт Telegram и [API ID / API Hash](https://my.telegram.org) (приложение на сайте)

## Установка

```bash
cd x:\Git\tgsos
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
cp .env.example .env
```

В `.env` укажите (все важные настройки — только через переменные окружения):

- `API_ID` — число с my.telegram.org  
- `API_HASH` — строка с my.telegram.org  
- `TELEGRAM_SESSION_PATH` — путь к файлу сессии (по умолчанию `./telethon_session`)  
- `DATABASE_URL` — URL БД (по умолчанию `sqlite+aiosqlite:///./tgsos.db`)  
- Опционально: `PORT` (для Docker), `COLLECTOR_LIMIT` (лимит постов при сборе)

## Запуск

### 1. API и веб-интерфейс

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Откройте в браузере: http://localhost:8000

### 2. Категории и каналы

- На вкладке **Каналы** создайте категории (например: «Финансы», «Новости») — кнопка «Добавить категорию».
- Добавьте каналы: укажите @username или ссылку `https://t.me/...`, при желании выберите категорию и название.
- Каналы можно фильтровать по категориям в ленте.

### 3. Сбор постов

При первом запуске сборщика потребуется войти в Telegram (номер телефона и код из приложения). Сессия сохранится в файл и больше не понадобится.

```bash
python -m collector.run
```

По умолчанию загружается до 200 последних сообщений с каждого канала. Лимит можно задать аргументом:

```bash
python -m collector.run 500
```

Для регулярного сбора можно запускать по расписанию (cron / Task Scheduler) или держать скрипт в цикле на VPS.

## Запуск в Docker

Все настройки задаются через `.env` (скопируйте `.env.example` в `.env` и заполните).

**Сборка и запуск API:**

```bash
docker compose up -d --build
```

Веб-интерфейс: http://localhost:8000 (порт можно изменить переменной `PORT` в `.env`).

Данные (БД и сессия Telethon) хранятся в volume `tgsos_data`. В Docker по умолчанию используются пути `/data/tgsos.db` и `/data/telethon_session` — при необходимости задайте в `.env`:

- `DATABASE_URL=sqlite+aiosqlite:////data/tgsos.db`
- `TELEGRAM_SESSION_PATH=/data/telethon_session`

**Первый вход в Telegram (сессия для сборщика):**

Сессия создаётся при первом запуске сборщика. Запустите контейнер сборщика **интерактивно** (чтобы ввести номер телефона и код из Telegram):

```bash
docker compose run --rm -it collector
```

После сохранения сессии в volume дальнейшие запуски можно делать без интерактива (например, по cron):

```bash
docker compose run --rm collector
# или с лимитом: docker compose run -e COLLECTOR_LIMIT=500 --rm collector
```

Остановка:

```bash
docker compose down
```

## Как начать собирать данные (кратко)

1. **Получите API_ID и API_HASH** на [my.telegram.org](https://my.telegram.org), пропишите их в `.env`.
2. **Запустите приложение:** `docker compose up -d --build` или локально `uvicorn backend.main:app --reload --port 8000`.
3. **Откройте** http://localhost:8000 → вкладка **Каналы**.
4. **Создайте категории** (Финансы, Новости и т.д.) и **добавьте каналы** — укажите @username или ссылку t.me, выберите категорию.
5. **Запустите сборщик:**  
   - Docker: первый раз интерактивно для входа в Telegram: `docker compose run --rm -it collector`.  
   - Дальше по расписанию или вручную: `docker compose run --rm collector` (или локально: `python -m collector.run`).
6. **Лента** — вкладка «Лента»: фильтр по категории/каналу, датам и поиск по тексту.

## Структура проекта

- `backend/` — FastAPI: REST API и раздача веб-интерфейса  
- `collector/` — сборщик на Telethon: чтение каналов и запись в БД  
- `database/` — модели (Category, Channel, Post) и сессия SQLAlchemy (SQLite по умолчанию)  
- `config.py` — настройки из `.env`

## API

- `GET/POST/DELETE /api/categories` — категории  
- `GET /api/channels`, `POST /api/channels` (`username`, `title`, `category_id`), `PATCH/DELETE /api/channels/{id}`  
- `GET /api/posts` — посты с пагинацией и фильтрами: `category_id`, `channel_id`, `from_date`, `to_date`, `search`, `page`, `page_size`  
- `GET /api/posts/{id}` — один пост  

Документация: http://localhost:8000/docs

## Документация и агенты

- **AGENTS.md** — инструкции для AI-агентов (сборка, конвенции). Поддерживается Cursor и другими инструментами ([agents.md](https://agents.md/)).
- **CLOUDE.md** — сводка по стеку, командам и переменным окружения.
- Оба файла можно пересобрать скриптом: `python scripts/build_docs.py`.
- Похожие решения на GitHub: [docs/RELATED_PROJECTS.md](docs/RELATED_PROJECTS.md).
- Правила Cursor для проекта: `.cursor/rules/` (Python/FastAPI, Telethon).

## Безопасность

- Файл сессии Telethon и `.env` не попадают в git (см. `.gitignore`).  
- Не публикуйте их и не выкладывайте контент каналов наружу — сервис рассчитан на личное использование.
