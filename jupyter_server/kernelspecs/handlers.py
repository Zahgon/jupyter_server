"""Kernelspecs API Handlers."""

import mimetypes

from jupyter_core.utils import ensure_async
from tornado import web

from jupyter_server.auth.decorator import authorized

from ..base.handlers import JupyterHandler
from ..services.kernelspecs.handlers import kernel_name_regex

AUTH_RESOURCE = "kernelspecs"


class KernelSpecResourceHandler(web.StaticFileHandler, JupyterHandler):
    """A Kernelspec resource handler."""

    SUPPORTED_METHODS = ("GET", "HEAD")
    auth_resource = AUTH_RESOURCE

    def initialize(self) -> None:  # type: ignore[override]
        """Initialize a kernelspec resource handler."""
        pass

    @web.authenticated
    @authorized
    async def get(self, kernel_name: str, path: str, include_body: bool = True):  # type: ignore[override]
        """Get a kernelspec resource."""
        pass

    @web.authenticated
    @authorized
    async def head(self, kernel_name: str, path: str) -> None:  # type: ignore[override]
        """Get the head info for a kernel resource."""
        pass


default_handlers = [
    (r"/kernelspecs/%s/(?P<path>.*)" % kernel_name_regex, KernelSpecResourceHandler),
]
