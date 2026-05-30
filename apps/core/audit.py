"""
İstek (request) bağlamındaki aktif kullanıcıyı ve IP'yi thread-local'de tutar.

Bu sayede model katmanı (BaseModel.save/delete) hangi kullanıcının işlem yaptığını
bilir ve `created_by` / `updated_by` ile AuditLog'u otomatik doldurabilir.
"""

from __future__ import annotations

import threading

_state = threading.local()


def set_actor(user, ip: str | None = None) -> None:
    _state.user = user if (user and getattr(user, "is_authenticated", False)) else None
    _state.ip = ip


def clear_actor() -> None:
    _state.user = None
    _state.ip = None


def get_actor():
    return getattr(_state, "user", None)


def get_ip() -> str | None:
    return getattr(_state, "ip", None)
