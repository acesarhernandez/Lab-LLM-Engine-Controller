from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


EngineStateValue = Literal["offline", "waking", "pc_online", "ready", "misconfigured"]


class HealthResponse(BaseModel):
    status: str


class StatusResponse(BaseModel):
    label: str
    state: EngineStateValue
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


class WakeResponse(BaseModel):
    wake_sent: bool
    cooldown_applied: bool
    state: EngineStateValue
    pc_awake: bool
    ollama_ready: bool
    wake_in_progress: bool
    ready: bool
    english_summary: str


class EnsureReadyRequest(BaseModel):
    timeout_seconds: int | None = Field(default=None, ge=1, le=600)


class EnsureReadyResponse(BaseModel):
    wake_sent: bool
    already_ready: bool
    waited_seconds: int
    state: EngineStateValue
    pc_awake: bool
    ollama_ready: bool
    wake_in_progress: bool
    ready: bool
    english_summary: str

