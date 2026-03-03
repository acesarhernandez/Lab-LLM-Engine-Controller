from __future__ import annotations

import socket
from typing import Protocol
from urllib import error, request


class EngineProber(Protocol):
    def probe_host(self, host: str, port: int, timeout_seconds: float) -> bool:
        ...

    def probe_ollama(self, base_url: str, ready_path: str, timeout_seconds: float) -> bool:
        ...


def _build_ready_url(base_url: str, ready_path: str) -> str:
    return f"{base_url.rstrip('/')}/{ready_path.lstrip('/')}"


class SocketEngineProber:
    def probe_host(self, host: str, port: int, timeout_seconds: float) -> bool:
        try:
            with socket.create_connection((host, int(port)), timeout=timeout_seconds):
                return True
        except OSError:
            return False

    def probe_ollama(self, base_url: str, ready_path: str, timeout_seconds: float) -> bool:
        url = _build_ready_url(base_url, ready_path)
        req = request.Request(url=url, method="GET")
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:
                return 200 <= getattr(response, "status", 0) < 300
        except error.HTTPError as exc:
            return 200 <= exc.code < 300
        except (error.URLError, TimeoutError, OSError):
            return False

