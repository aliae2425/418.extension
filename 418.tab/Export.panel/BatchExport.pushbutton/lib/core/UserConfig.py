# -*- coding: utf-8 -*-
# Wrapper simple autour de UserConfigStore pour instanciation explicite

class UserConfig(object):
    def __init__(self, namespace='batch_export'):
        try:
            from ..config import UserConfigStore as _Store
        except Exception:
            _Store = None  # type: ignore
        self._store = _Store(namespace) if _Store is not None else None

    # Lit une valeur (str)
    def get(self, key, default=None):
        try:
            return self._store.get(key, default) if self._store is not None else default
        except Exception:
            return default

    # Écrit une valeur (str)
    def set(self, key, value):
        try:
            return bool(self._store.set(key, value)) if self._store is not None else False
        except Exception:
            return False

    # Liste -> [str]
    def get_list(self, key, default=None):
        try:
            return self._store.get_list(key, default=default or []) if self._store is not None else (default or [])
        except Exception:
            return default or []
