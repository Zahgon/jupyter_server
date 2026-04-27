"""Tornado handlers for kernel specifications.

Preliminary documentation at https://github.com/ipython/ipython/wiki/IPEP-25%3A-Registry-of-installed-kernels#rest-api
"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import glob
import json
import os
from typing import Any

pjoin = os.path.join

from jupyter_core.utils import ensure_async
from tornado import web

from jupyter_server.auth.decorator import authorized

from ...base.handlers import APIHandler
from ...utils import url_path_join, url_unescape

AUTH_RESOURCE = "kernelspecs"


def kernelspec_model(handler, name, spec_dict, resource_dir):
    """Load a KernelSpec by name and return the REST API model"""
    pass


def is_kernelspec_model(spec_dict):
    """Returns True if spec_dict is already in proper form.  This will occur when using a gateway."""
    pass


class KernelSpecsAPIHandler(APIHandler):
    """A kernel spec API handler."""

    auth_resource = AUTH_RESOURCE


class MainKernelSpecHandler(KernelSpecsAPIHandler):
    """The root kernel spec handler."""

    @web.authenticated
    @authorized
    async def get(self):
        """Get the list of kernel specs."""
        pass


class KernelSpecHandler(KernelSpecsAPIHandler):
    """A handler for an individual kernel spec."""

    @web.authenticated
    @authorized
    async def get(self, kernel_name):
        """Get a kernel spec model."""
        pass


# URL to handler mappings

kernel_name_regex = r"(?P<kernel_name>[\w\.\-%]+)"

default_handlers = [
    (r"/api/kernelspecs", MainKernelSpecHandler),
    (r"/api/kernelspecs/%s" % kernel_name_regex, KernelSpecHandler),
]
