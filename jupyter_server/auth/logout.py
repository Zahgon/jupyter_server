"""Tornado handlers for logging out of the Jupyter Server."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from ..base.handlers import JupyterHandler
from .decorator import allow_unauthenticated


class LogoutHandler(JupyterHandler):
    """An auth logout handler."""

    @allow_unauthenticated
    def get(self):
        """Handle a logout."""
        pass


default_handlers = [(r"/logout", LogoutHandler)]
