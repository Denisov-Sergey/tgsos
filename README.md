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

Веб-интерфейс: http://localhost:8000. Чтобы использовать другой порт (например 3000), задайте в `.env`: `PORT=3000`, перезапустите контейнеры (`docker compose up -d`).

Данные (БД и сессия Telethon) хранятся в volume `tgsos_data`. В Docker по умолчанию используются пути `/data/tgsos.db` и `/data/telethon_session` — при необходимости задайте в `.env`:

- `DATABASE_URL=sqlite+aiosqlite:////data/tgsos.db`
- `TELEGRAM_SESSION_PATH=/data/telethon_session`

**Первый вход в Telegram (сессия для сборщика):**

Сессия создаётся при первом запуске сборщика. Есть два способа:

1. **Через интерфейс приложения (рекомендуется):**
   - Откройте вкладку **Каналы**.
   - В блоке **Авторизация Telegram** введите номер телефона и нажмите **«Отправить код»**.
   - Введите код из Telegram. Если включен 2FA-пароль, введите его на следующем шаге.

2. **Через контейнер collector (интерактивно):**
   - Запустите контейнер сборщика **интерактивно** (чтобы ввести номер телефона и код):

```bash
docker compose run --rm -it collector
```

**Код для входа приходит только в приложение Telegram** (на телефон или другой уже авторизованный клиент), не по SMS. Откройте Telegram и проверьте уведомление или чат «Telegram» с кодом.

После сохранения сессии в volume дальнейшие запуски можно делать без интерактива.

### Диагностика проблем с авторизацией Telegram

Если код не приходит или вход не завершается:

1. Проверьте статус в UI:
   - На вкладке **Каналы** строка `Telegram: ...` показывает состояние сессии.
   - При ошибке отображается причина (`invalid_api_credentials`, `flood_wait`, `password_required`, `invalid_code`, и т.д.).

2. Проверьте `.env`:
   - `API_ID` и `API_HASH` должны быть реальными значениями с `my.telegram.org`.
   - Для Docker используйте:
     - `TELEGRAM_SESSION_PATH=/data/telethon_session`
     - `DATABASE_URL=sqlite+aiosqlite:////data/tgsos.db`

3. Проверьте логи:

```bash
docker compose logs -f app
docker compose logs -f collector
```

4. Частые причины:
   - **Код не приходит**: он приходит только в приложение Telegram (сервисный чат Telegram), не по SMS.
   - **`flood_wait`**: Telegram временно ограничил попытки; подождите и попробуйте позже.
   - **`password_required`**: у аккаунта включён 2FA; после кода нужно ввести пароль.
   - **`invalid_api_credentials`**: неверные `API_ID`/`API_HASH`.

**Способы запуска сборщика:**

1. **Кнопка в интерфейсе** — на вкладке **Каналы** нажмите **«Запустить сбор постов»** (можно задать лимит постов на канал). Сбор пойдёт в фоне, статус отобразится на странице.
2. **Встроенный планировщик** — в `.env` задайте `SCHEDULER_INTERVAL_MINUTES=30` (или другое число минут). Контейнер app будет автоматически запускать сбор каждые N минут. Кнопка и планировщик рассчитаны на один процесс (не запускайте uvicorn с `--workers 2+`).
3. **Cron (Linux/macOS)** — добавьте в crontab (`crontab -e`):
   ```cron
   */15 * * * * cd /path/to/tgsos && docker compose run --rm collector
   ```
   (каждые 15 минут; укажите свой путь к проекту.)
4. **Task Scheduler (Windows)** — создайте задачу, которая по расписанию выполняет:
   ```bat
   cd x:\Git\tgsos && docker compose run --rm collector
   ```
5. **Вручную из консоли:**
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
- `GET /api/collect/status` — идёт ли сбор  
- `POST /api/collect/run?limit=200` — запустить сбор в фоне (202 = запущен, 409 = уже идёт)  

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
