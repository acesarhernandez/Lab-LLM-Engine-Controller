from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Callable

from llm_engine_server.probes import EngineProber, SocketEngineProber
from llm_engine_server.settings import Settings
from llm_engine_server.wol import SocketWakeSender, WakeSender, mask_mac_address


class EngineState(StrEnum):
    OFFLINE = "offline"
    WAKING = "waking"
    PC_ONLINE = "pc_online"
    READY = "ready"
    MISCONFIGURED = "misconfigured"


class EngineConfigurationError(ValueError):
    """Raised when required engine configuration is missing or invalid."""


class WakeSendError(RuntimeError):
    """Raised when sending the WoL packet fails."""


class WakeTimeoutError(TimeoutError):
    def __init__(self, message: str, status: "EngineStatus", waited_seconds: int) -> None:
        super().__init__(message)
        self.status = status
        self.waited_seconds = waited_seconds


@dataclass(slots=True)
class EngineStatus:
    label: str
    state: EngineState
    pc_awake: bool
    ollama_ready: bool
    wake_in_progress: bool
    ready: bool
    wake_enabled: bool
    ollama_base_url: str
    pc_host: str
    pc_probe_port: int | None
    mac_masked: str | None
    last_wake_sent_at: str | None
    last_ready_at: str | None
    last_status_checked_at: str | None
    last_state_change_at: str | None
    cooldown_remaining_seconds: int
    last_error: str | None
    english_summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "state": self.state.value,
            "pc_awake": self.pc_awake,
            "ollama_ready": self.ollama_ready,
            "wake_in_progress": self.wake_in_progress,
            "ready": self.ready,
            "wake_enabled": self.wake_enabled,
            "ollama_base_url": self.ollama_base_url,
            "pc_host": self.pc_host,
            "pc_probe_port": self.pc_probe_port,
            "mac_masked": self.mac_masked,
            "last_wake_sent_at": self.last_wake_sent_at,
            "last_ready_at": self.last_ready_at,
            "last_status_checked_at": self.last_status_checked_at,
            "last_state_change_at": self.last_state_change_at,
            "cooldown_remaining_seconds": self.cooldown_remaining_seconds,
            "last_error": self.last_error,
            "english_summary": self.english_summary,
        }


@dataclass(slots=True)
class WakeResult:
    wake_sent: bool
    cooldown_applied: bool
    status: EngineStatus
    http_status_code: int
    english_summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "wake_sent": self.wake_sent,
            "cooldown_applied": self.cooldown_applied,
            "state": self.status.state.value,
            "pc_awake": self.status.pc_awake,
            "ollama_ready": self.status.ollama_ready,
            "wake_in_progress": self.status.wake_in_progress,
            "ready": self.status.ready,
            "english_summary": self.english_summary,
        }


@dataclass(slots=True)
class EnsureReadyResult:
    wake_sent: bool
    already_ready: bool
    waited_seconds: int
    status: EngineStatus
    english_summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "wake_sent": self.wake_sent,
            "already_ready": self.already_ready,
            "waited_seconds": self.waited_seconds,
            "state": self.status.state.value,
            "pc_awake": self.status.pc_awake,
            "ollama_ready": self.status.ollama_ready,
            "wake_in_progress": self.status.wake_in_progress,
            "ready": self.status.ready,
            "english_summary": self.english_summary,
        }


@dataclass(slots=True)
class _ControllerState:
    last_wake_sent_at: datetime | None = None
    last_ready_at: datetime | None = None
    last_status_checked_at: datetime | None = None
    last_state_change_at: datetime | None = None
    last_state: EngineState | None = None
    last_error: str | None = None
    cached_status: EngineStatus | None = None


