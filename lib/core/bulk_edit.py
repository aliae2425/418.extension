# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Édition en masse d'une propriété sur une multi-sélection d'items quelconques.
# Fonctions de module : il n'y a aucun état à porter. Items = tout objet dont
# les propriétés sont accessibles via getattr/setattr. Aucune dépendance
# Revit ou WPF — testable en Python pur.


def get_selected(items, prop=u'Selected'):
    """Retourne les items dont `prop` est truthy."""
    return [it for it in (items or []) if getattr(it, prop, False)]


def apply(items, prop, value):
    """Fixe `prop = value` sur tous les items (silencieux si setattr échoue)."""
    for it in (items or []):
        try:
            setattr(it, prop, value)
        except Exception:
            pass


def toggle(items, prop):
    """Bascule `prop` sur la sélection.

    Règle : si TOUS les items ont `prop=True` → met tout à False.
            sinon                             → met tout à True.
    Idempotent sur une liste vide.
    """
    items = list(items or [])
    if not items:
        return
    apply(items, prop, not all(getattr(it, prop, False) for it in items))


def select_all(items, prop=u'Selected'):
    """Met `prop = True` sur tous les items."""
    apply(items, prop, True)


def deselect_all(items, prop=u'Selected'):
    """Met `prop = False` sur tous les items."""
    apply(items, prop, False)
