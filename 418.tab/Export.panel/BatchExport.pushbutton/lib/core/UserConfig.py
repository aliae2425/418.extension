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
            print("UserConfig: _UC is None")
            return None
        # S'assurer que la section existe si possible
        try:
            uc.add_section('batch_export')
        except Exception:
            pass
        try:
            return uc.batch_export
        except Exception as e:
            print("UserConfig: Could not access uc.batch_export: {}".format(e))
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
            print("UserConfig: Section is None, cannot set '{}'".format(key))
            return False
        
        # Prepare value: ensure it is a utf-8 encoded byte string for ConfigParser
        try:
            # 1. Convert to unicode
            if isinstance(value, unicode):
                uval = value
            elif isinstance(value, str):
                try:
                    uval = value.decode('utf-8')
                except Exception:
                    try:
                        uval = value.decode('mbcs')
                    except Exception:
                        uval = value.decode('latin-1')
            else:
                uval = unicode(value)
            
            # 2. Encode to utf-8 bytes
            sval = uval.encode('utf-8')
        except Exception as e:
            print("UserConfig: Error preparing value for '{}': {}".format(key, e))
            sval = value

        try:
            print("UserConfig: Setting '{}' to '{}'".format(key, sval))
        except Exception:
            print("UserConfig: Setting '{}' (value not printable)".format(key))
        
        success = False
        # 1. Try set_option (pyRevit standard)
        if hasattr(sec, 'set_option'):
            try:
                sec.set_option(key, sval)
                success = True
            except Exception as e:
                print("UserConfig: Failed to set_option '{}': {}".format(key, e))
        
        # 2. Try setattr (fallback)
        if not success:
            try:
                setattr(sec, key, sval)
                success = True
            except Exception as e:
                print("UserConfig: Failed to setattr '{}': {}".format(key, e))

        if success:
            # Sauvegarde si API dispo
            try:
                _UC.save_changes()
                print("UserConfig: Saved changes successfully.")
            except Exception as e:
                print("UserConfig: Failed to save_changes: {}".format(e))
            return True
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
