# -*- coding: utf-8 -*-
"""Configuration store (core): UserConfigStore.

This centralizes access to pyRevit's user_config with a thin adapter.
"""

from pyrevit.userconfig import user_config as UC

try:
    BASESTRING_T = basestring  # type: ignore
except NameError:
    BASESTRING_T = str  # type: ignore


class UserConfigStore:
    def __init__(self, namespace='batch_export'):
        self.namespace = namespace

    def set(self, key, value):
        try:
            UC.add_section("batch_export")
        except Exception:
            pass
        try:
            sval = str(value)
        except Exception:
            try:
                sval = u"{}".format(value)
            except Exception:
                sval = value
        try:
            if key == "Export":
                UC.batch_export.Export = sval
            elif key == "ExportParFeuilles":
                UC.batch_export.ExportParFeuilles = sval
            elif key == "ExportDWG":
                UC.batch_export.ExportDWG = sval
            elif key == "PathDossier":
                UC.batch_export.PathDossier = sval
            else:
                try:
                    setattr(UC.batch_export, key, sval)
                except Exception:
                    return False
            UC.save_changes()
            return True
        except Exception:
            return False

    def get(self, key, default=""):
        try:
            return UC.batch_export.get_option(key, default)
        except Exception:
            try:
                return getattr(UC.batch_export, key)
            except Exception:
                return default

    def get_list(self, key, default=None):
        if default is None:
            default = []
        try:
            raw = None
            try:
                raw = UC.batch_export.get_option(key, None)
            except Exception:
                pass
            if raw is None:
                try:
                    raw = getattr(UC.batch_export, key)
                except Exception:
                    raw = None
            if isinstance(raw, list):
                return list(raw)
            if isinstance(raw, BASESTRING_T):
                s = raw.strip()
                if not s:
                    return list(default)
                return [p.strip() for p in s.split(',') if p.strip()]
            return list(default)
        except Exception:
            return list(default)


__all__ = ["UserConfigStore"]
