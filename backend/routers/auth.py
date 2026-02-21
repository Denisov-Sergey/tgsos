"""API for Telegram authorization flow inside web app."""
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from collector.fetcher import check_session_authorized, get_telegram_client, normalize_auth_error

router = APIRouter()
logger = logging.getLogger(__name__)

_SESSION_TTL_SECONDS = 10 * 60
_auth_lock = threading.Lock()
_auth_state: Optional["AuthState"] = None
_auth_last_error: Optional[str] = None
_auth_last_error_code: Optional[str] = None
_auth_last_error_hint: Optional[str] = None
_auth_last_updated_at: float = 0.0


@dataclass
class AuthState:
    phone: str
    phone_code_hash: str
    stage: str
    created_at: float
    expires_at: float
    client: Any
    delivery_type: Optional[str] = None
    next_delivery_type: Optional[str] = None
    delivery_timeout: Optional[int] = None


class StartAuthRequest(BaseModel):
    phone: str = Field(min_length=5, max_length=32, description="Phone in international format")


class VerifyCodeRequest(BaseModel):
    code: str = Field(min_length=3, max_length=10)


class VerifyPasswordRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


def _set_last_error(message: Optional[str], code: Optional[str], hint: Optional[str]) -> None:
    global _auth_last_error, _auth_last_error_code, _auth_last_error_hint, _auth_last_updated_at
    _auth_last_error = message
    _auth_last_error_code = code
    _auth_last_error_hint = hint
    _auth_last_updated_at = time.time()


def _clear_last_error() -> None:
    _set_last_error(None, None, None)


async def _disconnect_client_if_needed(client: Any) -> None:
    if client is None:
        return
    try:
        await client.disconnect()
    except Exception:
        logger.exception("Failed to disconnect Telegram client in auth flow")


def _is_expired(state: AuthState) -> bool:
    return time.time() >= state.expires_at


def _expires_in_seconds(state: Optional[AuthState]) -> Optional[int]:
    if state is None:
        return None
    return max(0, int(state.expires_at - time.time()))


def _sent_code_delivery_details(sent: Any) -> dict[str, Optional[Any]]:
    """Extract sent code routing details from Telethon response."""
    delivery_type = None
    next_delivery_type = None
    delivery_timeout = getattr(sent, "timeout", None)

    sent_type = getattr(sent, "type", None)
    if sent_type is not None:
        delivery_type = sent_type.__class__.__name__.replace("SentCodeType", "").lower()

    sent_next_type = getattr(sent, "next_type", None)
    if sent_next_type is not None:
        next_delivery_type = sent_next_type.__class__.__name__.replace("CodeType", "").lower()

    return {
        "delivery_type": delivery_type,
        "next_delivery_type": next_delivery_type,
        "delivery_timeout": delivery_timeout,
    }


@router.get("/telegram/status")
async def telegram_auth_status():
    global _auth_state
    with _auth_lock:
        state = _auth_state
        last_error = _auth_last_error
        last_error_code = _auth_last_error_code
        last_error_hint = _auth_last_error_hint
        last_updated = _auth_last_updated_at
    if state and _is_expired(state):
        await _disconnect_client_if_needed(state.client)
        with _auth_lock:
            _auth_state = None
            state = None
            _set_last_error(
                "Время ожидания кода истекло. Запросите код повторно.",
                "auth_session_expired",
                "Нажмите «Отправить код» снова.",
            )
            last_error = _auth_last_error
            last_error_code = _auth_last_error_code
            last_error_hint = _auth_last_error_hint
            last_updated = _auth_last_updated_at

    authorized, session_error, session_error_code, session_error_hint = await check_session_authorized()
    return {
        "authorized": authorized,
        "session_error": session_error,
        "session_error_code": session_error_code,
        "session_error_hint": session_error_hint,
        "flow_active": state is not None,
        "flow_stage": state.stage if state else None,
        "flow_expires_in": _expires_in_seconds(state),
        "delivery_type": state.delivery_type if state else None,
        "next_delivery_type": state.next_delivery_type if state else None,
        "delivery_timeout": state.delivery_timeout if state else None,
        "last_error": last_error,
        "last_error_code": last_error_code,
        "last_error_hint": last_error_hint,
        "last_updated_at": last_updated,
    }


