"""HTTP handler to shut down the Jupyter server."""

from tornado import ioloop, web

from jupyter_server.auth.decorator import authorized
from jupyter_server.base.handlers import JupyterHandler

AUTH_RESOURCE = "server"


class ShutdownHandler(JupyterHandler):
    """A shutdown API handler."""

    auth_resource = AUTH_RESOURCE

    @web.authenticated
    @authorized
    async def post(self):
        """Shut down the server."""
        pass


default_handlers = [
    (r"/api/shutdown", ShutdownHandler),
]
