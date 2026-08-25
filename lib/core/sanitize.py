# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re

_INVALID = re.compile(r'[\\/:*?"<>|]')
_TRAILING = re.compile(r'[\s\.]+$')
_MAX_LEN = 180


def sanitize(name, max_len=_MAX_LEN, fallback=u'export'):
    r"""Nettoie `name` pour en faire un nom de FICHIER Windows valide.

    Remplace les caractères interdits (`\ / : * ? " < > |`) par `_`, puis
    retire espaces et points en fin de nom -- Windows les rejette, et un nom
    tronqué à `max_len` peut se terminer sur l'un d'eux. Tronque à `max_len`.
    Retourne `fallback` si l'entrée est vide ou ne laisse rien après nettoyage.
    """
    if not name:
        return fallback
    name = _INVALID.sub(u'_', name)
    name = _TRAILING.sub(u'', name.strip())[:max_len]
    name = _TRAILING.sub(u'', name)
    return name or fallback


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
