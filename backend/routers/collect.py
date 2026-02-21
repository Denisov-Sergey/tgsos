"""API для запуска сборщика постов (кнопка в интерфейсе) и планировщик."""
import asyncio
import threading
import time
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

import config

router = APIRouter()

_collector_running = False
_collector_last_error: Optional[str] = None
_collector_thread: Optional[threading.Thread] = None
_scheduler_thread: Optional[threading.Thread] = None

_session_authorized: Optional[bool] = None
_session_error: Optional[str] = None
_session_error_code: Optional[str] = None
_session_error_hint: Optional[str] = None
_session_check_time: float = 0
_SESSION_CACHE_SECONDS = 60
_session_lock = threading.Lock()
_session_check_running = False


def _check_session_thread() -> None:
    global _session_authorized, _session_error, _session_error_code, _session_error_hint, _session_check_time, _session_check_running
    try:
        from collector.fetcher import check_session_authorized
        authorized, err, err_code, err_hint = asyncio.run(check_session_authorized())
        with _session_lock:
            _session_authorized = authorized
            _session_error = err
            _session_error_code = err_code
            _session_error_hint = err_hint
            _session_check_time = time.time()
    except Exception as e:
        with _session_lock:
            _session_authorized = False
            _session_error = str(e) or type(e).__name__
            _session_error_code = "status_check_failed"
            _session_error_hint = "Проверьте логи backend/collector и попробуйте ещё раз."
            _session_check_time = time.time()
    finally:
        _session_check_running = False


def _run_collector(limit: int) -> None:
    global _collector_running, _collector_last_error
    _collector_last_error = None
    try:
        from collector.fetcher import run_once
        asyncio.run(run_once(limit_per_channel=limit))
    except Exception as e:
        _collector_last_error = str(e) or type(e).__name__
    finally:
        _collector_running = False


@router.get("/status")
async def collect_status():
    """Статус сборщика: running, error, и статус сессии Telegram (session_authorized, session_error)."""
    global _session_check_running
    now = time.time()
    with _session_lock:
        need_check = (
            _session_authorized is None
            or (now - _session_check_time) > _SESSION_CACHE_SECONDS
        )
        if need_check and not _session_check_running:
            _session_check_running = True
            t = threading.Thread(target=_check_session_thread, daemon=True)
            t.start()
    with _session_lock:
        return {
            "running": _collector_running,
            "error": _collector_last_error,
            "session_authorized": _session_authorized,
            "session_error": _session_error,
            "session_error_code": _session_error_code,
            "session_error_hint": _session_error_hint,
        }


@router.post("/run")
async def collect_run(limit: int = Query(200, ge=1, le=5000, description="Лимит постов на канал")):
    """
    Запустить сбор постов в фоне. Возвращает сразу (202), сбор идёт асинхронно.
    Если сбор уже идёт — 409.
    """
    global _collector_running, _collector_thread
    if _collector_running:
        return JSONResponse(
            content={"started": False, "message": "Сбор уже запущен"},
            status_code=409,
        )
    _collector_last_error = None
    _collector_running = True
    _collector_thread = threading.Thread(target=_run_collector, args=(limit,), daemon=True)
    _collector_thread.start()
    return JSONResponse(
        content={"started": True, "message": "Сбор запущен"},
        status_code=202,
    )


def _scheduler_loop(interval_minutes: int, limit_per_run: int = 200) -> None:
    """В цикле раз в interval_minutes запускает сборщик."""
    global _collector_running
    while True:
        time.sleep(interval_minutes * 60)
        if _collector_running:
            continue
        _collector_running = True
        t = threading.Thread(target=_run_collector, args=(limit_per_run,), daemon=True)
        t.start()
        t.join()  # ждём окончания, чтобы не плодить потоки


def start_scheduler_if_enabled() -> None:
    """Запустить фоновый планировщик, если SCHEDULER_INTERVAL_MINUTES > 0."""
    global _scheduler_thread
    interval = getattr(config, "SCHEDULER_INTERVAL_MINUTES", 0) or 0
    if interval <= 0:
        return
    _scheduler_thread = threading.Thread(
        target=_scheduler_loop,
        args=(interval,),
        daemon=True,
    )
    _scheduler_thread.start()
