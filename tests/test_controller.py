from __future__ import annotations

import asyncio
import os
import unittest
from datetime import UTC, datetime, timedelta

from llm_engine_server.app import create_app
from llm_engine_server.controller import EngineController, EngineState, WakeTimeoutError
from llm_engine_server.settings import Settings


class FakeClock:
    def __init__(self, start: datetime) -> None:
        self.current = start

    def now(self) -> datetime:
        return self.current

    def sleep(self, seconds: float) -> None:
        self.current += timedelta(seconds=seconds)

    def advance(self, seconds: float) -> None:
        self.current += timedelta(seconds=seconds)


class RecordingWakeSender:
    def __init__(self) -> None:
        self.calls = 0

    def send(self, mac_address: str, broadcast_ip: str, port: int) -> int:
        self.calls += 1
        return 102


class StaticProber:
    def __init__(self, *, host: bool = False, ollama: bool = False) -> None:
        self.host = host
        self.ollama = ollama
        self.host_calls = 0
        self.ollama_calls = 0

    def probe_host(self, host: str, port: int, timeout_seconds: float) -> bool:
        self.host_calls += 1
        return self.host

    def probe_ollama(self, base_url: str, ready_path: str, timeout_seconds: float) -> bool:
        self.ollama_calls += 1
        return self.ollama


class ThresholdProber:
    def __init__(self, clock: FakeClock, host_after_seconds: int, ollama_after_seconds: int) -> None:
        self.clock = clock
        self.start = clock.now()
        self.host_after_seconds = host_after_seconds
        self.ollama_after_seconds = ollama_after_seconds

    def probe_host(self, host: str, port: int, timeout_seconds: float) -> bool:
        elapsed = (self.clock.now() - self.start).total_seconds()
        return elapsed >= self.host_after_seconds

    def probe_ollama(self, base_url: str, ready_path: str, timeout_seconds: float) -> bool:
        elapsed = (self.clock.now() - self.start).total_seconds()
        return elapsed >= self.ollama_after_seconds


def build_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "api_key": "secret",
        "label": "Gaming PC",
        "pc_host": "192.168.1.50",
        "pc_probe_port": 3389,
        "ollama_base_url": "http://192.168.1.50:11434",
        "wol_enabled": True,
        "wol_mac": "AA:BB:CC:DD:EE:FF",
        "wake_cooldown_seconds": 20,
        "ready_timeout_seconds": 30,
        "status_cache_seconds_ready": 10,
        "status_cache_seconds_waking": 3,
        "status_cache_seconds_offline": 5,
        "poll_interval_seconds": 1.0,
    }
    defaults.update(overrides)
    return Settings(**defaults)


