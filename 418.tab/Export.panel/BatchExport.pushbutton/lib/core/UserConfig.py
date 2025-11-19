# -*- coding: utf-8 -*-
# Accès unifié à la configuration utilisateur via pyRevit (sans dépendre de lib/config.py)

try:
    from pyrevit.userconfig import user_config as _UC
except Exception:
    _UC = None  # type: ignore


class UserConfig(object):
    def __init__(self, namespace='batch_export'):
        # Namespace conservé pour compat, on opère sur la section batch_export
        self._ns = namespace or 'batch_export'

    def _section(self):
        uc = _UC
        if uc is None:
            return None
        # S'assurer que la section existe si possible
        try:
            uc.add_section('batch_export')
        except Exception:
            pass
        try:
            return uc.batch_export
        except Exception:
            return None

    # Lit une valeur (str)
    def get(self, key, default=None):
        sec = self._section()
        if sec is None:
            return default
        try:
            # Préférence à get_option si présent
            try:
                return sec.get_option(key, default)
            except Exception:
                pass
            return getattr(sec, key)
        except Exception:
            return default

    # Écrit une valeur (str)
    def set(self, key, value):
        sec = self._section()
        if sec is None:
            return False
        try:
            sval = u"{}".format(value)
        except Exception:
            sval = value
        try:
            # Affectation générique par attribut
            setattr(sec, key, sval)
            # Sauvegarde si API dispo
            try:
                _UC.save_changes()
            except Exception:
                pass
            return True
        except Exception:
            return False

    # Liste -> [str]
    def get_list(self, key, default=None):
        if default is None:
            default = []
        val = self.get(key, None)
        try:
            if isinstance(val, list):
                return list(val)
            if isinstance(val, (str, unicode)):
                s = val.strip()
                if not s:
                    return list(default)
                return [p.strip() for p in s.split(',') if p.strip()]
        except Exception:
            pass
        return list(default)
