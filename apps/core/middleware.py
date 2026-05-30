"""Her istekte aktif kullanıcıyı/IP'yi denetim bağlamına yazar, sonunda temizler."""

from __future__ import annotations

from .audit import clear_actor, set_actor


def _client_ip(request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_actor(getattr(request, "user", None), _client_ip(request))
        try:
            return self.get_response(request)
        finally:
            clear_actor()
