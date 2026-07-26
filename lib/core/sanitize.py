# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re

_INVALID = re.compile(r'[\\/:*?"<>|]')
_MAX_LEN = 180


def sanitize(name, max_len=_MAX_LEN):
    if not name:
        return u'export'
    name = _INVALID.sub(u'_', name)
    return name[:max_len]
