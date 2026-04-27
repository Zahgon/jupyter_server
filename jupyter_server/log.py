"""Log utilities."""

# -----------------------------------------------------------------------------
#  Copyright (c) Jupyter Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file LICENSE, distributed as part of this software.
# -----------------------------------------------------------------------------
import json
from urllib.parse import urlparse, urlunparse

from tornado.log import access_log

from .auth import User
from .prometheus.log_functions import prometheus_log_method

# url params to be scrubbed if seen
# any url param that *contains* one of these
# will be scrubbed from logs
_DEFAULT_SCRUB_PARAM_KEYS = {"token", "auth", "key", "code", "state", "xsrf"}


def _scrub_uri(uri: str, extra_param_keys=None) -> str:
    """scrub auth info from uri"""
    pass


def log_request(handler, record_prometheus_metrics=True):
    """log a bit more information about each request than tornado's default

    - move static file get success to debug-level (reduces noise)
    - get proxied IP instead of proxy IP
    - log referer for redirect and failed requests
    - log user-agent for failed requests

    if record_prometheus_metrics is true, will record a histogram prometheus
    metric (http_request_duration_seconds) for each request handler
    """
    pass
