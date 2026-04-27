"""A Websocket Handler for emitting Jupyter server events.

.. versionadded:: 2.0
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional, cast

from jupyter_core.utils import ensure_async
from tornado import web, websocket

from jupyter_server.auth.decorator import authorized, ws_authenticated
from jupyter_server.base.handlers import JupyterHandler

from ...base.handlers import APIHandler

AUTH_RESOURCE = "events"


if TYPE_CHECKING:
    import jupyter_events.logger


class SubscribeWebsocket(
    JupyterHandler,
    websocket.WebSocketHandler,
):
    """Websocket handler for subscribing to events"""

    auth_resource = AUTH_RESOURCE

    async def pre_get(self):
        """Handles authorization when
        attempting to subscribe to events emitted by
        Jupyter Server's eventbus.
        """
        pass

    @ws_authenticated
    async def get(self, *args, **kwargs):
        """Get an event socket."""
        pass

    async def event_listener(
        self, logger: jupyter_events.logger.EventLogger, schema_id: str, data: dict[str, Any]
    ) -> None:
        """Write an event message."""
        pass

    def open(self) -> None:  # type: ignore[override]
        """Routes events that are emitted by Jupyter Server's
        EventBus to a WebSocket client in the browser.
        """
        pass

    def on_close(self):
        """Handle a socket close."""
        pass


def validate_model(
    data: dict[str, Any], registry: jupyter_events.schema_registry.SchemaRegistry
) -> None:
    """Validates for required fields in the JSON request body and verifies that
    a registered schema/version exists"""
    pass


def get_timestamp(data: dict[str, Any]) -> Optional[datetime]:
    """Parses timestamp from the JSON request body"""
    pass


class EventHandler(APIHandler):
    """REST api handler for events"""

    auth_resource = AUTH_RESOURCE

    @web.authenticated
    @authorized
    async def post(self):
        """Emit an event."""
        pass


default_handlers = [
    (r"/api/events", EventHandler),
    (r"/api/events/subscribe", SubscribeWebsocket),
]
