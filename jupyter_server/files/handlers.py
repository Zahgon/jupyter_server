"""Serve files directly from the ContentsManager."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import mimetypes
from base64 import decodebytes
from typing import TYPE_CHECKING

from jupyter_core.utils import ensure_async
from tornado import web

from jupyter_server.auth.decorator import authorized
from jupyter_server.base.handlers import JupyterHandler

if TYPE_CHECKING:
    from collections.abc import Awaitable

AUTH_RESOURCE = "contents"


class FilesHandler(JupyterHandler, web.StaticFileHandler):
    """serve files via ContentsManager

    Normally used when ContentsManager is not a FileContentsManager.

    FileContentsManager subclasses use AuthenticatedFilesHandler by default,
    a subclass of StaticFileHandler.
    """

    auth_resource = AUTH_RESOURCE

    @property
    def content_security_policy(self):
        """The content security policy."""
        pass

    @web.authenticated
    @authorized
    def head(self, path: str) -> Awaitable[None] | None:  # type:ignore[override]
        """The head response."""
        pass

    @web.authenticated
    @authorized
    async def get(self, path, include_body=True):  # type: ignore[override]
        """Get a file by path."""
        pass


default_handlers: list[JupyterHandler] = []
