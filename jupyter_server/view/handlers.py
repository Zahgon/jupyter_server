"""Tornado handlers for viewing HTML files."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from jupyter_core.utils import ensure_async
from tornado import web

from jupyter_server.auth.decorator import authorized

from ..base.handlers import JupyterHandler, path_regex
from ..utils import url_escape, url_path_join

AUTH_RESOURCE = "contents"


class ViewHandler(JupyterHandler):
    """Render HTML files within an iframe."""

    auth_resource = AUTH_RESOURCE

    @web.authenticated
    @authorized
    async def get(self, path):
        """Get a view on a given path."""
        pass


default_handlers = [
    (r"/view%s" % path_regex, ViewHandler),
]
