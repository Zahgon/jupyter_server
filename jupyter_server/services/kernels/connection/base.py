"""Kernel connection helpers."""

import json
import struct
from typing import Any

from jupyter_client.session import Session
from tornado.websocket import WebSocketHandler
from traitlets import Float, Instance, Unicode, default
from traitlets.config import LoggingConfigurable

try:
    from jupyter_client.jsonutil import json_default
except ImportError:
    from jupyter_client.jsonutil import date_default as json_default

from jupyter_client.jsonutil import extract_dates

from jupyter_server.transutils import _i18n

from .abc import KernelWebsocketConnectionABC


def serialize_binary_message(msg):
    """serialize a message as a binary blob

    Header:

    4 bytes: number of msg parts (nbufs) as 32b int
    4 * nbufs bytes: offset for each buffer as integer as 32b int

    Offsets are from the start of the buffer, including the header.

    Returns
    -------
    The message serialized to bytes.

    """
    pass


def deserialize_binary_message(bmsg):
    """deserialize a message from a binary blog

    Header:

    4 bytes: number of msg parts (nbufs) as 32b int
    4 * nbufs bytes: offset for each buffer as integer as 32b int

    Offsets are from the start of the buffer, including the header.

    Returns
    -------
    message dictionary
    """
    pass


def serialize_msg_to_ws_v1(msg_or_list, channel, pack=None):
    """Serialize a message using the v1 protocol."""
    pass


def deserialize_msg_from_ws_v1(ws_msg):
    """Deserialize a message using the v1 protocol."""
    pass


class BaseKernelWebsocketConnection(LoggingConfigurable):
    """A configurable base class for connecting Kernel WebSockets to ZMQ sockets."""

    kernel_ws_protocol = Unicode(
        None,
        allow_none=True,
        config=True,
        help=_i18n(
            "Preferred kernel message protocol over websocket to use (default: None). "
            "If an empty string is passed, select the legacy protocol. If None, "
            "the selected protocol will depend on what the front-end supports "
            "(usually the most recent protocol supported by the back-end and the "
            "front-end)."
        ),
    )

    @property
    def kernel_manager(self):
        """The kernel manager."""
        pass

    @property
    def multi_kernel_manager(self):
        """The multi kernel manager."""
        pass

    @property
    def kernel_id(self):
        """The kernel id."""
        pass

    @property
    def session_id(self):
        """The session id."""
        pass

    kernel_info_timeout = Float()

    @default("kernel_info_timeout")
    def _default_kernel_info_timeout(self):
        pass

    session = Instance(klass=Session, config=True)

    @default("session")
    def _default_session(self):
        pass

    websocket_handler = Instance(WebSocketHandler)

    async def connect(self):
        """Handle a connect."""
        pass

    async def disconnect(self):
        """Handle a disconnect."""
        pass

    def handle_incoming_message(self, incoming_msg: str) -> None:
        """Handle an incoming message."""
        pass

    def handle_outgoing_message(self, stream: str, outgoing_msg: list[Any]) -> None:
        """Handle an outgoing message."""
        pass


KernelWebsocketConnectionABC.register(BaseKernelWebsocketConnection)
