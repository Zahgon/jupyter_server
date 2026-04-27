"""Server functions for loading translations"""

from __future__ import annotations

import errno
import json
import re
from collections import defaultdict
from os.path import dirname
from os.path import join as pjoin
from typing import Any

I18N_DIR = dirname(__file__)
# Cache structure:
# {'nbjs': {   # Domain
#   'zh-CN': {  # Language code
#     <english string>: <translated string>
#     ...
#   }
# }}
TRANSLATIONS_CACHE: dict[str, Any] = {"nbjs": {}}


_accept_lang_re = re.compile(
    r"""
(?P<lang>[a-zA-Z]{1,8}(-[a-zA-Z]{1,8})?)
(\s*;\s*q\s*=\s*
  (?P<qvalue>[01](.\d+)?)
)?""",
    re.VERBOSE,
)


def parse_accept_lang_header(accept_lang):
    """Parses the 'Accept-Language' HTTP header.

    Returns a list of language codes in *ascending* order of preference
    (with the most preferred language last).
    """
    pass


def load(language, domain="nbjs"):
    """Load translations from an nbjs.json file"""
    pass


def cached_load(language, domain="nbjs"):
    """Load translations for one language, using in-memory cache if available"""
    pass


def combine_translations(accept_language, domain="nbjs"):
    """Combine translations for multiple accepted languages.

    Returns data re-packaged in jed1.x format.
    """
    pass
