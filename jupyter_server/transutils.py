"""Translation related utilities. When imported, injects _ to builtins"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import gettext
import os
import warnings


def _trans_gettext_deprecation_helper(*args, **kwargs):
    """The trans gettext deprecation helper."""
    pass


# Set up message catalog access
base_dir = os.path.realpath(os.path.join(__file__, "..", ".."))
trans = gettext.translation(
    "notebook", localedir=os.path.join(base_dir, "notebook/i18n"), fallback=True
)
_ = _trans_gettext_deprecation_helper
_i18n = trans.gettext