class EngineController:
    def __init__(
        self,
        settings: Settings,
        *,
        prober: EngineProber | None = None,
        wake_sender: WakeSender | None = None,
        clock: Callable[[], datetime] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self._settings = settings
        self._prober = prober or SocketEngineProber()
        self._wake_sender = wake_sender or SocketWakeSender()
        self._clock = clock or _utcnow
        self._sleep = sleeper or time.sleep
        self._lock = threading.Lock()
        self._state = _ControllerState()

    def get_status(self, *, force_refresh: bool = False) -> EngineStatus:
        with self._lock:
            now = self._clock()
            if not force_refresh and self._is_cache_fresh_locked(now):
                return replace(self._state.cached_status)
            status = self._refresh_status_locked(now)
            return replace(status)

    def wake(self) -> WakeResult:
        with self._lock:
            now = self._clock()
            current = self._refresh_status_locked(now)

            if current.ready:
                return WakeResult(
                    wake_sent=False,
                    cooldown_applied=False,
                    status=current,
                    http_status_code=200,
                    english_summary=f"{self._settings.label} is already awake and Ollama is ready.",
                )

            if current.pc_awake:
                return WakeResult(
                    wake_sent=False,
                    cooldown_applied=False,
                    status=current,
                    http_status_code=200,
                    english_summary=f"{self._settings.label} is already awake. Ollama is not ready yet.",
                )

            if self._has_recent_wake_for_cooldown_locked(now):
                waiting_status = self._refresh_status_locked(now)
                return WakeResult(
                    wake_sent=False,
                    cooldown_applied=True,
                    status=waiting_status,
                    http_status_code=200,
                    english_summary=(
                        f"Wake already requested recently. Waiting for {self._settings.label} "
                        "to finish starting."
                    ),
                )

            self._ensure_wake_config_locked()

            try:
                self._wake_sender.send(
                    self._settings.wol_mac,
                    self._settings.wol_broadcast_ip,
                    self._settings.wol_port,
                )
            except Exception as exc:  # pragma: no cover - direct system error path
                self._state.last_error = f"Wake-on-LAN send failed: {exc}"
                raise WakeSendError(self._state.last_error) from exc

            self._state.last_wake_sent_at = now
            self._state.last_error = None
            status = self._refresh_status_locked(now)

            return WakeResult(
                wake_sent=True,
                cooldown_applied=False,
                status=status,
                http_status_code=202,
                english_summary=f"Wake signal sent to {self._settings.label}.",
            )

    def ensure_ready(self, timeout_seconds: int | None = None) -> EnsureReadyResult:
        timeout = timeout_seconds or self._settings.ready_timeout_seconds
        started_at = self._clock()
        current = self.get_status(force_refresh=True)

        if current.ready:
            return EnsureReadyResult(
                wake_sent=False,
                already_ready=True,
                waited_seconds=0,
                status=current,
                english_summary=f"{self._settings.label} is already awake and Ollama is ready.",
            )

        wake_result = self.wake()
        wake_sent = wake_result.wake_sent
        status = wake_result.status
        deadline = started_at + timedelta(seconds=timeout)

        while True:
            now = self._clock()
            if status.ready:
                waited_seconds = max(0, math.ceil((now - started_at).total_seconds()))
                return EnsureReadyResult(
                    wake_sent=wake_sent,
                    already_ready=False,
                    waited_seconds=waited_seconds,
                    status=status,
                    english_summary=f"{self._settings.label} is awake and Ollama is ready.",
                )

            if now >= deadline:
                waited_seconds = max(0, math.ceil((now - started_at).total_seconds()))
                with self._lock:
                    self._state.last_error = (
                        f"{self._settings.label} did not become ready within {timeout} seconds."
                    )
                    latest = self._refresh_status_locked(now)
                raise WakeTimeoutError(
                    self._state.last_error,
                    latest,
                    waited_seconds,
                )

            remaining_seconds = max(0.0, (deadline - now).total_seconds())
            sleep_seconds = min(self._settings.poll_interval_seconds, remaining_seconds)
            self._sleep(max(0.1, sleep_seconds))
            status = self.get_status(force_refresh=True)

    def _ensure_wake_config_locked(self) -> None:
        if not self._settings.wol_enabled:
            raise EngineConfigurationError("Wake-on-LAN is disabled on this server.")

        errors = self._settings.engine_validation_errors()
        if errors:
            raise EngineConfigurationError("; ".join(errors))

    def _is_cache_fresh_locked(self, now: datetime) -> bool:
        if self._state.cached_status is None or self._state.last_status_checked_at is None:
            return False

        age_seconds = (now - self._state.last_status_checked_at).total_seconds()
        ttl_seconds = self._cache_ttl_for_state_locked()
        return age_seconds <= ttl_seconds

    def _cache_ttl_for_state_locked(self) -> int:
        state = self._state.cached_status.state if self._state.cached_status else EngineState.OFFLINE
        if state == EngineState.READY:
            return self._settings.status_cache_seconds_ready
        if state in {EngineState.WAKING, EngineState.PC_ONLINE}:
            return self._settings.status_cache_seconds_waking
        return self._settings.status_cache_seconds_offline

    def _has_recent_wake_for_cooldown_locked(self, now: datetime) -> bool:
        if self._state.last_wake_sent_at is None:
            return False
        return (now - self._state.last_wake_sent_at).total_seconds() < self._settings.wake_cooldown_seconds

    def _has_recent_wake_for_grace_locked(self, now: datetime) -> bool:
        if self._state.last_wake_sent_at is None:
            return False
        return (now - self._state.last_wake_sent_at).total_seconds() < self._settings.effective_wake_grace_seconds

    def _refresh_status_locked(self, now: datetime) -> EngineStatus:
        pc_awake = False
        ollama_ready = False
        validation_errors = self._settings.engine_validation_errors()
        recent_wake_for_grace = self._has_recent_wake_for_grace_locked(now)

        if validation_errors:
            state = EngineState.MISCONFIGURED
            last_error = "; ".join(validation_errors)
            self._state.last_error = last_error
        else:
            pc_host = self._settings.resolved_pc_host
            if self._settings.pc_probe_port is not None and pc_host:
                pc_awake = self._prober.probe_host(
                    pc_host,
                    self._settings.pc_probe_port,
                    self._settings.pc_probe_timeout_seconds,
                )

            should_probe_ollama = pc_awake or self._settings.pc_probe_port is None
            if should_probe_ollama:
                ollama_ready = self._prober.probe_ollama(
                    self._settings.ollama_base_url,
                    self._settings.normalized_ready_path,
                    self._settings.ollama_timeout_seconds,
                )
                if self._settings.pc_probe_port is None and ollama_ready:
                    pc_awake = True

            if ollama_ready:
                state = EngineState.READY
                self._state.last_ready_at = now
                self._state.last_error = None
            elif pc_awake:
                state = EngineState.PC_ONLINE
            elif recent_wake_for_grace:
                state = EngineState.WAKING
            else:
                state = EngineState.OFFLINE

            last_error = self._state.last_error

        if state != self._state.last_state:
            self._state.last_state = state
            self._state.last_state_change_at = now

        self._state.last_status_checked_at = now

        status = EngineStatus(
            label=self._settings.label,
            state=state,
            pc_awake=pc_awake,
            ollama_ready=ollama_ready,
            wake_in_progress=recent_wake_for_grace and not ollama_ready,
            ready=ollama_ready,
            wake_enabled=self._settings.wol_enabled,
            ollama_base_url=self._settings.ollama_base_url,
            pc_host=self._settings.resolved_pc_host,
            pc_probe_port=self._settings.pc_probe_port,
            mac_masked=_masked_mac_or_none(self._settings.wol_mac),
            last_wake_sent_at=_format_dt(self._state.last_wake_sent_at),
            last_ready_at=_format_dt(self._state.last_ready_at),
            last_status_checked_at=_format_dt(self._state.last_status_checked_at),
            last_state_change_at=_format_dt(self._state.last_state_change_at),
            cooldown_remaining_seconds=self._cooldown_remaining_seconds_locked(now),
            last_error=last_error,
            english_summary=self._build_summary_locked(
                state,
                pc_awake,
                ollama_ready,
                recent_wake_for_grace,
                validation_errors,
            ),
        )

        self._state.cached_status = status
        return status

    def _cooldown_remaining_seconds_locked(self, now: datetime) -> int:
        if self._state.last_wake_sent_at is None:
            return 0
        elapsed_seconds = (now - self._state.last_wake_sent_at).total_seconds()
        remaining = self._settings.wake_cooldown_seconds - elapsed_seconds
        return max(0, math.ceil(remaining))

    def _build_summary_locked(
        self,
        state: EngineState,
        pc_awake: bool,
        ollama_ready: bool,
        recent_wake: bool,
        validation_errors: list[str],
    ) -> str:
        if state == EngineState.MISCONFIGURED:
            return f"Engine control is misconfigured: {'; '.join(validation_errors)}."
        if state == EngineState.READY:
            return f"{self._settings.label} is awake and Ollama is ready."
        if state == EngineState.PC_ONLINE:
            if recent_wake:
                return f"{self._settings.label} is awake, but Ollama is still starting."
            return f"{self._settings.label} is awake, but Ollama is not ready."
        if state == EngineState.WAKING:
            return f"{self._settings.label} is waking up."
        if not self._settings.wol_enabled:
            return f"{self._settings.label} appears to be offline. Wake-on-LAN is disabled."
        if not pc_awake and not ollama_ready:
            return f"{self._settings.label} appears to be offline."
        return f"{self._settings.label} is not ready."


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _format_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _masked_mac_or_none(mac_address: str) -> str | None:
    if not mac_address:
        return None
    try:
        return mask_mac_address(mac_address)
    except ValueError:
        return None
