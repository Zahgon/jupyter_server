"""Tornado handlers for api specifications."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
import os
from typing import Any, cast

from jupyter_core.utils import ensure_async
from tornado import web

from jupyter_server._tz import isoformat, utcfromtimestamp
from jupyter_server.auth.decorator import authorized
from jupyter_server.auth.identity import IdentityProvider, UpdatableField

from ...base.handlers import APIHandler, JupyterHandler

AUTH_RESOURCE = "api"


class APISpecHandler(web.StaticFileHandler, JupyterHandler):
    """A spec handler for the REST API."""

    auth_resource = AUTH_RESOURCE

    def initialize(self):  # type: ignore[override]
        """Initialize the API spec handler."""
        pass

    @web.authenticated
    @authorized
    def head(self):  # type: ignore[override]
        pass

    @web.authenticated
    @authorized
    def get(self):  # type: ignore[override]
        """Get the API spec."""
        pass

    def get_content_type(self):
        """Get the content type."""
        pass


class APIStatusHandler(APIHandler):
    """An API status handler."""

    auth_resource = AUTH_RESOURCE
    _track_activity = False

    @web.authenticated
    @authorized
    async def get(self):
        """Get the API status."""
        pass


class IdentityHandler(APIHandler):
    """Get or patch the current user's identity model"""

    @web.authenticated
    async def get(self):
        """Get the identity model."""
        pass

    @web.authenticated
    async def patch(self):
        """Update user information."""
        pass


default_handlers = [
    (r"/api/spec.yaml", APISpecHandler),
    (r"/api/status", APIStatusHandler),
    (r"/api/me", IdentityHandler),
]