class EngineControllerTests(unittest.TestCase):
    def test_status_reports_offline_when_host_and_ollama_are_down(self) -> None:
        clock = FakeClock(datetime(2026, 3, 3, tzinfo=UTC))
        prober = StaticProber(host=False, ollama=False)
        sender = RecordingWakeSender()
        controller = EngineController(
            build_settings(),
            prober=prober,
            wake_sender=sender,
            clock=clock.now,
            sleeper=clock.sleep,
        )

        status = controller.get_status(force_refresh=True)

        self.assertEqual(status.state, EngineState.OFFLINE)
        self.assertFalse(status.ready)
        self.assertEqual(sender.calls, 0)

    def test_wake_applies_cooldown_and_does_not_send_twice(self) -> None:
        clock = FakeClock(datetime(2026, 3, 3, tzinfo=UTC))
        prober = StaticProber(host=False, ollama=False)
        sender = RecordingWakeSender()
        controller = EngineController(
            build_settings(),
            prober=prober,
            wake_sender=sender,
            clock=clock.now,
            sleeper=clock.sleep,
        )

        first = controller.wake()
        second = controller.wake()

        self.assertTrue(first.wake_sent)
        self.assertEqual(first.status.state, EngineState.WAKING)
        self.assertFalse(second.wake_sent)
        self.assertTrue(second.cooldown_applied)
        self.assertEqual(sender.calls, 1)

    def test_ready_status_uses_cache(self) -> None:
        clock = FakeClock(datetime(2026, 3, 3, tzinfo=UTC))
        prober = StaticProber(host=True, ollama=True)
        controller = EngineController(
            build_settings(),
            prober=prober,
            wake_sender=RecordingWakeSender(),
            clock=clock.now,
            sleeper=clock.sleep,
        )

        first = controller.get_status(force_refresh=True)
        clock.advance(5)
        second = controller.get_status()

        self.assertEqual(first.state, EngineState.READY)
        self.assertEqual(second.state, EngineState.READY)
        self.assertEqual(prober.host_calls, 1)
        self.assertEqual(prober.ollama_calls, 1)

    def test_wake_does_not_fail_when_pc_is_already_awake_and_wol_is_disabled(self) -> None:
        clock = FakeClock(datetime(2026, 3, 3, tzinfo=UTC))
        prober = StaticProber(host=True, ollama=False)
        sender = RecordingWakeSender()
        controller = EngineController(
            build_settings(wol_enabled=False, wol_mac=""),
            prober=prober,
            wake_sender=sender,
            clock=clock.now,
            sleeper=clock.sleep,
        )

        result = controller.wake()

        self.assertFalse(result.wake_sent)
        self.assertEqual(result.http_status_code, 200)
        self.assertEqual(result.status.state, EngineState.PC_ONLINE)
        self.assertEqual(sender.calls, 0)

    def test_ensure_ready_waits_until_ollama_is_ready(self) -> None:
        clock = FakeClock(datetime(2026, 3, 3, tzinfo=UTC))
        prober = ThresholdProber(clock, host_after_seconds=2, ollama_after_seconds=4)
        sender = RecordingWakeSender()
        controller = EngineController(
            build_settings(),
            prober=prober,
            wake_sender=sender,
            clock=clock.now,
            sleeper=clock.sleep,
        )

        result = controller.ensure_ready(timeout_seconds=10)

        self.assertTrue(result.wake_sent)
        self.assertFalse(result.already_ready)
        self.assertTrue(result.status.ready)
        self.assertEqual(result.status.state, EngineState.READY)
        self.assertEqual(result.waited_seconds, 4)
        self.assertEqual(sender.calls, 1)

    def test_ensure_ready_times_out_when_engine_never_comes_online(self) -> None:
        clock = FakeClock(datetime(2026, 3, 3, tzinfo=UTC))
        prober = ThresholdProber(clock, host_after_seconds=50, ollama_after_seconds=50)
        sender = RecordingWakeSender()
        controller = EngineController(
            build_settings(ready_timeout_seconds=3),
            prober=prober,
            wake_sender=sender,
            clock=clock.now,
            sleeper=clock.sleep,
        )

        with self.assertRaises(WakeTimeoutError) as ctx:
            controller.ensure_ready(timeout_seconds=3)

        self.assertEqual(ctx.exception.status.state, EngineState.WAKING)
        self.assertEqual(ctx.exception.waited_seconds, 3)
        self.assertEqual(sender.calls, 1)

    def test_status_endpoint_sets_no_cache_headers(self) -> None:
        os_environ_backup = dict(os.environ)
        try:
            os.environ["ENGINE_API_KEY"] = "test-key"
            app = create_app()
            route = next(route for route in app.routes if getattr(route, "path", "") == "/v1/engine/status")

            class DummyAppState:
                settings = type("S", (), {"api_key": "test-key"})()
                controller = EngineController(build_settings())

            class DummyRequest:
                app = type("A", (), {"state": DummyAppState()})()

            class DummyResponse:
                headers = {}

            # This keeps the test lightweight without requiring httpx/starlette test client.
            result = asyncio.run(route.endpoint(DummyRequest(), DummyResponse()))
            self.assertIn("state", result.model_dump())
            self.assertEqual(
                DummyResponse.headers.get("Cache-Control"),
                "no-store, no-cache, must-revalidate, max-age=0",
            )
        finally:
            os.environ.clear()
            os.environ.update(os_environ_backup)


if __name__ == "__main__":
    unittest.main()
