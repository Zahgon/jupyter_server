"""The cli for auth."""

import argparse
import sys
import warnings
from getpass import getpass

from jupyter_core.paths import jupyter_config_dir
from traitlets.log import get_logger

from jupyter_server.auth import passwd  # type:ignore[attr-defined]
from jupyter_server.config_manager import BaseJSONConfigManager


def set_password(args):
    """Set a password."""
    pass


def main(argv):
    """The main cli handler."""
    pass


if __name__ == "__main__":
    main(sys.argv)
