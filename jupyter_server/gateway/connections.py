"""Gateway connection classes."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, cast

import tornado.websocket as tornado_websocket
from tornado.concurrent import Future
from tornado.escape import json_decode, url_escape, utf8
from tornado.httpclient import HTTPRequest
from tornado.ioloop import IOLoop
from traitlets import Bool, Instance, Int, Unicode

from ..services.kernels.connection.base import BaseKernelWebsocketConnection
from ..utils import url_path_join
from .gateway_client import GatewayClient


class GatewayWebSocketConnection(BaseKernelWebsocketConnection):
    """Web socket connection that proxies to a kernel/enterprise gateway."""

    ws = Instance(klass=tornado_websocket.WebSocketClientConnection, allow_none=True)

    ws_future = Instance(klass=Future, allow_none=True)

    disconnected = Bool(False)

    retry = Int(0)

    # When opening ws connection to gateway, server already negotiated subprotocol with notebook client.
    # Same protocol must be used for client and gateway, so legacy ws subprotocol for client is enforced here.

    kernel_ws_protocol = Unicode("", allow_none=True, config=True)

    async def connect(self):
        """Connect to the socket."""
        pass

    def _connection_done(self, fut):
        """Handle a finished connection."""
        pass

    def disconnect(self):
        """Handle a disconnect."""
        pass

    async def _read_messages(self):
        """Read messages from gateway server."""
        pass

    def handle_outgoing_message(self, incoming_msg: str, *args: Any) -> None:
        """Send message to the notebook client."""
        pass

    def handle_incoming_message(self, message: str) -> None:
        """Send message to gateway server."""
        pass

    def _write_message(self, message):
        """Send message to gateway server."""
        pass

    @staticmethod
    def _get_message_summary(message):
        """Get a summary of a message."""
        pass
