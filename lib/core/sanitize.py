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


_INVALID_REVIT = re.compile(r'[\\:{}\[\]|;<>?`~]')


def sanitize_revit_name(name):
    r"""Nettoie un nom d'élément Revit : retire les caractères interdits par
    Revit (`\\ : { } [ ] | ; < > ? ` ~`). Retourne `u'SansNom'` si le
    résultat est vide. Ne tronque pas (contrairement à `sanitize`, dédié aux
    noms de fichiers)."""
    if not name:
        return u'SansNom'
    cleaned = _INVALID_REVIT.sub(u'', name)
    return cleaned if cleaned else u'SansNom'
