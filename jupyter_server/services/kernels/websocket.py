"""Tornado handlers for WebSocket <-> ZMQ sockets."""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from jupyter_core.utils import ensure_async
from tornado import web
from tornado.websocket import WebSocketHandler

from jupyter_server.auth.decorator import ws_authenticated
from jupyter_server.base.handlers import JupyterHandler
from jupyter_server.base.websocket import WebSocketMixin

AUTH_RESOURCE = "kernels"


class KernelWebsocketHandler(WebSocketMixin, WebSocketHandler, JupyterHandler):
    """The kernels websocket should connect"""

    auth_resource = AUTH_RESOURCE

    @property
    def kernel_websocket_connection_class(self):
        """The kernel websocket connection class."""
        return self.settings.get("kernel_websocket_connection_class")

    def set_default_headers(self):
        """Undo the set_default_headers in JupyterHandler

        which doesn't make sense for websockets
        """

    def get_compression_options(self):
        """Get the socket connection options."""
        pass

    async def pre_get(self):
        """Handle a pre_get."""
        pass

    @ws_authenticated
    async def get(self, kernel_id):
        """Handle a get request for a kernel."""
        pass

    async def open(self, kernel_id):  # type: ignore[override]
        """Open a kernel websocket."""
        pass

    def on_message(self, ws_message):
        """Get a kernel message from the websocket and turn it into a ZMQ message."""
        pass

    def on_close(self):
        """Handle a socket closure."""
        pass

    def select_subprotocol(self, subprotocols):
        """Select the sub protocol for the socket."""
        pass
