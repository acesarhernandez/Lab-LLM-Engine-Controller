from __future__ import annotations

import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse

from llm_engine_server import __version__
from llm_engine_server.controller import (
    EngineConfigurationError,
    EngineController,
    WakeSendError,
    WakeTimeoutError,
)
from llm_engine_server.models import (
    EnsureReadyRequest,
    EnsureReadyResponse,
    HealthResponse,
    StatusResponse,
    WakeResponse,
)
from llm_engine_server.settings import Settings
from llm_engine_server.ui import render_dashboard_html


def create_app() -> FastAPI:
    settings = Settings.from_env()
    controller = EngineController(settings)

    app = FastAPI(
        title="LLM Engine Server",
        version=__version__,
        description=(
            "Wake-on-LAN and readiness control server for a single shared homelab "
            "LLM engine host."
        ),
    )
    app.state.settings = settings
    app.state.controller = controller

    @app.get("/", include_in_schema=False)
    async def dashboard() -> HTMLResponse:
        return HTMLResponse(render_dashboard_html(release_version=__version__))

    @app.get("/ui", include_in_schema=False)
    async def dashboard_alias() -> HTMLResponse:
        return HTMLResponse(render_dashboard_html(release_version=__version__))

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/v1/engine/status", response_model=StatusResponse, dependencies=[Depends(_require_api_key)])
    async def get_engine_status(request: Request, response: Response) -> StatusResponse:
        controller = _controller_from_request(request)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return StatusResponse(**controller.get_status().to_dict())

    @app.post("/v1/engine/wake", response_model=WakeResponse, dependencies=[Depends(_require_api_key)])
    async def wake_engine(request: Request) -> JSONResponse:
        controller = _controller_from_request(request)
        try:
            result = controller.wake()
        except EngineConfigurationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except WakeSendError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return JSONResponse(status_code=result.http_status_code, content=WakeResponse(**result.to_dict()).model_dump())

    @app.post(
        "/v1/engine/ensure-ready",
        response_model=EnsureReadyResponse,
        dependencies=[Depends(_require_api_key)],
    )
    async def ensure_engine_ready(
        request: Request,
        payload: EnsureReadyRequest | None = None,
    ) -> EnsureReadyResponse:
        controller = _controller_from_request(request)
        timeout_seconds = None if payload is None else payload.timeout_seconds
        try:
            result = controller.ensure_ready(timeout_seconds=timeout_seconds)
        except EngineConfigurationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except WakeSendError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except WakeTimeoutError as exc:
            raise HTTPException(
                status_code=504,
                detail={
                    "message": str(exc),
                    "waited_seconds": exc.waited_seconds,
                    "state": exc.status.state.value,
                },
            ) from exc

        return EnsureReadyResponse(**result.to_dict())

    return app


def _controller_from_request(request: Request) -> EngineController:
    return request.app.state.controller


def _require_api_key(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    expected = request.app.state.settings.api_key
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="ENGINE_API_KEY is not configured on this server.",
        )

    scheme, _, provided = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not provided:
        raise HTTPException(status_code=401, detail="Missing Bearer token.")

    if not secrets.compare_digest(expected, provided):
        raise HTTPException(status_code=401, detail="Invalid API key.")
