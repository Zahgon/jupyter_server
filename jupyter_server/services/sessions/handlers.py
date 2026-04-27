"""Tornado handlers for the sessions web service.

Preliminary documentation at https://github.com/ipython/ipython/wiki/IPEP-16%3A-Notebook-multi-directory-dashboard-and-URL-mapping#sessions-api
"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import asyncio
import json

try:
    from jupyter_client.jsonutil import json_default
except ImportError:
    from jupyter_client.jsonutil import date_default as json_default

from jupyter_client.kernelspec import NoSuchKernel
from jupyter_core.utils import ensure_async
from tornado import web

from jupyter_server.auth.decorator import authorized
from jupyter_server.utils import url_path_join

from ...base.handlers import APIHandler

AUTH_RESOURCE = "sessions"


class SessionsAPIHandler(APIHandler):
    """A Sessions API handler."""

    auth_resource = AUTH_RESOURCE


class SessionRootHandler(SessionsAPIHandler):
    """A Session Root API handler."""

    @web.authenticated
    @authorized
    async def get(self):
        """Get a list of running sessions."""
        pass

    @web.authenticated
    @authorized
    async def post(self):
        """Create a new session."""
        pass


class SessionHandler(SessionsAPIHandler):
    """A handler for a single session."""

    @web.authenticated
    @authorized
    async def get(self, session_id):
        """Get the JSON model for a single session."""
        pass

    @web.authenticated
    @authorized
    async def patch(self, session_id):
        """Patch updates sessions:

        - path updates session to track renamed paths
        - kernel.name starts a new kernel with a given kernelspec
        """
        pass

    @web.authenticated
    @authorized
    async def delete(self, session_id):
        """Delete the session with given session_id."""
        pass


# -----------------------------------------------------------------------------
# URL to handler mappings
# -----------------------------------------------------------------------------

_session_id_regex = r"(?P<session_id>\w+-\w+-\w+-\w+-\w+)"

default_handlers = [
    (r"/api/sessions/%s" % _session_id_regex, SessionHandler),
    (r"/api/sessions", SessionRootHandler),
]
