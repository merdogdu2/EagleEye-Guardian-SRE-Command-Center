# Copyright 2026 EagleEye Guardian Contributors
# SPDX-License-Identifier: Apache-2.0

"""Production FastAPI + A2A v0.3 + A2UI v0.9 server entrypoint for EagleEye Guardian."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.a2ui.a2a_bridge import install_a2a_bridge

install_a2a_bridge()

A2UI_EXTENSION_URI = "https://a2ui.org/a2a-extension/a2ui/v0.9"
AGENTS_DIR = str(Path(__file__).resolve().parents[1])


class A2uiAndStreamingMiddleware:
    """Echo X-A2A-Extensions for A2UI v0.9 negotiation and disable proxy buffering on SSE."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        req_headers = {
            k.decode("latin1").lower(): v.decode("latin1")
            for k, v in scope.get("headers", [])
        }
        requested_ext = req_headers.get("x-a2a-extensions", "")
        echo_a2ui = A2UI_EXTENSION_URI in requested_ext or scope.get("path", "").startswith("/a2a")

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                header_names = {k.lower() for k, _ in headers}
                if echo_a2ui and b"x-a2a-extensions" not in header_names:
                    headers.append((b"x-a2a-extensions", A2UI_EXTENSION_URI.encode("latin1")))

                content_type = next(
                    (v for k, v in headers if k.lower() == b"content-type"),
                    b"",
                )
                if b"text/event-stream" in content_type:
                    if b"x-accel-buffering" not in header_names:
                        headers.append((b"x-accel-buffering", b"no"))
                    if b"cache-control" not in header_names:
                        headers.append((b"cache-control", b"no-cache, no-transform"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


def create_server_app(**kwargs: Any) -> FastAPI:
    """Create the ADK FastAPI application with A2A (/a2a/app) and A2UI v0.9 middleware enabled."""
    install_a2a_bridge()
    fast_api_app = get_fast_api_app(
        agents_dir=AGENTS_DIR,
        web=True,
        a2a=True,
        use_local_storage=False,
        allow_origins=["*"],
        **kwargs,
    )
    fast_api_app.add_middleware(A2uiAndStreamingMiddleware)
    return fast_api_app


app: FastAPI = create_server_app()
