"""Manager to read and modify config data in JSON files."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import copy
import errno
import glob
import json
import os
import typing as t

from traitlets.config import LoggingConfigurable
from traitlets.traitlets import Bool, Unicode

StrDict = dict[str, t.Any]


def recursive_update(target: StrDict, new: StrDict) -> None:
    """Recursively update one dictionary using another.

    None values will delete their keys.
    """
    pass


def remove_defaults(data: StrDict, defaults: StrDict) -> None:
    """Recursively remove items from dict that are already in defaults"""
    pass


class BaseJSONConfigManager(LoggingConfigurable):
    """General JSON config manager

    Deals with persisting/storing config in a json file with optionally
    default values in a {section_name}.d directory.
    """

    config_dir = Unicode(".")
    read_directory = Bool(True)

    def ensure_config_dir_exists(self) -> None:
        """Will try to create the config_dir directory."""
        pass

    def file_name(self, section_name: str) -> str:
        """Returns the json filename for the section_name: {config_dir}/{section_name}.json"""
        pass

    def directory(self, section_name: str) -> str:
        """Returns the directory name for the section name: {config_dir}/{section_name}.d"""
        pass

    def get(self, section_name: str, include_root: bool = True) -> dict[str, t.Any]:
        """Retrieve the config data for the specified section.

        Returns the data as a dictionary, or an empty dictionary if the file
        doesn't exist.

        When include_root is False, it will not read the root .json file,
        effectively returning the default values.
        """
        pass

    def set(self, section_name: str, data: t.Any) -> None:
        """Store the given config data."""
        pass

    def update(self, section_name: str, new_data: t.Any) -> dict[str, t.Any]:
        """Modify the config section by recursively updating it with new_data.

        Returns the modified config data as a dictionary.
        """
        pass
