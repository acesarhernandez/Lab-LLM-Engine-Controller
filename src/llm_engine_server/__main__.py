from __future__ import annotations

import uvicorn

from llm_engine_server.settings import Settings


def main() -> None:
    settings = Settings.from_env()
    uvicorn.run(
        "llm_engine_server.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )


if __name__ == "__main__":
    main()

