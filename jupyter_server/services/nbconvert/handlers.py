"""API Handlers for nbconvert."""

import asyncio
import json

from anyio.to_thread import run_sync
from tornado import web

from jupyter_server.auth.decorator import authorized

from ...base.handlers import APIHandler

AUTH_RESOURCE = "nbconvert"


class NbconvertRootHandler(APIHandler):
    """The nbconvert root API handler."""

    auth_resource = AUTH_RESOURCE
    _exporter_lock: asyncio.Lock

    def initialize(self, **kwargs):
        """Initialize an nbconvert root handler."""
        pass

    @web.authenticated
    @authorized
    async def get(self):
        """Get the list of nbconvert exporters."""
        pass


default_handlers = [
    (r"/api/nbconvert", NbconvertRootHandler),
]