@router.post("/telegram/start")
async def telegram_auth_start(payload: StartAuthRequest):
    global _auth_state
    phone = payload.phone.strip()
    if not phone.startswith("+"):
        raise HTTPException(status_code=400, detail="Номер должен начинаться с '+' и быть в международном формате.")

    with _auth_lock:
        prev_state = _auth_state
        _auth_state = None
    if prev_state:
        await _disconnect_client_if_needed(prev_state.client)

    _clear_last_error()
    client = await get_telegram_client()
    try:
        logger.info("Auth start requested for phone=%s", phone)
        await client.connect()
        if await client.is_user_authorized():
            await client.disconnect()
            return {"ok": True, "authorized": True, "message": "Сессия уже авторизована."}

        sent = await client.send_code_request(phone=phone)
        delivery = _sent_code_delivery_details(sent)
        state = AuthState(
            phone=phone,
            phone_code_hash=sent.phone_code_hash,
            stage="code_required",
            created_at=time.time(),
            expires_at=time.time() + _SESSION_TTL_SECONDS,
            client=client,
            delivery_type=delivery["delivery_type"],
            next_delivery_type=delivery["next_delivery_type"],
            delivery_timeout=delivery["delivery_timeout"],
        )
        with _auth_lock:
            _auth_state = state
        logger.warning(
            "Code sent for phone=%s delivery_type=%s next_delivery_type=%s timeout=%s",
            phone,
            state.delivery_type,
            state.next_delivery_type,
            state.delivery_timeout,
        )
        return {
            "ok": True,
            "authorized": False,
            "stage": "code_required",
            "message": "Код отправлен в Telegram.",
            "expires_in": _expires_in_seconds(state),
            "delivery_type": state.delivery_type,
            "next_delivery_type": state.next_delivery_type,
            "delivery_timeout": state.delivery_timeout,
        }
    except Exception as exc:
        await _disconnect_client_if_needed(client)
        diag = normalize_auth_error(exc)
        _set_last_error(diag["message"], diag["code"], diag["hint"])
        logger.exception("Auth start failed: code=%s", diag["code"])
        raise HTTPException(status_code=400, detail=f"{diag['message']} {diag['hint']}") from exc


@router.post("/telegram/verify")
async def telegram_auth_verify(payload: VerifyCodeRequest):
    global _auth_state
    with _auth_lock:
        state = _auth_state
    if state is None:
        raise HTTPException(status_code=400, detail="Нет активной авторизации. Сначала запросите код.")
    if _is_expired(state):
        await _disconnect_client_if_needed(state.client)
        with _auth_lock:
            _auth_state = None
        _set_last_error(
            "Время ожидания кода истекло.",
            "auth_session_expired",
            "Запросите код повторно.",
        )
        raise HTTPException(status_code=400, detail="Код истёк. Запросите новый.")

    try:
        logger.info("Verifying Telegram auth code")
        await state.client.sign_in(
            phone=state.phone,
            code=payload.code.strip(),
            phone_code_hash=state.phone_code_hash,
        )
        await _disconnect_client_if_needed(state.client)
        with _auth_lock:
            _auth_state = None
        _clear_last_error()
        return {"ok": True, "authorized": True, "message": "Telegram успешно авторизован."}
    except Exception as exc:
        diag = normalize_auth_error(exc)
        if diag["code"] == "password_required":
            with _auth_lock:
                if _auth_state:
                    _auth_state.stage = "password_required"
                    _auth_state.expires_at = time.time() + _SESSION_TTL_SECONDS
            _set_last_error(diag["message"], diag["code"], diag["hint"])
            return {
                "ok": True,
                "authorized": False,
                "stage": "password_required",
                "message": diag["message"],
                "hint": diag["hint"],
            }
        _set_last_error(diag["message"], diag["code"], diag["hint"])
        logger.exception("Auth verify failed: code=%s", diag["code"])
        raise HTTPException(status_code=400, detail=f"{diag['message']} {diag['hint']}") from exc


@router.post("/telegram/password")
async def telegram_auth_password(payload: VerifyPasswordRequest):
    global _auth_state
    with _auth_lock:
        state = _auth_state
    if state is None:
        raise HTTPException(status_code=400, detail="Нет активной авторизации. Сначала запросите код.")
    if state.stage != "password_required":
        raise HTTPException(status_code=400, detail="Сейчас не требуется пароль 2FA.")
    if _is_expired(state):
        await _disconnect_client_if_needed(state.client)
        with _auth_lock:
            _auth_state = None
        _set_last_error(
            "Время ожидания пароля истекло.",
            "auth_session_expired",
            "Запросите код повторно.",
        )
        raise HTTPException(status_code=400, detail="Сессия авторизации истекла. Запросите код заново.")

    try:
        logger.info("Verifying Telegram 2FA password")
        await state.client.sign_in(password=payload.password)
        await _disconnect_client_if_needed(state.client)
        with _auth_lock:
            _auth_state = None
        _clear_last_error()
        return {"ok": True, "authorized": True, "message": "Telegram успешно авторизован."}
    except Exception as exc:
        diag = normalize_auth_error(exc)
        _set_last_error(diag["message"], diag["code"], diag["hint"])
        logger.exception("Auth password verification failed: code=%s", diag["code"])
        raise HTTPException(status_code=400, detail=f"{diag['message']} {diag['hint']}") from exc


@router.post("/telegram/cancel")
async def telegram_auth_cancel():
    global _auth_state
    with _auth_lock:
        state = _auth_state
        _auth_state = None
    if state:
        await _disconnect_client_if_needed(state.client)
    _clear_last_error()
    return {"ok": True, "message": "Авторизация отменена."}
