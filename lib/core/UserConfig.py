# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import io
import json

# Persistance des réglages dans le dossier de données COMMUN de l'extension :
# 418.extension/data/<namespace>.json (via AppPaths.data_dir).
#
# Service commun à toutes les features. Indépendant du `user_config` de pyRevit
# (qui, en « mode admin », ne persiste rien : save_changes() y est un no-op).
#
# Conception volontairement SANS cache mémoire : chaque get relit le fichier et
# chaque set fait une lecture-modification-écriture. C'est robuste contre le
# piège des doubles modules (le même fichier importé sous `core.UserConfig` ET
# `lib.core.UserConfig` donne deux modules distincts, donc deux caches
# séparés → écrasements mutuels). En relisant le fichier à chaque écriture, les
# écritures de toutes les instances/modules fusionnent au lieu de se clobber.
#
# Clés INSENSIBLES À LA CASSE (normalisées en minuscules), comme le
# configparser legacy de pyRevit : le code historique écrit p.ex. 'PathDossier'
# et le relit en 'pathdossier'.
#
# API publique : get / set.

from core.AppPaths import AppPaths as _AppPaths


def _config_dir():
    # Override explicite (tests) : isole la persistance hors du dossier réel.
    override = os.environ.get('PY418_CONFIG_DIR')
    if override:
        return override
    if _AppPaths is not None:
        try:
            return _AppPaths().data_dir()
        except Exception:
            pass
    # Repli : à côté de ce module (418.extension/data).
    ext = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(ext, 'data')


def _norm(key):
    try:
        return u'{}'.format(key).lower()
    except Exception:
        return key


def _load_file(path):
    try:
        if os.path.exists(path):
            with io.open(path, 'r', encoding='utf-8') as f:
                d = json.load(f)
            if isinstance(d, dict):
                return dict((_norm(k), v) for k, v in d.items())
    except Exception:
        pass
    return {}


def _write_file(path, data):
    try:
        d = os.path.dirname(path)
        if d and not os.path.isdir(d):
            os.makedirs(d)
    except Exception:
        pass
    tmp = path + '.tmp'
    try:
        with io.open(tmp, 'w', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=2))
        # os.replace (Py3) est atomique et écrase la cible : contrairement à
        # remove-puis-rename, il ne laisse aucune fenêtre où la config a été
        # effacée mais pas encore remplacée. Repli explicite sous IronPython
        # 2.7, où os.replace n'existe pas et où os.rename refuse d'écraser.
        try:
            os.replace(tmp, path)
        except AttributeError:
            if os.path.exists(path):
                os.remove(path)
            os.rename(tmp, path)
        return True
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return False


class UserConfig(object):
    def __init__(self, namespace='418_extension'):
        self._ns = namespace or '418_extension'

    def _path(self):
        return os.path.join(_config_dir(), self._ns + '.json')

    def get(self, key, default=None):
        data = _load_file(self._path())
        k = _norm(key)
        if k in data:
            return data[k]
        return default

    def set(self, key, value):
        # Lecture-modification-écriture : relit le fichier pour fusionner avec
        # les écritures des autres instances/modules avant de sauvegarder.
        path = self._path()
        data = _load_file(path)
        try:
            data[_norm(key)] = u'{}'.format(value)
        except Exception:
            data[_norm(key)] = value
        return _write_file(path, data)
