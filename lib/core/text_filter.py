# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import unicodedata

# Filtrage d'une liste d'items par sous-chaîne, insensible à la casse et aux
# accents. Fonctions de module : rien à porter entre deux appels. Aucune
# dépendance Revit/WPF — testable en Python pur.


def normaliser(value):
    """Minuscule, sans accents. Tolère None et les non-chaînes."""
    if value is None:
        return u''
    try:
        text = value if isinstance(value, type(u'')) else u'{0}'.format(value)
    except Exception:
        return u''
    decomposed = unicodedata.normalize('NFKD', text)
    stripped = u''.join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.lower()


def filtrer(items, text, getters):
    """Renvoie les items dont au moins un getter contient ``text``.

    text vide/None → tous les items. getters = callables item -> texte.
    """
    items = list(items or [])
    needle = normaliser(text).strip()
    if not needle:
        return items
    out = []
    for item in items:
        for getter in getters:
            try:
                hay = normaliser(getter(item))
            except Exception:
                hay = u''
            if needle in hay:
                out.append(item)
                break
    return out
