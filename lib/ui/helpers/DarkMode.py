# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from pyrevit.userconfig import user_config as _UC
    def is_dark():
        try:
            theme = _UC.core.get_option('colorize_docs', 'default')
            return str(theme).lower() in ('dark', 'true', '1')
        except Exception:
            return False
except Exception:
    def is_dark():
        return False
