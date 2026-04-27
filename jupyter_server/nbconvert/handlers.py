"""Tornado handlers for nbconvert."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import io
import os
import sys
import zipfile

from anyio.to_thread import run_sync
from jupyter_core.utils import ensure_async
from nbformat import from_dict
from tornado import web
from tornado.log import app_log

from jupyter_server.auth.decorator import authorized

from ..base.handlers import FilesRedirectHandler, JupyterHandler, path_regex

AUTH_RESOURCE = "nbconvert"

# datetime.strftime date format for jupyter
# inlined from ipython_genutils
if sys.platform == "win32":
    date_format = "%B %d, %Y"
else:
    date_format = "%B %-d, %Y"


def find_resource_files(output_files_dir):
    """Find the resource files in a directory."""
    pass


def respond_zip(handler, name, output, resources):
    """Zip up the output and resource files and respond with the zip file.

    Returns True if it has served a zip file, False if there are no resource
    files, in which case we serve the plain output file.
    """
    pass


def get_exporter(format, **kwargs):
    """get an exporter, raising appropriate errors"""
    pass


class NbconvertFileHandler(JupyterHandler):
    """An nbconvert file handler."""

    auth_resource = AUTH_RESOURCE
    SUPPORTED_METHODS = ("GET",)

    @web.authenticated
    @authorized
    async def get(self, format, path):
        """Get a notebook file in a desired format."""
        pass


class NbconvertPostHandler(JupyterHandler):
    """An nbconvert post handler."""

    SUPPORTED_METHODS = ("POST",)
    auth_resource = AUTH_RESOURCE

    @web.authenticated
    @authorized
    async def post(self, format):
        """Convert a notebook file to a desired format."""
        pass


# -----------------------------------------------------------------------------
# URL to handler mappings
# -----------------------------------------------------------------------------

_format_regex = r"(?P<format>\w+)"


default_handlers = [
    (r"/nbconvert/%s" % _format_regex, NbconvertPostHandler),
    (rf"/nbconvert/{_format_regex}{path_regex}", NbconvertFileHandler),
]
