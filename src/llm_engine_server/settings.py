from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from llm_engine_server.wol import normalize_mac_address


def load_dotenv_file(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        # Support simple quoted values such as ENGINE_LABEL="Gaming PC".
        if value and (value[0] == value[-1]) and value[0] in {'"', "'"}:
            try:
                parsed = shlex.split(value)
                value = parsed[0] if parsed else ""
            except ValueError:
                value = value[1:-1]

        os.environ.setdefault(key, value)


def _env_str(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw.strip())


@dataclass(slots=True, frozen=True)
class Settings:
    api_key: str = ""
    host: str = "0.0.0.0"
    port: int = 8088
    label: str = "Gaming PC"
    pc_host: str = ""
    pc_probe_port: int | None = 3389
    pc_probe_timeout_seconds: float = 1.0
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_ready_path: str = "/api/tags"
    ollama_timeout_seconds: float = 1.5
    wol_enabled: bool = True
    wol_mac: str = ""
    wol_broadcast_ip: str = "255.255.255.255"
    wol_port: int = 9
    wake_cooldown_seconds: int = 20
    wake_grace_seconds: int = 90
    ready_timeout_seconds: int = 90
    status_cache_seconds_ready: int = 10
    status_cache_seconds_waking: int = 3
    status_cache_seconds_offline: int = 5
    poll_interval_seconds: float = 2.0

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv_file()

        raw_probe_port = os.environ.get("ENGINE_PC_PROBE_PORT")
        if raw_probe_port is None:
            probe_port = 3389
        elif raw_probe_port.strip() == "":
            probe_port = None
        else:
            parsed_probe_port = int(raw_probe_port.strip())
            probe_port = parsed_probe_port if parsed_probe_port > 0 else None

        return cls(
            api_key=_env_str("ENGINE_API_KEY"),
            host=_env_str("ENGINE_HOST", "0.0.0.0"),
            port=_env_int("ENGINE_PORT", 8088),
            label=_env_str("ENGINE_LABEL", "Gaming PC") or "Gaming PC",
            pc_host=_env_str("ENGINE_PC_HOST"),
            pc_probe_port=probe_port,
            ollama_base_url=_env_str("ENGINE_OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            ollama_ready_path=_env_str("ENGINE_OLLAMA_READY_PATH", "/api/tags") or "/api/tags",
            wol_enabled=_env_bool("ENGINE_WOL_ENABLED", True),
            wol_mac=_env_str("ENGINE_WOL_MAC"),
            wol_broadcast_ip=_env_str("ENGINE_WOL_BROADCAST_IP", "255.255.255.255"),
            wol_port=_env_int("ENGINE_WOL_PORT", 9),
            wake_cooldown_seconds=_env_int("ENGINE_WAKE_COOLDOWN_SECONDS", 20),
            wake_grace_seconds=_env_int("ENGINE_WAKE_GRACE_SECONDS", 90),
            ready_timeout_seconds=_env_int("ENGINE_READY_TIMEOUT_SECONDS", 90),
            status_cache_seconds_ready=_env_int("ENGINE_STATUS_CACHE_SECONDS_READY", 10),
            status_cache_seconds_waking=_env_int("ENGINE_STATUS_CACHE_SECONDS_WAKING", 3),
            status_cache_seconds_offline=_env_int("ENGINE_STATUS_CACHE_SECONDS_OFFLINE", 5),
        )

    @property
    def resolved_pc_host(self) -> str:
        if self.pc_host:
            return self.pc_host
        parsed = urlparse(self.ollama_base_url)
        return parsed.hostname or ""

    @property
    def normalized_ready_path(self) -> str:
        path = self.ollama_ready_path.strip() or "/api/tags"
        if not path.startswith("/"):
            return f"/{path}"
        return path

    def engine_validation_errors(self) -> list[str]:
        errors: list[str] = []

        parsed = urlparse(self.ollama_base_url)
        if not parsed.scheme or not parsed.hostname:
            errors.append("ENGINE_OLLAMA_BASE_URL must be a valid http or https URL")

        if self.pc_probe_port is not None and self.pc_probe_port <= 0:
            errors.append("ENGINE_PC_PROBE_PORT must be blank, 0, or a positive integer")

        if self.wol_port <= 0:
            errors.append("ENGINE_WOL_PORT must be a positive integer")

        if self.wake_cooldown_seconds < 0:
            errors.append("ENGINE_WAKE_COOLDOWN_SECONDS must be zero or greater")

        if self.wake_grace_seconds < 0:
            errors.append("ENGINE_WAKE_GRACE_SECONDS must be zero or greater")

        if self.ready_timeout_seconds <= 0:
            errors.append("ENGINE_READY_TIMEOUT_SECONDS must be a positive integer")

        if self.status_cache_seconds_ready < 0:
            errors.append("ENGINE_STATUS_CACHE_SECONDS_READY must be zero or greater")

        if self.status_cache_seconds_waking < 0:
            errors.append("ENGINE_STATUS_CACHE_SECONDS_WAKING must be zero or greater")

        if self.status_cache_seconds_offline < 0:
            errors.append("ENGINE_STATUS_CACHE_SECONDS_OFFLINE must be zero or greater")

        if self.wol_enabled:
            if not self.wol_mac:
                errors.append("ENGINE_WOL_MAC must be set when ENGINE_WOL_ENABLED=true")
            else:
                try:
                    normalize_mac_address(self.wol_mac)
                except ValueError as exc:
                    errors.append(f"ENGINE_WOL_MAC is invalid: {exc}")

        return errors

    @property
    def effective_wake_grace_seconds(self) -> int:
        # Wake status should not flip back to offline before resend cooldown expires.
        return max(self.wake_grace_seconds, self.wake_cooldown_seconds)
