# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    from pyrevit.userconfig import user_config as _UC
except Exception:
    _UC = None


class UserConfig(object):
    def __init__(self, namespace='418_extension'):
        self._ns = namespace or '418_extension'

    def _section(self):
        if _UC is None:
            return None
        try:
            _UC.add_section(self._ns)
        except Exception:
            pass
        try:
            return getattr(_UC, self._ns)
        except Exception as e:
            print('UserConfig [001]: section {} introuvable: {}'.format(self._ns, e))
            return None

    def get(self, key, default=None):
        sec = self._section()
        if sec is None:
            return default
        try:
            return sec.get_option(key, default)
        except Exception:
            pass
        try:
            return getattr(sec, key)
        except Exception:
            return default

    def set(self, key, value):
        # Pour persister une liste, utiliser set_list() à la place.
        sec = self._section()
        if sec is None:
            return False
        sval = u'{}'.format(value)
        saved = False
        if hasattr(sec, 'set_option'):
            try:
                sec.set_option(key, sval)
                saved = True
            except Exception:
                pass
        if not saved:
            try:
                setattr(sec, key, sval)
                saved = True
            except Exception:
                pass
        if saved and _UC is not None:
            try:
                _UC.save_changes()
            except Exception:
                pass
        return saved

    def set_list(self, key, values):
        """Persiste une liste sous forme 'v1, v2, v3' lisible par get_list."""
        return self.set(key, u', '.join(unicode(v) for v in values))

    def get_list(self, key, default=None):
        if default is None:
            default = []
        val = self.get(key, None)
        if val is None:
            return list(default)
        try:
            if isinstance(val, list):
                return list(val)
            s = val.strip()
            if not s:
                return list(default)
            return [p.strip() for p in s.split(',') if p.strip()]
        except Exception:
            return list(default)
