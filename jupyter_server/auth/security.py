"""
Password generation for the Jupyter Server.
"""

import getpass
import hashlib
import json
import os
import random
import traceback
import warnings
from contextlib import contextmanager

from jupyter_core.paths import jupyter_config_dir
from traitlets.config import Config
from traitlets.config.loader import ConfigFileNotFound, JSONFileConfigLoader

# Length of the salt in nr of hex chars, which implies salt_len * 4
# bits of randomness.
salt_len = 12


def passwd(passphrase=None, algorithm="argon2"):
    """Generate hashed password and salt for use in server configuration.

    In the server configuration, set `c.ServerApp.password` to
    the generated string.

    Parameters
    ----------
    passphrase : str
        Password to hash.  If unspecified, the user is asked to input
        and verify a password.
    algorithm : str
        Hashing algorithm to use (e.g, 'sha1' or any argument supported
        by :func:`hashlib.new`, or 'argon2').

    Returns
    -------
    hashed_passphrase : str
        Hashed password, in the format 'hash_algorithm:salt:passphrase_hash'.

    Examples
    --------
    >>> passwd("mypassword")  # doctest: +ELLIPSIS
    'argon2:...'

    """
    pass


def passwd_check(hashed_passphrase, passphrase):
    """Verify that a given passphrase matches its hashed version.

    Parameters
    ----------
    hashed_passphrase : str
        Hashed password, in the format returned by `passwd`.
    passphrase : str
        Passphrase to validate.

    Returns
    -------
    valid : bool
        True if the passphrase matches the hash.

    Examples
    --------
    >>> myhash = passwd("mypassword")
    >>> passwd_check(myhash, "mypassword")
    True

    >>> passwd_check(myhash, "otherpassword")
    False

    >>> passwd_check("sha1:0e112c3ddfce:a68df677475c2b47b6e86d0467eec97ac5f4b85a", "mypassword")
    True
    """
    pass


@contextmanager
def persist_config(config_file=None, mode=0o600):
    """Context manager that can be used to modify a config object

    On exit of the context manager, the config will be written back to disk,
    by default with user-only (600) permissions.
    """
    pass


def set_password(password=None, config_file=None):
    """Ask user for password, store it in JSON configuration file"""
    pass
