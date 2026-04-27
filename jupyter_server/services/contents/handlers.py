"""Tornado handlers for the contents web service.

Preliminary documentation at https://github.com/ipython/ipython/wiki/IPEP-27%3A-Contents-Service
"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import json
from http import HTTPStatus
from typing import Any

try:
    from jupyter_client.jsonutil import json_default
except ImportError:
    from jupyter_client.jsonutil import date_default as json_default

from jupyter_core.utils import ensure_async
from tornado import web

from jupyter_server.auth.decorator import allow_unauthenticated, authorized
from jupyter_server.base.handlers import APIHandler, JupyterHandler, path_regex
from jupyter_server.utils import url_escape, url_path_join

AUTH_RESOURCE = "contents"


def _validate_keys(expect_defined: bool, model: dict[str, Any], keys: list[str]):
    """
    Validate that the keys are defined (i.e. not None) or not (i.e. None)
    """
    pass


def validate_model(model, expect_content=False, expect_hash=False):
    """
    Validate a model returned by a ContentsManager method.

    If expect_content is True, then we expect non-null entries for 'content'
    and 'format'.

    If expect_hash is True, then we expect non-null entries for 'hash' and 'hash_algorithm'.
    """
    pass


class ContentsAPIHandler(APIHandler):
    """A contents API handler."""

    auth_resource = AUTH_RESOURCE


class ContentsHandler(ContentsAPIHandler):
    """A contents handler."""

    def location_url(self, path):
        """Return the full URL location of a file.

        Parameters
        ----------
        path : unicode
            The API path of the file, such as "foo/bar.txt".
        """
        pass

    def _finish_model(self, model, location=True):
        """Finish a JSON request with a model, setting relevant headers, etc."""
        pass

    async def _finish_error(self, code, message):
        """Finish a JSON request with an error code and descriptive message"""
        pass

    @web.authenticated
    @authorized
    async def get(self, path=""):
        """Return a model for a file or directory.

        A directory model contains a list of models (without content)
        of the files and directories it contains.
        """
        pass

    @web.authenticated
    @authorized
    async def patch(self, path=""):
        """PATCH renames a file or directory without re-uploading content."""
        pass

    async def _copy(self, copy_from, copy_to=None):
        """Copy a file, optionally specifying a target directory."""
        pass

    async def _upload(self, model, path):
        """Handle upload of a new file to path"""
        pass

    async def _new_untitled(self, path, type="", ext=""):
        """Create a new, empty untitled entity"""
        pass

    async def _save(self, model, path):
        """Save an existing file."""
        pass

    @web.authenticated
    @authorized
    async def post(self, path=""):
        """Create a new file in the specified path.

        POST creates new files. The server always decides on the name.

        POST /api/contents/path
          New untitled, empty file or directory.
        POST /api/contents/path
          with body {"copy_from" : "/path/to/OtherNotebook.ipynb"}
          New copy of OtherNotebook in path
        """
        pass

    @web.authenticated
    @authorized
    async def put(self, path=""):
        """Saves the file in the location specified by name and path.

        PUT is very similar to POST, but the requester specifies the name,
        whereas with POST, the server picks the name.

        PUT /api/contents/path/Name.ipynb
          Save notebook at ``path/Name.ipynb``. Notebook structure is specified
          in `content` key of JSON request body. If content is not specified,
          create a new empty notebook.
        """
        pass

    @web.authenticated
    @authorized
    async def delete(self, path=""):
        """delete a file in the given path"""
        pass


class CheckpointsHandler(ContentsAPIHandler):
    """A checkpoints API handler."""

    @web.authenticated
    @authorized
    async def get(self, path=""):
        """get lists checkpoints for a file"""
        pass

    @web.authenticated
    @authorized
    async def post(self, path=""):
        """post creates a new checkpoint"""
        pass


class ModifyCheckpointsHandler(ContentsAPIHandler):
    """A checkpoints modification handler."""

    @web.authenticated
    @authorized
    async def post(self, path, checkpoint_id):
        """post restores a file from a checkpoint"""
        pass

    @web.authenticated
    @authorized
    async def delete(self, path, checkpoint_id):
        """delete clears a checkpoint for a given file"""
        pass


class NotebooksRedirectHandler(JupyterHandler):
    """Redirect /api/notebooks to /api/contents"""

    SUPPORTED_METHODS = (
        "GET",
        "PUT",
        "PATCH",
        "POST",
        "DELETE",
    )

    @allow_unauthenticated
    def get(self, path):
        """Handle a notebooks redirect."""
        pass

    put = patch = post = delete = get


class TrustNotebooksHandler(JupyterHandler):
    """Handles trust/signing of notebooks"""

    @web.authenticated
    @authorized(resource=AUTH_RESOURCE)
    async def post(self, path=""):
        """Trust a notebook by path."""
        pass


# -----------------------------------------------------------------------------
# URL to handler mappings
# -----------------------------------------------------------------------------


_checkpoint_id_regex = r"(?P<checkpoint_id>[\w-]+)"


default_handlers = [
    (r"/api/contents%s/checkpoints" % path_regex, CheckpointsHandler),
    (
        rf"/api/contents{path_regex}/checkpoints/{_checkpoint_id_regex}",
        ModifyCheckpointsHandler,
    ),
    (r"/api/contents%s/trust" % path_regex, TrustNotebooksHandler),
    (r"/api/contents%s" % path_regex, ContentsHandler),
    (r"/api/notebooks/?(.*)", NotebooksRedirectHandler),
]
