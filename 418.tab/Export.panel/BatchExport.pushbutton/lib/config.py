# -*- coding: utf-8 -*-
"""Adapter simple pour le stockage utilisateur via un module user_Config externe.

Expose une petite classe UserConfigStore avec un espace de noms, fournissant:
- get(key, default=None)
- set(key, value)
- get_list(key, default=None)  # accepte CSV ou liste

Cette implémentation tente différentes signatures usuelles de user_Config
pour rester compatible avec plusieurs implémentations.
"""

try:
    import user_Config as UC  # type: ignore
except Exception:
    UC = None  # type: ignore


class UserConfigStore(object):
    def __init__(self, namespace='batch_export'):
        self.namespace = namespace
        self._fallback_store = {}

    # --- lecture ---
    def get(self, key, default=None):
        if UC is not None:
            try:
                if hasattr(UC, 'get'):
                    return UC.get(self.namespace, key, default)
                if hasattr(UC, 'get_config'):
                    return UC.get_config(self.namespace, key, default)
                if hasattr(UC, 'read'):
                    return UC.read(self.namespace, key, default)
                if hasattr(UC, 'get_value'):
                    return UC.get_value(key, default)
            except Exception:
                pass
        # fallback en mémoire (utile hors Revit)
        return self._fallback_store.get(key, default)

    def get_list(self, key, default=None):
        val = self.get(key, default)
        if val is None:
            return default
        if isinstance(val, (list, tuple)):
            return list(val)
        if isinstance(val, str):
            items = [s.strip() for s in val.split(',') if s and s.strip()]
            return items
        return default

    # --- écriture ---
    def set(self, key, value):
        if UC is not None:
            try:
                if hasattr(UC, 'set'):
                    UC.set(self.namespace, key, value)
                    return True
                if hasattr(UC, 'set_config'):
                    UC.set_config(self.namespace, key, value)
                    return True
                if hasattr(UC, 'write'):
                    UC.write(self.namespace, key, value)
                    return True
                if hasattr(UC, 'set_value'):
                    UC.set_value(key, value)
                    return True
            except Exception:
                pass
        # fallback en mémoire (utile hors Revit)
        self._fallback_store[key] = value
        return False
