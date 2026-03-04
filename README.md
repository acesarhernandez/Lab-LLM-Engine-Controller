# LLM Engine Server

This project is a small control-plane service for one shared homelab LLM host.

It does three things:

- sends Wake-on-LAN packets to the gaming PC
- checks whether the PC is awake
- checks whether Ollama is actually ready before other apps try to use it

It also includes a built-in browser dashboard for v1:

- live status polling
- manual wake button
- ensure-ready button
- a readable view of the raw engine signals

The point is to give all of your LLM-using apps one common contract instead of each app inventing its own wake logic.

## What The API Means

The service exposes these engine states:

- `offline`: the PC does not appear awake
- `waking`: a wake request was sent recently and the PC is still coming up
- `pc_online`: the PC is awake, but Ollama is not ready yet
- `ready`: Ollama is responding and the engine is safe to use
- `misconfigured`: required server settings are missing or invalid

Important rule:

- `GET /v1/engine/status` never sends a wake packet

That means your UI can poll status safely without accidentally waking the PC.

## Configuration

Copy `.env.example` to `.env` and set the real values.

Key settings:

- `ENGINE_API_KEY`: shared secret other apps must send as a Bearer token
- `ENGINE_PC_HOST`: the gaming PC host or IP
- `ENGINE_PC_PROBE_PORT`: a normal TCP port that proves the PC is awake
- `ENGINE_OLLAMA_BASE_URL`: the actual Ollama base URL
- `ENGINE_WOL_MAC`: MAC address for Wake-on-LAN

Why `ENGINE_PC_PROBE_PORT` matters:

- if the host probe works but Ollama does not, the service returns `pc_online`
- if Ollama works, the service returns `ready`

If you leave `ENGINE_PC_PROBE_PORT` blank or set it to `0`, the service skips the separate host probe and uses Ollama readiness only.

## Run Locally

If you are running directly from source without installing the package:

```bash
PYTHONPATH=src python3 -m llm_engine_server
```

If you install it into a virtual environment:

```bash
pip install -e .
python -m llm_engine_server
```

The server listens on `ENGINE_HOST:ENGINE_PORT` and defaults to `0.0.0.0:8088`.

## Built-In Dashboard

Open the root URL in your browser:

```text
http://localhost:8088/
```

Or:

```text
http://localhost:8088/ui
```

How it works:

- the dashboard is served by this same app
- it does not bypass API auth
- you paste your `ENGINE_API_KEY` into the page
- the page stores it only in your browser if you choose to remember it

What the dashboard does:

- polls `GET /v1/engine/status`
- triggers `POST /v1/engine/wake`
- triggers `POST /v1/engine/ensure-ready`

Important:

- polling the dashboard does not send wake packets by itself
- only the wake and ensure-ready buttons can trigger a wake

## Run With Docker

Build and start:

```bash
docker compose up --build -d
```

The included `docker-compose.yml` expects a local `.env` file.

## API

All non-health endpoints require:

```text
Authorization: Bearer <ENGINE_API_KEY>
```

### Health Check

```bash
curl http://localhost:8088/health
```

### Poll Live Status

```bash
curl \
  -H "Authorization: Bearer $ENGINE_API_KEY" \
  http://localhost:8088/v1/engine/status
```

This is the endpoint your UI should poll every 2 to 5 seconds while a relevant screen is open.

### Manual Wake

```bash
curl \
  -X POST \
  -H "Authorization: Bearer $ENGINE_API_KEY" \
  http://localhost:8088/v1/engine/wake
```

This sends a wake packet only if the cooldown allows it.

### Ensure Ready Before LLM Use

```bash
curl \
  -X POST \
  -H "Authorization: Bearer $ENGINE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"timeout_seconds":90}' \
  http://localhost:8088/v1/engine/ensure-ready
```

This is the endpoint backend apps should call immediately before an LLM operation.

It will:

1. check the current status
2. wake the PC if needed
3. wait until Ollama is ready or time out

## Intended Integration Pattern

Every app should use the same pattern:

- `GET /v1/engine/status` for live UI status
- `POST /v1/engine/wake` for a manual wake button
- `POST /v1/engine/ensure-ready` before backend LLM requests

That gives you one place to manage wake behavior, cooldowns, and readiness.

## Verification

This repo includes unit tests for:

- MAC normalization and magic packet building
- state transitions
- wake cooldown behavior
- cached status behavior
- `ensure-ready` success and timeout paths

Run them from this repo:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Notes About Dependencies

The runtime code uses the Python standard library for reachability checks so it can run on this machine without `httpx` installed.

The project file still leaves room for adding `httpx` and `pytest` as optional dev dependencies later if you want richer API tests.
