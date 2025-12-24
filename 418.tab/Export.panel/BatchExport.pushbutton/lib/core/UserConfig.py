# -*- coding: utf-8 -*-
"""Backend de configuration local.

Historique: ce module utilisait pyRevit userconfig.
Nouveau: stockage JSON local dans BatchExport.pushbutton/Data.

Objectif: éviter toute dépendance à pyRevit.userconfig pour les réglages,
et permettre la portabilité (copie du dossier = mêmes réglages).
"""

from __future__ import unicode_literals

import io
import json
import os


try:
    unicode  # type: ignore
except Exception:
    unicode = str  # type: ignore


def _to_text(value):
    try:
        return u"{}".format(value)
    except Exception:
        try:
            return str(value)
        except Exception:
            return ''


def _data_dir():
    # lib/core/UserConfig.py -> lib/core -> lib -> BatchExport.pushbutton
    here = os.path.dirname(__file__)
    return os.path.normpath(os.path.join(here, '..', '..', 'Data'))


def _store_path():
    return os.path.join(_data_dir(), 'config.json')


def _ensure_dir():
    try:
        d = _data_dir()
        if not os.path.exists(d):
            os.makedirs(d)
    except Exception:
        pass


def _load_store():
    _ensure_dir()
    p = _store_path()
    if not os.path.exists(p):
        return {}
    try:
        with io.open(p, mode='r', encoding='utf-8-sig') as f:
            raw = f.read()
        raw = (raw or '').strip()
        if not raw:
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_store(store_dict):
    _ensure_dir()
    p = _store_path()
    try:
        safe = store_dict if isinstance(store_dict, dict) else {}
        with io.open(p, mode='w', encoding='utf-8', newline='') as f:
            f.write(_to_text(json.dumps(safe, indent=2, sort_keys=True)))
        return True
    except Exception:
        return False


class UserConfig(object):
    def __init__(self, namespace='batch_export'):
        self._ns = (namespace or 'batch_export').strip() or 'batch_export'

    def _get_namespace_dict(self, store_dict, create=True):
        if not isinstance(store_dict, dict):
            return None
        if self._ns not in store_dict:
            if not create:
                return None
            store_dict[self._ns] = {}
        sec = store_dict.get(self._ns)
        if not isinstance(sec, dict):
            if create:
                store_dict[self._ns] = {}
                sec = store_dict[self._ns]
            else:
                return None
        return sec

    # Lit une valeur (str)
    def get(self, key, default=None):
        key = (key or '').strip()
        if not key:
            return default
        store = _load_store()
        sec = self._get_namespace_dict(store, create=False)
        if sec is None:
            return default
        try:
            return sec.get(key, default)
        except Exception:
            return default

    # Écrit une valeur (str)
    def set(self, key, value):
        key = (key or '').strip()
        if not key:
            return False

        # Convention: la majorité du code stocke des strings.
        # On garde tel quel, mais on accepte dict/list pour certaines clés.
        try:
            if isinstance(value, (dict, list)):
                sval = value
            else:
                sval = _to_text(value)
        except Exception:
            sval = _to_text(value)

        store = _load_store()
        sec = self._get_namespace_dict(store, create=True)
        if sec is None:
            return False
        try:
            sec[key] = sval
        except Exception:
            return False
        return bool(_save_store(store))

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
